#!/usr/bin/env python3
"""Fetch latest WHOOP data and update /now/index.html.

Called by the GitHub Action on a daily cron. Reads secrets from environment
variables, fetches recovery + sleep + workout data, and replaces the
<!-- WHOOP-START --> / <!-- WHOOP-END --> block in now/index.html.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.parse import urlencode

API_BASE = "https://api.prod.whoop.com/developer/v1"
NOW_HTML = os.path.join(os.path.dirname(__file__), "..", "now", "index.html")
USER_AGENT = "jameschang.co/1.0 (WHOOP personal dashboard; +https://jameschang.co)"


def get_access_token():
    """Exchange refresh token for a fresh access token."""
    import base64

    client_id = os.environ["WHOOP_CLIENT_ID"]
    client_secret = os.environ["WHOOP_CLIENT_SECRET"]
    refresh_token = os.environ["WHOOP_REFRESH_TOKEN"]

    data = urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()

    # WHOOP expects HTTP Basic Auth (client_id:client_secret) for token requests
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    req = Request(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(req) as resp:
            body = json.loads(resp.read())
    except Exception as e:
        # Read the error response body for debugging
        if hasattr(e, "read"):
            error_body = e.read().decode("utf-8", errors="replace")
            print(f"Token refresh failed: {e}")
            print(f"Response body: {error_body}")
        else:
            print(f"Token refresh failed: {e}")
        sys.exit(1)

    # Update the refresh token secret if it rotated
    new_refresh = body.get("refresh_token")
    if new_refresh and new_refresh != refresh_token:
        print(f"::warning::WHOOP refresh token rotated. Update WHOOP_REFRESH_TOKEN secret.")

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
    with urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_latest_recovery(token):
    """Get the most recent recovery score."""
    data = api_get(token, "/recovery", {"limit": "1", "order": "desc"})
    records = data.get("records", [])
    if not records:
        return None
    score = records[0].get("score", {})
    return {
        "recovery_score": score.get("recovery_score"),
        "hrv": score.get("hrv_rmssd_milli"),
        "resting_hr": score.get("resting_heart_rate"),
        "spo2": score.get("spo2_percentage"),
    }


def fetch_latest_sleep(token):
    """Get the most recent sleep record."""
    data = api_get(token, "/activity/sleep", {"limit": "1", "order": "desc"})
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
        "performance": score.get("sleep_performance_percentage"),
    }


def fetch_latest_workout(token):
    """Get the most recent workout."""
    data = api_get(token, "/activity/workout", {"limit": "1", "order": "desc"})
    records = data.get("records", [])
    if not records:
        return None
    score = records[0].get("score", {})
    return {
        "strain": score.get("strain"),
        "kilojoules": score.get("kilojoule"),
    }


def fetch_latest_cycle(token):
    """Get the most recent cycle for day strain."""
    data = api_get(token, "/cycle", {"limit": "1", "order": "desc"})
    records = data.get("records", [])
    if not records:
        return None
    score = records[0].get("score", {})
    return {
        "day_strain": score.get("strain"),
        "day_kilojoules": score.get("kilojoule"),
    }


def recovery_color(score):
    """Map recovery score to a color class."""
    if score is None:
        return "muted"
    if score >= 67:
        return "green"
    if score >= 34:
        return "yellow"
    return "red"


def build_html(recovery, sleep, cycle):
    """Build the WHOOP stats HTML block."""
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")

    parts = []
    parts.append(f'        <p class="whoop-updated">Auto-updated {now} via <a href="https://www.whoop.com">WHOOP</a> API</p>')

    if recovery:
        score = recovery["recovery_score"]
        color = recovery_color(score)
        score_str = f"{score:.0f}%" if score is not None else "—"
        hrv_str = f'{recovery["hrv"]:.0f}ms' if recovery.get("hrv") else "—"
        rhr_str = f'{recovery["resting_hr"]:.0f}bpm' if recovery.get("resting_hr") else "—"
        parts.append(f'        <p><strong class="whoop-{color}">Recovery: {score_str}</strong> &middot; HRV: {hrv_str} &middot; Resting HR: {rhr_str}</p>')

    if sleep:
        h, m = sleep["hours"], sleep["minutes"]
        eff = f'{sleep["efficiency"]:.0f}%' if sleep.get("efficiency") else "—"
        parts.append(f'        <p>Sleep: {h}h {m:02d}m &middot; Efficiency: {eff}</p>')

    if cycle and cycle.get("day_strain") is not None:
        strain = f'{cycle["day_strain"]:.1f}'
        parts.append(f'        <p>Day Strain: {strain}</p>')

    return "\n".join(parts)


def update_now_html(html_block):
    """Replace the WHOOP marker block in now/index.html."""
    path = os.path.normpath(NOW_HTML)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(<!-- WHOOP-START -->).*?(<!-- WHOOP-END -->)"
    replacement = f"<!-- WHOOP-START -->\n{html_block}\n        <!-- WHOOP-END -->"

    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count == 0:
        print("ERROR: Could not find <!-- WHOOP-START --> / <!-- WHOOP-END --> markers in now/index.html")
        sys.exit(1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated {path} with latest WHOOP data.")


def main():
    token = get_access_token()
    recovery = fetch_latest_recovery(token)
    sleep = fetch_latest_sleep(token)
    cycle = fetch_latest_cycle(token)

    html = build_html(recovery, sleep, cycle)
    update_now_html(html)

    # Print summary
    if recovery and recovery["recovery_score"] is not None:
        print(f"  Recovery: {recovery['recovery_score']:.0f}%")
    if sleep:
        print(f"  Sleep: {sleep['hours']}h {sleep['minutes']:02d}m")
    if cycle and cycle.get("day_strain") is not None:
        print(f"  Strain: {cycle['day_strain']:.1f}")


if __name__ == "__main__":
    main()
