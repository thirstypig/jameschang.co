#!/usr/bin/env python3
"""Fetch latest WHOOP data and update /now/index.html.

Called by the GitHub Action on a daily cron. Uses an encrypted refresh token
file (.whoop-token.enc) that gets re-encrypted after each token rotation.
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
    replace_marker,
    record_heartbeat,
    sanitize_error,
    content_changed,
    format_update_time,
    read_now_html,
    write_now_html,
    NOW_HTML,
    USER_AGENT,
    REPO_ROOT,
)

API_BASE = "https://api.prod.whoop.com/developer/v2"
TOKEN_ENC = os.path.join(REPO_ROOT, ".whoop-token.enc")


def decrypt_refresh_token():
    """Decrypt the refresh token from .whoop-token.enc using WHOOP_TOKEN_KEY."""
    key = os.environ.get("WHOOP_TOKEN_KEY")
    if not key:
        print("ERROR: WHOOP_TOKEN_KEY not set.")
        sys.exit(1)
    if not os.path.exists(TOKEN_ENC):
        print(f"ERROR: {TOKEN_ENC} not found. Run bin/whoop-encrypt.sh first.")
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
    """Encrypt the refresh token to .whoop-token.enc."""
    key = os.environ.get("WHOOP_TOKEN_KEY")
    result = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "600000",
         "-out", TOKEN_ENC, "-pass", f"pass:{key}"],
        input=token, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Encryption failed: {result.stderr}")
        sys.exit(1)


def get_access_token():
    """Exchange refresh token for a fresh access token."""
    client_id = os.environ["WHOOP_CLIENT_ID"]
    client_secret = os.environ["WHOOP_CLIENT_SECRET"]
    refresh_token = decrypt_refresh_token()

    data = urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "https://jameschang.co/whoop/callback/",
        "scope": "read:recovery read:sleep read:workout read:cycles read:profile read:body_measurement offline",
    }).encode()

    req = Request(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(req) as resp:
            body = json.loads(resp.read())
    except HTTPError as e:
        print(f"Token refresh failed: {sanitize_error(e)}")
        sys.exit(1)

    new_refresh = body.get("refresh_token")
    return body["access_token"], new_refresh


def api_get(token, path, params=None):
    """GET request to WHOOP API."""
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
            return json.loads(resp.read())
    except HTTPError as e:
        print(f"API {path} failed: {sanitize_error(e)}")
        return {"records": []}


def fetch_latest_recovery(token):
    data = api_get(token, "/recovery", {"limit": "1"})
    records = data.get("records", [])
    if not records:
        return None
    score = records[0].get("score", {})
    return {
        "recovery_score": score.get("recovery_score"),
        "hrv": score.get("hrv_rmssd_milli"),
        "resting_hr": score.get("resting_heart_rate"),
    }


def fetch_latest_sleep(token):
    data = api_get(token, "/activity/sleep", {"limit": "1"})
    records = data.get("records", [])
    if not records:
        return None
    score = records[0].get("score", {})
    stages = score.get("stage_summary", {}) or {}
    # Actual sleep time = in-bed minus awake (matches what the WHOOP app displays)
    in_bed_ms = stages.get("total_in_bed_time_milli", 0)
    awake_ms = stages.get("total_awake_time_milli", 0)
    slept_ms = max(in_bed_ms - awake_ms, 0)
    hours = slept_ms // 3_600_000
    minutes = (slept_ms % 3_600_000) // 60_000
    return {
        "hours": hours,
        "minutes": minutes,
        "efficiency": score.get("sleep_efficiency_percentage"),
    }


def fetch_latest_cycle(token):
    data = api_get(token, "/cycle", {"limit": "1"})
    records = data.get("records", [])
    if not records:
        return None
    score = records[0].get("score", {})
    return {
        "day_strain": score.get("strain"),
    }


def recovery_color(score):
    """Maps a WHOOP recovery score (0-100) to a notebook .v color class.

    pos = WHOOP green (>= 67), warn = WHOOP yellow (34-66),
    danger = WHOOP red (< 34), muted = no data.
    """
    if score is None:
        return "muted"
    if score >= 67:
        return "pos"
    if score >= 34:
        return "warn"
    return "danger"


def _stat(key, value, color_class=""):
    """Render one .nb-stat tile."""
    v_class = f"v {escape_html(color_class)}".strip() if color_class else "v"
    return (
        '        <div class="nb-stat">\n'
        f'          <div class="k">{escape_html(key)}</div>\n'
        f'          <div class="{v_class}">{value}</div>\n'
        '        </div>'
    )


def build_html(recovery, sleep, cycle):
    """Emits a 4-tile nb-grid-4 (recovery, hrv, resting hr, sleep) plus an
    update-line that surfaces day-strain when available. The hand-crafted
    notebook /now placeholder used the same shape \u2014 preserving it here means
    every cron sync round-trips with no visual regression."""
    now = escape_html(format_update_time())
    tiles = []

    # Recovery \u2014 colored by WHOOP zone
    if recovery and recovery.get("recovery_score") is not None:
        score = recovery["recovery_score"]
        color = recovery_color(score)
        tiles.append(_stat("recovery", escape_html(f"{score:.0f}%"), color))
    else:
        tiles.append(_stat("recovery", "\u2014", "muted"))

    # HRV
    hrv_val = "\u2014"
    if recovery and recovery.get("hrv") is not None:
        hrv_val = escape_html(f'{recovery["hrv"]:.0f} ms')
    tiles.append(_stat("hrv", hrv_val))

    # Resting HR
    rhr_val = "\u2014"
    if recovery and recovery.get("resting_hr") is not None:
        rhr_val = escape_html(f'{recovery["resting_hr"]:.0f} bpm')
    tiles.append(_stat("resting hr", rhr_val))

    # Sleep
    if sleep:
        h, m = sleep["hours"], sleep["minutes"]
        sleep_val = escape_html(f"{h}h {m:02d}m")
    else:
        sleep_val = "\u2014"
    tiles.append(_stat("sleep", sleep_val))

    parts = ['      <div class="nb-grid-4">'] + tiles + ['      </div>']

    # Day strain + update timestamp on a single trailing line
    strain_suffix = ""
    if cycle and cycle.get("day_strain") is not None:
        strain_suffix = f' &middot; day strain {escape_html(f"{cycle["day_strain"]:.1f}")}'
    sleep_eff_suffix = ""
    if sleep and sleep.get("efficiency") is not None:
        sleep_eff_suffix = f' &middot; sleep efficiency {escape_html(f"{sleep["efficiency"]:.0f}%")}'
    parts.append(
        f'      <p class="feed-updated">Auto-updated {now} via <a href="https://www.whoop.com">WHOOP</a> API'
        f'{strain_suffix}{sleep_eff_suffix}</p>'
    )

    return "\n".join(parts)


def main():
    access_token, new_refresh = get_access_token()

    recovery = fetch_latest_recovery(access_token)
    sleep = fetch_latest_sleep(access_token)
    cycle = fetch_latest_cycle(access_token)

    html_block = build_html(recovery, sleep, cycle)

    old_content = read_now_html()
    new_content, replaced = replace_marker(old_content, "WHOOP", html_block)
    if not replaced:
        print("ERROR: WHOOP markers not found in now/index.html")
        sys.exit(1)

    if not content_changed(old_content, new_content):
        record_heartbeat("whoop")
        print("No meaningful changes")
        sys.exit(0)

    write_now_html(new_content)
    record_heartbeat("whoop")
    print(f"Updated {NOW_HTML} with latest WHOOP data.")

    # Encrypt the rotated refresh token AFTER successful write (todo 045)
    if new_refresh:
        encrypt_refresh_token(new_refresh)
        print("Refresh token rotated and re-encrypted.")

    if recovery and recovery["recovery_score"] is not None:
        print(f"  Recovery: {recovery['recovery_score']:.0f}%")
    if sleep:
        print(f"  Sleep: {sleep['hours']}h {sleep['minutes']:02d}m")
    if cycle and cycle.get("day_strain") is not None:
        print(f"  Strain: {cycle['day_strain']:.1f}")


if __name__ == "__main__":
    main()
