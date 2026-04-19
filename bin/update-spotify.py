#!/usr/bin/env python3
"""Fetch Spotify listening data and update /now/index.html.

Called by the GitHub Action on a 4-hour cron. Pulls recently-played music
tracks (always) and the currently-playing podcast episode (when one is
actively playing). Persists the last-seen podcast in .spotify-state.json
so the /now page can show it until superseded by a newer podcast, with a
7-day auto-age-out.
"""

import base64
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from _shared import (
    escape_html,
    relative_time,
    replace_marker,
    record_heartbeat,
    sanitize_error,
    content_changed,
    read_now_html,
    write_now_html,
    USER_AGENT,
    REPO_ROOT,
)

API_BASE = "https://api.spotify.com/v1"
TOKEN_URL = "https://accounts.spotify.com/api/token"
STATE_FILE = os.path.join(REPO_ROOT, ".spotify-state.json")
PODCAST_AGE_LIMIT = timedelta(days=7)
TRACKS_LIMIT = 5


def get_access_token():
    """Exchange refresh token for a fresh access token (client_secret_basic)."""
    client_id = os.environ["SPOTIFY_CLIENT_ID"]
    client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
    refresh_token = os.environ["SPOTIFY_REFRESH_TOKEN"]

    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()

    req = Request(TOKEN_URL, data=data, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {creds}",
        "User-Agent": USER_AGENT,
    })
    try:
        with urlopen(req) as resp:
            body = json.loads(resp.read())
    except HTTPError as e:
        print(f"Token refresh failed: {sanitize_error(e)}")
        sys.exit(1)

    return body["access_token"]


def api_get(token, path, params=None):
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    try:
        with urlopen(req) as resp:
            if resp.status == 204:
                return None
            return json.loads(resp.read())
    except HTTPError as e:
        print(f"API {path} failed: {sanitize_error(e)}")
        return None


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def fetch_recent_tracks(token):
    """Return list of last N music tracks, each as {name, artists, played_at}."""
    data = api_get(token, "/me/player/recently-played", {"limit": str(TRACKS_LIMIT)})
    if not data:
        return []
    out = []
    for item in data.get("items", []):
        track = item.get("track") or {}
        out.append({
            "name": track.get("name", "(unknown)"),
            "artists": ", ".join(a.get("name", "") for a in track.get("artists", [])),
            "played_at": item.get("played_at"),
            "url": (track.get("external_urls") or {}).get("spotify"),
        })
    return out


def fetch_current_podcast(token):
    """Return podcast info if one is actively playing, else None."""
    data = api_get(token, "/me/player/currently-playing", {"additional_types": "episode"})
    if not data or not data.get("is_playing"):
        return None
    item = data.get("item") or {}
    if item.get("type") != "episode":
        return None
    return {
        "episode": item.get("name"),
        "show": (item.get("show") or {}).get("name"),
        "url": (item.get("external_urls") or {}).get("spotify"),
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def build_html(tracks, podcast):
    """Return the HTML block between the WHOOP-style markers."""
    parts = []

    # Podcast line (if fresh)
    if podcast:
        show = podcast.get("show") or ""
        episode = podcast.get("episode") or ""
        url = podcast.get("url")
        captured = relative_time(podcast.get("captured_at"))
        label_html = f'<em>{escape_html(show)}</em> &mdash; &ldquo;{escape_html(episode)}&rdquo;'
        if url:
            label_html = f'<a href="{escape_html(url)}" rel="noopener" target="_blank">{label_html}</a>'
        parts.append(f'        <p class="spotify-podcast"><strong>Last podcast:</strong> {label_html} &middot; heard {captured}</p>')

    # Tracks list
    if tracks:
        parts.append('        <p class="spotify-heading"><strong>Recently on Spotify</strong></p>')
        parts.append('        <ul class="spotify-list">')
        for t in tracks:
            name = escape_html(t["name"])
            artists = escape_html(t["artists"])
            played = relative_time(t.get("played_at"))
            title_html = f'&ldquo;{name}&rdquo; &mdash; {artists}'
            if t.get("url"):
                title_html = f'<a href="{escape_html(t["url"])}" rel="noopener" target="_blank">{title_html}</a>'
            parts.append(f'          <li>{title_html} <span class="spotify-when">&middot; {played}</span></li>')
        parts.append('        </ul>')

    if not parts:
        parts.append('        <p class="spotify-empty">Nothing recent &mdash; the Action runs every few hours.</p>')

    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    parts.append(f'        <p class="spotify-updated">Auto-updated {now} via <a href="https://developer.spotify.com/documentation/web-api">Spotify Web API</a>.</p>')

    return "\n".join(parts)




def main():
    token = get_access_token()

    tracks = fetch_recent_tracks(token)
    current = fetch_current_podcast(token)

    state = load_state()
    podcast = state.get("last_podcast")
    state_dirty = False

    if current:
        podcast = current
        state["last_podcast"] = podcast
        state_dirty = True
        print(f"Captured podcast: {current['show']} — {current['episode']}")
    elif podcast:
        try:
            captured = datetime.fromisoformat(podcast["captured_at"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - captured > PODCAST_AGE_LIMIT:
                print(f"Stale podcast (>{PODCAST_AGE_LIMIT.days}d old), hiding.")
                podcast = None
        except (KeyError, ValueError, TypeError):
            podcast = None

    html_block = build_html(tracks, podcast)

    # Content-hash cache: skip HTML write if tracks + podcast haven't changed
    date_stripped = re.sub(r"Auto-updated [A-Z][a-z]+ \d+, \d{4}", "", html_block)
    tracks_hash = hashlib.sha1(date_stripped.encode()).hexdigest()[:12]
    old_hash = state.get("last_tracks_hash")

    if tracks_hash == old_hash and not state_dirty:
        record_heartbeat("spotify")
        print("Tracks + podcast unchanged, skipping write.")
        return

    state["last_tracks_hash"] = tracks_hash
    save_state(state)

    old_content = read_now_html()
    new_content, replaced = replace_marker(old_content, "SPOTIFY", html_block)
    if not replaced:
        print("ERROR: SPOTIFY markers not found in now/index.html")
        sys.exit(1)

    if not content_changed(old_content, new_content):
        record_heartbeat("spotify")
        print("No meaningful changes.")
        return

    write_now_html(new_content)
    record_heartbeat("spotify")
    print(f"  Tracks: {len(tracks)}")
    if podcast:
        print(f"  Podcast: {podcast.get('show')} — {podcast.get('episode')}")


if __name__ == "__main__":
    main()
