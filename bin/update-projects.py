#!/usr/bin/env python3
"""Fetch project TLDR blocks + GitHub shipping events and update /now/index.html.

Called by the GitHub Action on a daily cron (7:00 AM PT). For each project in
bin/projects-config.json:

  1. Fetches the repo's CLAUDE.md (via TLDR_FETCH_TOKEN) and extracts the
     <!-- now-tldr -->...<!-- /now-tldr --> block.
  2. Filters the global user-events feed for recent PushEvent/PullRequestEvent/
     ReleaseEvent activity in that project's shipping_repos and renders a
     "Recently shipped" line showing the single most recent item.
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
    relative_time_html,
    replace_marker,
    safe_url,
    write_now_html,
    REPO_ROOT,
    USER_AGENT,
)

CONFIG_PATH = os.path.join(REPO_ROOT, "bin", "projects-config.json")
TLDR_PATTERN = re.compile(r"<!-- now-tldr -->\s*(.*?)\s*<!-- /now-tldr -->", re.DOTALL)
EVENT_WINDOW = timedelta(days=14)  # how far back to look for shipping events
EVENTS_PER_PROJECT = 1
MAX_COMMIT_ENRICHMENTS = 15  # hard cap on per-run GitHub /commits/{sha} fetches
ACTIVE_THRESHOLD_DAYS = 7  # most-recent shipping event within this window → active


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
        print(f"  fetch failed for {repo}/{path}: {e}", file=sys.stderr)
        return None


def extract_tldr(markdown):
    """Return TLDR block content from markdown, or None if absent.

    The TLDR block is embedded directly into the rendered HTML, so any
    markdown emphasis (**bold**) and inline code (`code`) tokens are
    converted to <strong> and <code> tags here. HTML entities in the
    raw text are escaped first so that authoring something like
    `<VenueChips>` in CLAUDE.md doesn't leak into the page as a real tag.
    """
    if not markdown:
        return None
    m = TLDR_PATTERN.search(markdown)
    if not m:
        return None
    raw = m.group(1).strip()
    return _render_markdown_inline(raw)


_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_MD_CODE_RE = re.compile(r"`([^`]+)`")


def _render_markdown_inline(text):
    """Convert basic inline markdown (**bold**, `code`) to HTML.

    Escapes HTML entities first so author-written angle brackets in
    CLAUDE.md TLDRs (e.g., a literal <VenueChips> reference) render
    as text rather than breaking the page. Order matters: escape, then
    apply the bold/code regexes against the escaped text.
    """
    out = escape_html(text)
    out = _MD_BOLD_RE.sub(r"<strong>\1</strong>", out)
    out = _MD_CODE_RE.sub(r"<code>\1</code>", out)
    return out


def fetch_github_events(token):
    """Fetch recent events for thirstypig (includes private repos when token is provided). Returns list or None on failure."""
    url = "https://api.github.com/users/thirstypig/events?per_page=100"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        return fetch_json(url, headers=headers, timeout=15)
    except (HTTPError, URLError) as e:
        print(f"  events fetch failed: {e}", file=sys.stderr)
        return None


def _parse_iso(ts):
    """Parse an ISO-8601 timestamp into a UTC datetime, tolerating both Z
    and +00:00 suffixes. Returns None on failure."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def parse_events(events, token):
    """Group recent events by repo. Returns {repo_name: [event_dict, ...]}.

    Each event dict: {time, summary, url, _repo, _head_sha?}. Events within a
    repo are ordered newest-first by their `time` field (datetime-parsed, not
    lex-compared, so mixed Z / +00:00 suffixes sort correctly). PushEvents
    include a _head_sha for commit-message enrichment.
    """
    if not events:
        return {}
    cutoff = datetime.now(timezone.utc) - EVENT_WINDOW
    by_repo = defaultdict(list)
    for ev in events:
        t = _parse_iso(ev.get("created_at"))
        if t is None or t < cutoff:
            continue
        repo = ev.get("repo", {}).get("name", "")
        if not repo:
            continue
        etype = ev.get("type")
        payload = ev.get("payload") or {}
        # _repo is stamped on construction so enrichment can attribute the
        # entry back to its repo by direct field lookup — avoids the prior
        # O(N²) `if entry in lst` identity-equality scan that broke silently
        # if any future refactor copied the entry dict.
        entry = {"time": ev["created_at"], "url": None, "summary": None, "_repo": repo}
        if etype == "PushEvent":
            sha = payload.get("head")
            ref = payload.get("ref", "").replace("refs/heads/", "")
            entry["summary"] = f"Pushed to {ref}" if ref else "Pushed"
            entry["url"] = f"https://github.com/{repo}/commit/{sha}" if sha else f"https://github.com/{repo}"
            entry["_head_sha"] = sha
        elif etype == "PullRequestEvent":
            pr = payload.get("pull_request") or {}
            html_url = pr.get("html_url")
            title = pr.get("title")
            # Public-events endpoint strips payload.pull_request for private-
            # repo events, leaving no URL or title. The merge commit still
            # arrives as a PushEvent with full data, so dropping these loses
            # nothing and avoids rendering "(untitled)" dead links.
            if not html_url or not title:
                continue
            action = payload.get("action", "")
            entry["summary"] = f"PR {action}: {title}"
            entry["url"] = html_url
        elif etype == "ReleaseEvent":
            rel = payload.get("release") or {}
            entry["summary"] = f"Released {rel.get('tag_name', '')}"
            entry["url"] = rel.get("html_url")
        else:
            continue
        by_repo[repo].append(entry)
    # Enrich the most-recent N push events per repo with the first line of
    # the commit message. Time-sort first so the "first N" we enrich match
    # the "first N" that events_for_project will surface.
    enriched = 0
    for events_list in by_repo.values():
        events_list.sort(key=lambda e: _parse_iso(e["time"]) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        for entry in events_list[:EVENTS_PER_PROJECT]:
            sha = entry.pop("_head_sha", None)
            if not sha or not entry["summary"].startswith("Pushed"):
                continue
            if enriched >= MAX_COMMIT_ENRICHMENTS:
                break
            try:
                headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                commit = fetch_json(f"https://api.github.com/repos/{entry['_repo']}/commits/{sha}", headers=headers, timeout=15)
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
    # Parse to datetime for correctness — lex-sort works only when every
    # timestamp shares the same tz suffix, which is fragile.
    merged.sort(key=lambda e: _parse_iso(e["time"]) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return merged[:EVENTS_PER_PROJECT]


def render_shipping_list(events):
    """Render the notebook-design shipped line, or empty string if no events.

    Emits <p class="nb-card-shipped"> with an accent "↑ shipped:" label, the
    event link, and a bare <time data-rel> element (data-rel drives the live-
    relative upgrade in script.js — no class needed). Matches the static
    placeholder format in now/index.html.
    """
    if not events:
        return ""
    items = []
    for ev in events:
        # Truncate raw text first, then escape — slicing escaped HTML by char
        # count can split mid-entity (`&amp;` → `&am`).
        summary = escape_html((ev["summary"] or "")[:90])
        url = escape_html(safe_url(ev["url"]))
        when = relative_time_html(ev["time"])
        items.append(f'<a href="{url}" rel="noopener" target="_blank">{summary}</a> &middot; {when}')
    return (
        '          <p class="nb-card-shipped"><span class="accent">&uarr; shipped:</span> '
        + ' &middot; '.join(items)
        + '</p>\n'
    )


def most_recent_event_time(project, events_by_repo):
    """Return the datetime of the most recent shipping event for a project,
    or None if the project has no events in the current window."""
    shipping_repos = project.get("shipping_repos") or [project["repo"]]
    latest = None
    for r in shipping_repos:
        for ev in events_by_repo.get(r, []):
            t = _parse_iso(ev["time"])
            if t and (latest is None or t > latest):
                latest = t
    return latest


def classify_projects(events_by_slug, threshold_days=ACTIVE_THRESHOLD_DAYS):
    """Split projects into (active_slugs, backburner_slugs) by recency.

    `events_by_slug` is a mapping {slug: most_recent_event_datetime_or_None}.
    A project is "active" if its most recent event is strictly within
    `threshold_days` of now. A project with no events is back-burner.

    Edge case pinned: an event exactly `threshold_days` old (delta ==
    threshold) is back-burner — the comparison is strict less-than.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_days)
    active, backburner = [], []
    for slug, latest in events_by_slug.items():
        if latest is not None and latest > cutoff:
            active.append(slug)
        else:
            backburner.append(slug)
    return active, backburner


def render_card(project, tldr_html, shipping_html, now_str, *, compact):
    """Render the full <article class="nb-card"> markup for a project.

    Active cards (compact=False) sit in the /01 .nb-grid-1 list and include
    a status badge. Back-burner cards (compact=True) sit in the /02
    .nb-grid-2 grid without the badge — matching the prior hand-curated
    structure.

    The TLDR markers stay nested INSIDE the card so the existing
    per-project TLDR sync continues to work for downstream-repo edits.
    """
    name = escape_html(project.get("name", project["slug"]))
    url = escape_html(safe_url(project.get("url"), fallback="#"))
    url_label = escape_html(project.get("url_label", ""))
    status = escape_html(project.get("status_badge", ""))
    slug = project["slug"]
    article_class = "nb-card compact" if compact else "nb-card"

    head_lines = [
        f'        <article class="{article_class}">',
        '          <div class="nb-card-head">',
        f'            <h3 class="nb-card-name"><a href="{url}">{name}</a></h3>',
    ]
    if url_label:
        head_lines.append(f'            <a class="nb-card-url" href="{url}">{url_label}</a>')
    if status and not compact:
        head_lines.append(f'            <span class="nb-card-status">{status}</span>')
    head_lines.append('          </div>')

    body = (
        f'          <!-- TLDR-{slug}-START -->\n'
        f'\n'
        f'          <p class="nb-card-body">{tldr_html}</p>\n'
        f'          <div class="nb-card-footer">\n'
        f'{shipping_html}'
        f'          <p class="feed-updated">Auto-updated {now_str} via CLAUDE.md + GitHub events.</p>\n'
        f'          </div>\n'
        f'        \n'
        f'        <!-- TLDR-{slug}-END -->'
    )

    return "\n".join(head_lines) + "\n" + body + "\n        </article>"


def render_eyebrow(label, count):
    noun = "project" if count == 1 else "projects"
    return f"{label} &middot; {count} {noun}"


def render_block(tldr_html, shipping_html, now_str):
    """Assemble the full replacement HTML for a project's TLDR marker block.

    Sits inside an <article class="nb-card"> — emits .nb-card-body for the
    TLDR copy and .nb-card-shipped (via render_shipping_list) for the shipping
    line, matching the rest of the notebook design system. The trailing
    .feed-updated line keeps the generic "auto-updated" footer convention
    used by every cron-managed feed.
    """
    return (
        f"\n"
        f'          <p class="nb-card-body">{tldr_html}</p>\n'
        f'          <div class="nb-card-footer">\n'
        f"{shipping_html}"
        f'          <p class="feed-updated">Auto-updated {now_str} via CLAUDE.md + GitHub events.</p>\n'
        f'          </div>\n'
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
    now_str = format_update_time()

    # Per project: fetch TLDR from upstream CLAUDE.md, compute most-recent
    # event time, and stage the rendered card body. Projects with no TLDR
    # are tracked as failures and excluded from the rendered output.
    rendered = {}  # slug → (project, tldr_html, shipping_html, latest_dt)
    failures = []
    for project in projects:
        slug = project["slug"]
        repo = project["repo"]
        print(f"  {slug} ({repo}/CLAUDE.md):")
        markdown = fetch_file(repo, "CLAUDE.md", token)
        tldr = extract_tldr(markdown)
        if not tldr:
            failures.append(slug)
            print("    skipped (no TLDR content)")
            continue
        shipping_events = events_for_project(project, events_by_repo)
        shipping_html = render_shipping_list(shipping_events)
        latest_dt = most_recent_event_time(project, events_by_repo)
        rendered[slug] = (project, tldr, shipping_html, latest_dt)
        print(f"    ready ({len(shipping_events)} shipping event{'s' if len(shipping_events) != 1 else ''})")

    if failures and not rendered:
        record_heartbeat("projects", error=f"all {len(projects)} projects failed")
        print(f"All {len(projects)} projects failed — heartbeat recorded with error.")
        return

    # Classify by recency. classify_projects only knows about slugs that
    # had a TLDR; failures are skipped entirely (no empty card rendered).
    events_by_slug = {slug: data[3] for slug, data in rendered.items()}
    active_slugs, backburner_slugs = classify_projects(events_by_slug)

    # Order within each bucket: most-recent first for active (most-shipping
    # at the top); for back-burner, projects with any event sort newest-
    # first, then projects with no events in alphabetical slug order so
    # the layout is deterministic across runs.
    def _active_key(s):
        dt = events_by_slug.get(s)
        return dt or datetime.min.replace(tzinfo=timezone.utc)

    def _backburner_key(s):
        dt = events_by_slug.get(s)
        # Two-tier sort: has-events-newest-first, then no-events-alpha.
        if dt is not None:
            return (0, -dt.timestamp(), s)
        return (1, 0, s)

    active_slugs.sort(key=_active_key, reverse=True)
    backburner_slugs.sort(key=_backburner_key)

    # Render full card markup for each bucket.
    active_cards = "\n".join(
        render_card(rendered[s][0], rendered[s][1], rendered[s][2], now_str, compact=False)
        for s in active_slugs
    )
    backburner_cards = "\n".join(
        render_card(rendered[s][0], rendered[s][1], rendered[s][2], now_str, compact=True)
        for s in backburner_slugs
    )

    new_content = old_content
    new_content, ok1 = replace_marker(new_content, "ACTIVE-PROJECTS", active_cards)
    new_content, ok2 = replace_marker(new_content, "BACKBURNER-PROJECTS", backburner_cards)
    new_content, _ = replace_marker(
        new_content, "ACTIVE-EYEBROW", render_eyebrow("where the time is going", len(active_slugs))
    )
    new_content, _ = replace_marker(
        new_content, "BACKBURNER-EYEBROW", render_eyebrow("shipping but not daily", len(backburner_slugs))
    )

    if not (ok1 and ok2):
        record_heartbeat("projects", error="ACTIVE-PROJECTS or BACKBURNER-PROJECTS markers missing")
        print("ERROR: ACTIVE-PROJECTS / BACKBURNER-PROJECTS markers missing in now/index.html.")
        return

    if not content_changed(old_content, new_content):
        if failures:
            record_heartbeat("projects", error=f"skipped {len(failures)} project(s): {', '.join(failures)}")
        else:
            record_heartbeat("projects")
        print("No meaningful changes.")
        return

    write_now_html(new_content)
    if failures:
        record_heartbeat("projects", error=f"skipped {len(failures)} project(s): {', '.join(failures)}")
    else:
        record_heartbeat("projects")
    print(
        f"Updated now/index.html. Active: {len(active_slugs)} "
        f"({', '.join(active_slugs) or 'none'}); back-burner: {len(backburner_slugs)} "
        f"({', '.join(backburner_slugs) or 'none'}); failed: {len(failures)}."
    )


if __name__ == "__main__":
    main()
