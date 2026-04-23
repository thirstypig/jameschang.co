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


def fetch_recent_plays(token):
    """Return (tracks, episodes) from /me/player/recently-played.

    Without additional_types=episode, Spotify's recently-played endpoint
    returns tracks only — podcast plays are silently dropped. That left
    the "Last podcast" line dependent on /me/player/currently-playing,
    which only fires if a podcast is actively playing at cron time.
    Most episode plays were missed.

    With additional_types=episode we get tracks AND episodes in one
    response (up to 50 items), each with a real played_at timestamp.
    The client must inspect item.track.type to tell them apart.
    """
    data = api_get(token, "/me/player/recently-played", {
        "limit": "50",
        "additional_types": "episode",
    })
    if not data:
        return [], []
    tracks, episodes = [], []
    for item in data.get("items", []):
        inner = item.get("track") or {}
        played_at = item.get("played_at")
        if inner.get("type") == "episode":
            episodes.append({
                "episode": inner.get("name"),
                "show": (inner.get("show") or {}).get("name"),
                "url": (inner.get("external_urls") or {}).get("spotify"),
                "captured_at": played_at,
            })
        else:
            tracks.append({
                "name": inner.get("name", "(unknown)"),
                "artists": ", ".join(a.get("name", "") for a in inner.get("artists", [])),
                "played_at": played_at,
                "url": (inner.get("external_urls") or {}).get("spotify"),
            })
    return tracks[:TRACKS_LIMIT], episodes


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
        captured = relative_time_html(podcast.get("captured_at"))
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
            played = relative_time_html(t.get("played_at"))
            title_html = f'&ldquo;{name}&rdquo; &mdash; {artists}'
            if t.get("url"):
                title_html = f'<a href="{escape_html(t["url"])}" rel="noopener" target="_blank">{title_html}</a>'
            parts.append(f'          <li>{title_html} <span class="spotify-when">&middot; {played}</span></li>')
        parts.append('        </ul>')

    if not parts:
        parts.append('        <p class="spotify-empty">Nothing recent &mdash; the Action runs every few hours.</p>')

    now = format_update_time()
    parts.append(f'        <p class="spotify-updated">Auto-updated {now} via <a href="https://developer.spotify.com/documentation/web-api">Spotify Web API</a>.</p>')

    return "\n".join(parts)




def main():
    token = get_access_token()

    tracks, episodes = fetch_recent_plays(token)
    current = fetch_current_podcast(token)

    state = load_state()
    podcast = state.get("last_podcast")
    state_dirty = False

    # Prefer the most recent episode from listening history (real play
    # timestamp, captures episodes even if playback has since stopped).
    # Fall back to currently-playing (real-time snapshot) and then to
    # cached state (stale up to PODCAST_AGE_LIMIT).
    if episodes:
        podcast = episodes[0]
        state["last_podcast"] = podcast
        state_dirty = True
        print(f"Captured podcast from history: {podcast['show']} — {podcast['episode']}")
    elif current:
        podcast = current
        state["last_podcast"] = podcast
        state_dirty = True
        print(f"Captured podcast from currently-playing: {current['show']} — {current['episode']}")
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
    date_stripped = re.sub(r"Auto-updated [A-Z][a-z]+ \d+, \d{4}(?: at \d{1,2}:\d{2} [AP]M [A-Z]{2,4})?", "", html_block)
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
