#!/usr/bin/env python3
"""Fetch project TLDR blocks from each repo's CLAUDE.md and update /now/index.html.

Called by the GitHub Action on a daily cron (7:00 AM PT). Reads the list of
projects from bin/projects-config.json. For each project, fetches the configured
file from GitHub via the raw API, extracts the <!-- now-tldr -->...<!-- /now-tldr -->
block, and replaces the matching <!-- TLDR-{slug}-START -->...<!-- TLDR-{slug}-END -->
block in now/index.html.

If a repo's file can't be fetched (network error, missing file, or missing marker),
the existing HTML content for that project is preserved — no "empty block" regression.
"""

import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from _shared import (
    content_changed,
    format_update_time,
    read_now_html,
    record_heartbeat,
    replace_marker,
    write_now_html,
    REPO_ROOT,
    USER_AGENT,
)

CONFIG_PATH = os.path.join(REPO_ROOT, "bin", "projects-config.json")
TLDR_PATTERN = re.compile(r"<!-- now-tldr -->\s*(.*?)\s*<!-- /now-tldr -->", re.DOTALL)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["projects"]


def fetch_file(repo, path, token):
    """Fetch a raw file from GitHub. Returns the content string or None on failure."""
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
    """Return the TLDR content from a markdown string, or None if no marker found."""
    if not markdown:
        return None
    m = TLDR_PATTERN.search(markdown)
    if not m:
        return None
    return m.group(1).strip()


def main():
    projects = load_config()
    token = os.environ.get("TLDR_FETCH_TOKEN", "").strip() or None
    if not token:
        print("WARNING: TLDR_FETCH_TOKEN not set — private repos will 404.")

    old_content = read_now_html()
    new_content = old_content
    updates = []
    failures = []

    for project in projects:
        slug = project["slug"]
        repo = project["repo"]
        path = project["file"]
        print(f"  {slug} ({repo}/{path}):")

        markdown = fetch_file(repo, path, token)
        tldr = extract_tldr(markdown)
        if not tldr:
            failures.append(slug)
            print("    skipped (no content to splice) — preserving existing HTML")
            continue

        html = f"      {tldr}"
        candidate, replaced = replace_marker(new_content, f"TLDR-{slug}", html)
        if not replaced:
            failures.append(slug)
            print(f"    skipped (markers <!-- TLDR-{slug}-START/END --> not found in now/index.html)")
            continue

        new_content = candidate
        updates.append(slug)
        print("    spliced")

    # Refresh the "projects sync" timestamp in the Active-section eyebrow
    now = format_update_time()
    banner = f"Project updates auto-sync from each repo's CLAUDE.md — last refresh {now}."
    new_content, _ = replace_marker(new_content, "PROJECTS-UPDATED", f"      <p class=\"feed-updated\">{banner}</p>")

    if not content_changed(old_content, new_content):
        record_heartbeat("projects")
        print("No meaningful changes.")
        return

    write_now_html(new_content)
    record_heartbeat(
        "projects",
        error=(f"failed for: {', '.join(failures)}" if failures else None),
    )
    print(f"Updated now/index.html. Spliced: {len(updates)}, failed: {len(failures)}.")


if __name__ == "__main__":
    main()
