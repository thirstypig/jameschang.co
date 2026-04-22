#!/usr/bin/env python3
"""Fetch Plex watch history and update /now/index.html.

Called by the GitHub Action on a 6-hour cron. Pulls recently watched
movies and TV episodes from the Plex Media Server API via relay.
Uses a static token (no OAuth rotation needed).
"""

import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from _shared import (
    escape_html,
    relative_time,
    replace_marker,
    record_heartbeat,
    content_changed,
    format_update_time,
    read_now_html,
    write_now_html,
    USER_AGENT,
)

PLEX_URL = os.environ.get("PLEX_URL", "")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN", "")
HISTORY_LIMIT = 10  # fetch more, deduplicate to ~5


def fetch_history():
    """Fetch recent watch history from Plex API.

    Returns a list of items on success (possibly empty if history is empty).
    Returns None on network/SSL failure so callers can distinguish
    "genuinely empty" from "couldn't reach the server" and preserve the
    last known state rather than overwriting with a fake empty block.
    """
    url = f"{PLEX_URL}/status/sessions/history/all?X-Plex-Token={PLEX_TOKEN}&sort=viewedAt:desc"
    req = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    })
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except (HTTPError, URLError, TimeoutError, OSError) as e:
        print(f"Plex fetch failed: {e}")
        return None

    items = data.get("MediaContainer", {}).get("Metadata", [])
    out = []
    seen = set()

    for item in items:
        typ = item.get("type")
        viewed_at = item.get("viewedAt", 0)
        iso_time = (
            datetime.fromtimestamp(viewed_at, tz=timezone.utc).isoformat()
            if viewed_at else None
        )

        if typ == "episode":
            show = item.get("grandparentTitle", "(unknown)")
            # Deduplicate by show name — show only most recent episode
            if show in seen:
                continue
            seen.add(show)
            out.append({
                "type": "tv",
                "title": show,
                "season": item.get("parentIndex"),
                "episode": item.get("index"),
                "episode_title": item.get("title", ""),
                "watched_at": iso_time,
            })
        elif typ == "movie":
            title = item.get("title", "(unknown)")
            if title in seen:
                continue
            seen.add(title)
            out.append({
                "type": "movie",
                "title": title,
                "year": item.get("year"),
                "watched_at": iso_time,
            })
        # Skip music tracks

        if len(out) >= 5:
            break

    return out


def build_html(items):
    """Return the HTML block for the PLEX markers."""
    parts = []

    if items:
        parts.append('        <p class="plex-heading"><strong>Recently on Plex</strong></p>')
        parts.append('        <ul class="plex-list">')
        for item in items:
            if item["type"] == "tv":
                label = escape_html(item["title"])
                if item.get("season") is not None and item.get("episode") is not None:
                    label += f' S{item["season"]:02d}E{item["episode"]:02d}'
                    if item.get("episode_title"):
                        label += f' &mdash; &ldquo;{escape_html(item["episode_title"])}&rdquo;'
            else:
                label = escape_html(item["title"])
                if item.get("year"):
                    label += f' ({item["year"]})'

            watched = relative_time(item.get("watched_at"))
            parts.append(f'          <li>{label} <span class="plex-when">&middot; {watched}</span></li>')
        parts.append('        </ul>')
    else:
        parts.append('        <p class="feed-empty">Nothing watched recently.</p>')

    now = format_update_time()
    parts.append(f'        <p class="feed-updated">Auto-updated {now} via Plex.</p>')

    return "\n".join(parts)


def main():
    if not PLEX_URL or not PLEX_TOKEN:
        print("ERROR: PLEX_URL and PLEX_TOKEN must be set.")
        sys.exit(1)

    items = fetch_history()
    if items is None:
        record_heartbeat("plex", error="fetch failed — preserving last known content")
        print("Plex fetch failed; leaving existing PLEX block untouched.")
        return

    html_block = build_html(items)

    old_content = read_now_html()
    new_content, replaced = replace_marker(old_content, "PLEX", html_block)
    if not replaced:
        print("ERROR: PLEX markers not found in now/index.html")
        sys.exit(1)

    if not content_changed(old_content, new_content):
        record_heartbeat("plex")
        print("No meaningful changes.")
        return

    write_now_html(new_content)
    record_heartbeat("plex")
    print(f"  Items: {len(items)}")
    for item in items:
        if item["type"] == "tv":
            print(f"    TV: {item['title']} S{item.get('season', 0):02d}E{item.get('episode', 0):02d}")
        else:
            print(f"    Movie: {item['title']} ({item.get('year', '?')})")


if __name__ == "__main__":
    main()
