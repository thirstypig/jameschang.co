#!/usr/bin/env python3
"""Fetch project TLDR blocks + GitHub shipping events and update /now/index.html.

Called by the GitHub Action on a daily cron (7:00 AM PT). For each project in
bin/projects-config.json:

  1. Fetches the repo's CLAUDE.md (via TLDR_FETCH_TOKEN) and extracts the
     <!-- now-tldr -->...<!-- /now-tldr --> block.
  2. Filters the global user-events feed for recent PushEvent/PullRequestEvent/
     ReleaseEvent activity in that project's shipping_repos and renders a
     "Recently shipped" list of up to 3 items.
  3. Renders an Auto-updated timestamp line.
  4. Splices the combined block into <!-- TLDR-{slug}-START -->...<!-- TLDR-{slug}-END -->
     in now/index.html.

Fail-safe: if a project's TLDR can't be fetched, that project is skipped
entirely — existing HTML fallback is preserved. If the events fetch fails,
shipping lines are omitted but TLDR + timestamp still render.
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from _shared import (
    content_changed,
    escape_html,
    fetch_json,
    format_update_time,
    read_now_html,
    record_heartbeat,
    relative_time,
    replace_marker,
    write_now_html,
    REPO_ROOT,
    USER_AGENT,
)

CONFIG_PATH = os.path.join(REPO_ROOT, "bin", "projects-config.json")
TLDR_PATTERN = re.compile(r"<!-- now-tldr -->\s*(.*?)\s*<!-- /now-tldr -->", re.DOTALL)
EVENT_WINDOW = timedelta(days=14)  # how far back to look for shipping events
EVENTS_PER_PROJECT = 3


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["projects"]


def fetch_file(repo, path, token):
    """Fetch a raw file from GitHub. Returns string or None on failure."""
    url = f"https://raw.githubusercontent.com/{repo}/HEAD/{path}"
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError) as e:
        print(f"  fetch failed for {repo}/{path}: {e}")
        return None


def extract_tldr(markdown):
    """Return TLDR block content from markdown, or None if absent."""
    if not markdown:
        return None
    m = TLDR_PATTERN.search(markdown)
    return m.group(1).strip() if m else None


def fetch_github_events(token):
    """Fetch recent public events for thirstypig. Returns list or None on failure."""
    url = "https://api.github.com/users/thirstypig/events/public?per_page=100"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        return fetch_json(url, headers=headers)
    except (HTTPError, URLError) as e:
        print(f"  events fetch failed: {e}")
        return None


def parse_events(events, token):
    """Group recent events by repo. Returns {repo_name: [event_dict, ...]}.

    Each event dict: {time, summary, url, _head_sha?}. Events are ordered
    newest-first. PushEvents include a _head_sha for commit-message enrichment.
    """
    if not events:
        return {}
    cutoff = datetime.now(timezone.utc) - EVENT_WINDOW
    by_repo = defaultdict(list)
    for ev in events:
        try:
            t = datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if t < cutoff:
            continue
        repo = ev.get("repo", {}).get("name", "")
        if not repo:
            continue
        etype = ev.get("type")
        payload = ev.get("payload") or {}
        entry = {"time": ev["created_at"], "url": None, "summary": None}
        if etype == "PushEvent":
            sha = payload.get("head")
            ref = payload.get("ref", "").replace("refs/heads/", "")
            entry["summary"] = f"Pushed to {ref}" if ref else "Pushed"
            entry["url"] = f"https://github.com/{repo}/commit/{sha}" if sha else f"https://github.com/{repo}"
            entry["_head_sha"] = sha
        elif etype == "PullRequestEvent":
            pr = payload.get("pull_request") or {}
            action = payload.get("action", "")
            title = pr.get("title") or "(untitled)"
            entry["summary"] = f"PR {action}: {title}"
            entry["url"] = pr.get("html_url")
        elif etype == "ReleaseEvent":
            rel = payload.get("release") or {}
            entry["summary"] = f"Released {rel.get('tag_name', '')}"
            entry["url"] = rel.get("html_url")
        else:
            continue
        by_repo[repo].append(entry)
    # Enrich push events with first line of commit message (top-N only to avoid rate burn)
    enriched = 0
    for events_list in by_repo.values():
        for entry in events_list[:EVENTS_PER_PROJECT]:
            sha = entry.pop("_head_sha", None)
            if not sha or not entry["summary"].startswith("Pushed"):
                continue
            if enriched >= 15:  # hard cap to stay well inside rate limit
                break
            try:
                headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                repo_name = [r for r, lst in by_repo.items() if entry in lst][0]
                commit = fetch_json(f"https://api.github.com/repos/{repo_name}/commits/{sha}", headers=headers)
                first_line = ((commit.get("commit") or {}).get("message") or "").split("\n")[0].strip()
                if first_line:
                    entry["summary"] = first_line
                enriched += 1
            except (HTTPError, URLError):
                pass
    return by_repo


def events_for_project(project, events_by_repo):
    """Return up to EVENTS_PER_PROJECT most recent events attributed to this project."""
    shipping_repos = project.get("shipping_repos") or [project["repo"]]
    merged = []
    for r in shipping_repos:
        merged.extend(events_by_repo.get(r, []))
    merged.sort(key=lambda e: e["time"], reverse=True)
    return merged[:EVENTS_PER_PROJECT]


def render_shipping_list(events):
    """Render the Recently-shipped <p> line, or empty string if no events."""
    if not events:
        return ""
    items = []
    for ev in events:
        summary = escape_html(ev["summary"])[:90]
        url = escape_html(ev["url"] or "#")
        when = relative_time(ev["time"])
        items.append(f'<a href="{url}" rel="noopener" target="_blank">{summary}</a> <span class="gh-when">&middot; {when}</span>')
    return (
        '          <p class="shipping-recent"><strong>Recently shipped:</strong> '
        + ' &middot; '.join(items)
        + '</p>\n'
    )


def render_block(tldr_html, shipping_html, now_str):
    """Assemble the full replacement HTML for a project's TLDR marker block."""
    return (
        f"\n"
        f"          <p>{tldr_html}</p>\n"
        f"{shipping_html}"
        f'          <p class="feed-updated">Auto-updated {now_str} via CLAUDE.md + GitHub events.</p>\n'
        f"        "
    )


