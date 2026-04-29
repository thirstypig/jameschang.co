#!/usr/bin/env python3
"""Fetch Trakt watch history and update /now/index.html.

DISABLED 2026-04-28: the workflow file was renamed to
`.github/workflows/trakt-sync.yml.disabled` so GitHub Actions no longer
invokes this script on a schedule. The script + tests are preserved.

To revive: (1) rename the workflow back to `.yml`, (2) restore the
<!-- TRAKT-START/END --> marker pair in now/index.html (probably under
the "tv" feed in /07 alongside Plex), (3) restore the Trakt disclosure
paragraph in privacy/index.html (see commit cede613 for the prior
wording — the paragraph mentioned "/users/me/history/shows" + the
read-only nature of the integration), and (4) update
tests/test_site_e2e.py: add TRAKT back to EXPECTED_MARKERS and add
"Trakt" to the privacy-policy required list.

Called by the GitHub Action on a 6-hour cron (when enabled). Uses an
encrypted refresh token file (.trakt-token.enc) that gets re-encrypted
after each token rotation. Same pattern as the WHOOP integration — see
docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from _shared import (
    escape_html,
    relative_time_html,
    replace_marker,
    record_heartbeat,
    sanitize_error,
    content_changed,
    format_update_time,
    read_now_html,
    write_now_html,
    USER_AGENT,
    REPO_ROOT,
)

API_BASE = "https://api.trakt.tv"
TOKEN_ENC = os.path.join(REPO_ROOT, ".trakt-token.enc")
SHOWS_LIMIT = 10  # fetch more, then deduplicate to ~5 unique shows


def decrypt_refresh_token():
    """Decrypt the refresh token from .trakt-token.enc using TRAKT_TOKEN_KEY."""
    key = os.environ.get("TRAKT_TOKEN_KEY")
    if not key:
        print("ERROR: TRAKT_TOKEN_KEY not set.")
        sys.exit(1)
    if not os.path.exists(TOKEN_ENC):
        print(f"ERROR: {TOKEN_ENC} not found. Run bin/trakt-encrypt.sh first.")
        sys.exit(1)
    result = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-d", "-pbkdf2", "-iter", "600000",
         "-in", TOKEN_ENC, "-pass", f"pass:{key}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Decryption failed: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()


def encrypt_refresh_token(token):
    """Encrypt the refresh token to .trakt-token.enc."""
    key = os.environ.get("TRAKT_TOKEN_KEY")
    result = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "600000",
         "-out", TOKEN_ENC, "-pass", f"pass:{key}"],
        input=token, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Encryption failed: {result.stderr}")
        sys.exit(1)


def get_access_token():
    """Exchange refresh token for a fresh access token. Returns (access, new_refresh)."""
    client_id = os.environ["TRAKT_CLIENT_ID"]
    client_secret = os.environ["TRAKT_CLIENT_SECRET"]
    refresh_token = decrypt_refresh_token()

    payload = json.dumps({
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "grant_type": "refresh_token",
    }).encode()

    req = Request(
        f"{API_BASE}/oauth/token",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )

    try:
        with urlopen(req) as resp:
            body = json.loads(resp.read())
    except HTTPError as e:
        print(f"Token refresh failed: {sanitize_error(e)}")
        sys.exit(1)

    return body["access_token"], body.get("refresh_token")


def api_get(token, path, params=None):
    """GET request to Trakt API."""
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "trakt-api-version": "2",
        "trakt-api-key": os.environ["TRAKT_CLIENT_ID"],
        "User-Agent": USER_AGENT,
    })
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        print(f"API {path} failed: {sanitize_error(e)}")
        return []


def fetch_recent_shows(token):
    """Return list of recently watched TV episodes, deduplicated by show."""
    data = api_get(token, "/users/me/history/shows", {"limit": str(SHOWS_LIMIT)})
    if not data:
        return []
    out = []
    seen_shows = set()
    for item in data:
        show = item.get("show") or {}
        episode = item.get("episode") or {}
        show_title = show.get("title", "(unknown)")

        # Deduplicate: show only the most recent episode per show
        if show_title in seen_shows:
            continue
        seen_shows.add(show_title)

        slug = show.get("ids", {}).get("slug", "")
        trakt_url = f"https://trakt.tv/shows/{slug}" if slug else ""
        out.append({
            "show": show_title,
            "season": episode.get("season"),
            "episode": episode.get("number"),
            "episode_title": episode.get("title", ""),
            "watched_at": item.get("watched_at"),
            "url": trakt_url,
        })
        if len(out) >= 5:
            break
    return out


def build_html(shows):
    """Return the HTML block for the TRAKT markers.

    Emits notebook-design markup: relies on .nb-feed (parent) for list and
    .when styling, and .feed-updated for the trailing timestamp. The redundant
    "Recently watched" heading is dropped — the parent .nb-feed-head already
    labels the feed as "tv".
    """
    parts = []

    if shows:
        parts.append('        <ul>')
        for s in shows:
            show_name = escape_html(s["show"])
            ep_label = ""
            if s.get("season") is not None and s.get("episode") is not None:
                ep_label = f' S{s["season"]:02d}E{s["episode"]:02d}'
                if s.get("episode_title"):
                    ep_label += f' &mdash; &ldquo;{escape_html(s["episode_title"])}&rdquo;'
            title_html = f'{show_name}{ep_label}'
            if s.get("url"):
                title_html = f'<a href="{escape_html(s["url"])}" rel="noopener" target="_blank">{title_html}</a>'
            watched = relative_time_html(s.get("watched_at"))
            parts.append(f'          <li>{title_html} <span class="when">&middot; {watched}</span></li>')
        parts.append('        </ul>')
    else:
        parts.append('        <p class="feed-empty">No shows tracked recently.</p>')

    now = format_update_time()
    parts.append(f'        <p class="feed-updated">Auto-updated {now} via <a href="https://trakt.tv">Trakt</a>.</p>')

    return "\n".join(parts)


def main():
    access_token, new_refresh = get_access_token()

    # Encrypt the rotated refresh token IMMEDIATELY (before any API calls)
    if new_refresh:
        encrypt_refresh_token(new_refresh)
        print("Refresh token rotated and re-encrypted.")

    shows = fetch_recent_shows(access_token)
    html_block = build_html(shows)

    old_content = read_now_html()
    new_content, replaced = replace_marker(old_content, "TRAKT", html_block)
    if not replaced:
        print("ERROR: TRAKT markers not found in now/index.html")
        sys.exit(1)

    if not content_changed(old_content, new_content):
        record_heartbeat("trakt")
        print("No meaningful changes.")
        return

    write_now_html(new_content)
    record_heartbeat("trakt")
    print(f"  Shows: {len(shows)}")
    for s in shows:
        ep = f"S{s['season']:02d}E{s['episode']:02d}" if s.get("season") else ""
        print(f"    {s['show']} {ep}")


if __name__ == "__main__":
    main()
