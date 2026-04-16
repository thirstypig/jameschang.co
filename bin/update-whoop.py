#!/usr/bin/env python3
"""Fetch latest WHOOP data and update /now/index.html.

Called by the GitHub Action on a daily cron. Uses an encrypted refresh token
file (.whoop-token.enc) that gets re-encrypted after each token rotation.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.prod.whoop.com/developer/v2"
REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
NOW_HTML = os.path.join(REPO_ROOT, "now", "index.html")
TOKEN_ENC = os.path.join(REPO_ROOT, ".whoop-token.enc")
USER_AGENT = "jameschang.co/1.0 (WHOOP personal dashboard; +https://jameschang.co)"


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
        ["openssl", "enc", "-aes-256-cbc", "-d", "-pbkdf2",
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
        ["openssl", "enc", "-aes-256-cbc", "-pbkdf2",
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
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"Token refresh failed: {e}")
        print(f"Response body: {error_body}")
        sys.exit(1)

    new_refresh = body.get("refresh_token")
    if new_refresh:
        encrypt_refresh_token(new_refresh)
        if new_refresh != refresh_token:
            print("Refresh token rotated and re-encrypted.")

    return body["access_token"]


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
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"API {path} failed: {e} — {error_body}")
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
    total_ms = score.get("total_in_bed_time_milli", 0)
    hours = total_ms // 3_600_000
    minutes = (total_ms % 3_600_000) // 60_000
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
    if score is None:
        return "muted"
    if score >= 67:
        return "green"
    if score >= 34:
        return "yellow"
    return "red"


def build_html(recovery, sleep, cycle):
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    parts = []
    parts.append(f'        <p class="whoop-updated">Auto-updated {now} via <a href="https://www.whoop.com">WHOOP</a> API</p>')

    if recovery:
        score = recovery["recovery_score"]
        color = recovery_color(score)
        score_str = f"{score:.0f}%" if score is not None else "\u2014"
        hrv_str = f'{recovery["hrv"]:.0f}ms' if recovery.get("hrv") else "\u2014"
        rhr_str = f'{recovery["resting_hr"]:.0f}bpm' if recovery.get("resting_hr") else "\u2014"
        parts.append(f'        <p><strong class="whoop-{color}">Recovery: {score_str}</strong> &middot; HRV: {hrv_str} &middot; Resting HR: {rhr_str}</p>')

    if sleep:
        h, m = sleep["hours"], sleep["minutes"]
        eff = f'{sleep["efficiency"]:.0f}%' if sleep.get("efficiency") else "\u2014"
        parts.append(f'        <p>Sleep: {h}h {m:02d}m &middot; Efficiency: {eff}</p>')

    if cycle and cycle.get("day_strain") is not None:
        strain = f'{cycle["day_strain"]:.1f}'
        parts.append(f'        <p>Day Strain: {strain}</p>')

    return "\n".join(parts)


def update_now_html(html_block):
    with open(NOW_HTML, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(<!-- WHOOP-START -->).*?(<!-- WHOOP-END -->)"
    replacement = f"<!-- WHOOP-START -->\n{html_block}\n        <!-- WHOOP-END -->"

    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count == 0:
        print("ERROR: Could not find <!-- WHOOP-START --> / <!-- WHOOP-END --> markers in now/index.html")
        sys.exit(1)

    with open(NOW_HTML, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated {NOW_HTML} with latest WHOOP data.")


def main():
    token = get_access_token()
    recovery = fetch_latest_recovery(token)
    sleep = fetch_latest_sleep(token)
    cycle = fetch_latest_cycle(token)

    html = build_html(recovery, sleep, cycle)
    update_now_html(html)

    if recovery and recovery["recovery_score"] is not None:
        print(f"  Recovery: {recovery['recovery_score']:.0f}%")
    if sleep:
        print(f"  Sleep: {sleep['hours']}h {sleep['minutes']:02d}m")
    if cycle and cycle.get("day_strain") is not None:
        print(f"  Strain: {cycle['day_strain']:.1f}")


if __name__ == "__main__":
    main()
