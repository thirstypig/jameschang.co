#!/usr/bin/env python3
"""Check feed heartbeats; open / update / close GitHub issues accordingly.

Called by .github/workflows/feeds-staleness-check.yml on a 6-hour cron.
Runs on every main-branch push or scheduled trigger.

Definition of stale: a feed's `last_success_utc` is older than STALE_HOURS.
`last_run_utc` on its own doesn't count — a failing-but-running feed is
still broken (e.g., Plex fetch returns None yet the script exits cleanly).

Issue management:
- New stale feed: open issue with label `feed-stale`, title "Feed stale: {slug}".
- Already-open issue for this feed: add a comment if >6h since last comment.
- Feed recovered: close any open `feed-stale` issue for that feed.

Requires GH_TOKEN env var (provided by github.token in the workflow).

Local / agent use: set DRY_RUN=1 to print what would happen without making
any `gh issue create/close/comment` calls. Required for any cold-run
verification — running the script unguarded against the live repo will open
or close real issues.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

STALE_HOURS = 48
HEARTBEAT_FILE = os.path.join(os.path.dirname(__file__), "..", ".feeds-heartbeat.json")
DRY_RUN = bool(os.environ.get("DRY_RUN"))

# Actionable guidance per feed — shown in the GitHub issue body.
GUIDANCE = {
    "whoop": (
        "OAuth refresh token likely expired or `WHOOP_TOKEN_KEY` mismatch. "
        "Recovery: run `./bin/whoop-auth.sh` locally to get a fresh refresh token, "
        "then `./bin/whoop-encrypt.sh` to rewrite `.whoop-token.enc`. Commit and push."
    ),
    "spotify": (
        "Refresh token invalid. Run `./bin/spotify-auth.sh` and update the "
        "`SPOTIFY_REFRESH_TOKEN` GitHub Secret."
    ),
    "plex": (
        "Usually transient (SSL handshake against the Plex relay). If it persists "
        "past 48h, verify the `PLEX_URL` secret still points to an active relay."
    ),
    "mlb": "MLB Stats API is unauthenticated — usually self-resolves on the next cron.",
    "goodreads": "Goodreads RSS — verify user ID 33966778 is still valid.",
    "goodreads-reading": "See `goodreads` above — same RSS source.",
    "fbst": "The Fantastic Leagues standings endpoint. Check thefantasticleagues.com is reachable.",
    "projects": (
        "Project TLDR sync. Verify `TLDR_FETCH_TOKEN` secret is valid (fine-grained PATs "
        "expire; regenerate at github.com/settings/personal-access-tokens)."
    ),
}


def gh(*args):
    """Run a gh CLI command; return stdout or raise on failure."""
    is_write = args and args[0] in ("issue",) and len(args) > 1 and args[1] in ("create", "close", "comment")
    if DRY_RUN and is_write:
        print(f"[dry-run] would run: gh {' '.join(args)}")
        return ""
    result = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"gh {' '.join(args)} failed: {result.stderr.strip()}", file=sys.stderr)
        raise RuntimeError(result.stderr.strip())
    return result.stdout


def ensure_label(name, color, description):
    """Create the label if missing. No-op if already exists."""
    if DRY_RUN:
        print(f"[dry-run] would ensure label: {name}")
        return
    result = subprocess.run(
        ["gh", "label", "create", name, "--color", color, "--description", description],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"WARN: could not create label {name}: {result.stderr.strip()}", file=sys.stderr)


def load_heartbeats():
    with open(HEARTBEAT_FILE, encoding="utf-8") as f:
        return json.load(f)


def feed_age_hours(info, now):
    last = info.get("last_success_utc")
    if not last:
        return float("inf")
    try:
        parsed = datetime.fromisoformat(last)
    except ValueError:
        return float("inf")
    # Defensive: heartbeats are written tz-aware, but if the file is hand-
    # edited a naive timestamp would crash the subtraction. Treat naive as UTC.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (now - parsed).total_seconds() / 3600


def open_issues_by_feed():
    """Return {feed_slug: issue_number} for currently-open feed-stale issues."""
    raw = gh("issue", "list", "--label", "feed-stale", "--state", "open",
             "--json", "number,title")
    data = json.loads(raw or "[]")
    out = {}
    for issue in data:
        title = issue["title"]
        if title.startswith("Feed stale: "):
            slug = title[len("Feed stale: "):].strip()
            out[slug] = issue["number"]
    return out


def build_body(slug, info, hours):
    last_success = info.get("last_success_utc", "never")
    last_error = info.get("last_error", "none recorded")
    guidance = GUIDANCE.get(slug, "No specific guidance — investigate the workflow logs.")
    return (
        f"Feed `{slug}` has not had a successful sync in **{hours:.0f} hours**.\n\n"
        f"- **Last success (UTC):** `{last_success}`\n"
        f"- **Last error:** `{last_error}`\n\n"
        f"### What to do\n\n"
        f"{guidance}\n\n"
        f"---\n"
        f"_Auto-opened by `bin/check-feed-health.py`. Will auto-close when the feed recovers._"
    )


def main():
    try:
        data = load_heartbeats()
    except FileNotFoundError:
        print("::error::.feeds-heartbeat.json not found")
        sys.exit(1)

    ensure_label("feed-stale", "ED4245", "Feed has not had a successful sync in 48h")

    now = datetime.now(timezone.utc)
    open_issues = open_issues_by_feed()
    stale_opened = 0
    recovered_closed = 0

    for slug, info in sorted(data.items()):
        hours = feed_age_hours(info, now)
        is_stale = hours > STALE_HOURS
        issue_num = open_issues.get(slug)

        if is_stale and issue_num is None:
            body = build_body(slug, info, hours)
            gh("issue", "create",
               "--title", f"Feed stale: {slug}",
               "--body", body,
               "--label", "feed-stale",
               "--label", "bug")
            print(f"OPEN: {slug} ({hours:.0f}h stale)")
            stale_opened += 1
        elif is_stale and issue_num is not None:
            print(f"STALE (existing issue #{issue_num}): {slug} ({hours:.0f}h)")
        elif not is_stale and issue_num is not None:
            last_success = info.get("last_success_utc", "recently")
            gh("issue", "close", str(issue_num),
               "--comment",
               f"Feed `{slug}` recovered. Last success: `{last_success}` "
               f"({hours:.0f}h ago). Auto-closed by `bin/check-feed-health.py`.")
            print(f"CLOSE #{issue_num}: {slug} recovered")
            recovered_closed += 1
        else:
            print(f"OK: {slug} ({hours:.0f}h)")

    # Orphan cleanup: close any open feed-stale issues whose slug is no longer
    # in the heartbeat. Happens when a feed is renamed (e.g., "github" → folded
    # into "projects") or retired entirely. Without this pass the issue sits
    # forever — the main loop never visits it because `data.items()` skips it.
    heartbeat_slugs = set(data.keys())
    for slug, issue_num in open_issues.items():
        if slug not in heartbeat_slugs:
            gh("issue", "close", str(issue_num),
               "--comment",
               f"Feed `{slug}` is no longer tracked in `.feeds-heartbeat.json` "
               f"(renamed or retired). Auto-closed by `bin/check-feed-health.py`.")
            print(f"CLOSE #{issue_num}: {slug} (orphan — slug not in heartbeat)")
            recovered_closed += 1

    if DRY_RUN:
        print(f"\n[dry-run] Summary: {stale_opened} would open, {recovered_closed} would close.")
    else:
        print(f"\nSummary: {stale_opened} opened, {recovered_closed} closed.")


if __name__ == "__main__":
    main()