def main():
    projects = load_config()
    token = os.environ.get("TLDR_FETCH_TOKEN", "").strip() or None
    if not token:
        print("WARNING: TLDR_FETCH_TOKEN not set — private repos will 404.")

    events_raw = fetch_github_events(token)
    events_by_repo = parse_events(events_raw, token)

    old_content = read_now_html()
    new_content = old_content
    updates = []
    failures = []
    now_str = format_update_time()

    for project in projects:
        slug = project["slug"]
        repo = project["repo"]
        path = project["file"]
        print(f"  {slug} ({repo}/{path}):")

        markdown = fetch_file(repo, path, token)
        tldr = extract_tldr(markdown)
        if not tldr:
            failures.append(slug)
            print("    skipped (no TLDR content) — preserving existing HTML")
            continue

        shipping_events = events_for_project(project, events_by_repo)
        shipping_html = render_shipping_list(shipping_events)

        block = render_block(tldr, shipping_html, now_str)
        candidate, replaced = replace_marker(new_content, f"TLDR-{slug}", block)
        if not replaced:
            failures.append(slug)
            print(f"    skipped (markers <!-- TLDR-{slug}-START/END --> not found in now/index.html)")
            continue

        new_content = candidate
        updates.append(slug)
        print(f"    spliced ({len(shipping_events)} shipping event{'s' if len(shipping_events) != 1 else ''})")

    if not content_changed(old_content, new_content):
        record_heartbeat("projects")
        print("No meaningful changes.")
        return

    write_now_html(new_content)
    if updates:
        record_heartbeat("projects")
    else:
        record_heartbeat("projects", error=f"all {len(projects)} projects failed")
    print(f"Updated now/index.html. Spliced: {len(updates)}, failed: {len(failures)}.")


if __name__ == "__main__":
    main()
