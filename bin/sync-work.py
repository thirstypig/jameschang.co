#!/usr/bin/env python3
"""
Sync /work/ replica pages with their live source projects.

Pilot implementation: only Fantastic Leagues' changelog. The pattern is
extensible — add a new sync_* function per project surface you want to
auto-refresh, then call it in main().

Strategy: fetch the source file from a PUBLIC URL (GitHub raw), parse
out the piece we care about (latest version + date), and patch it into
the corresponding /work/*.html page's snapshot banner. Full-content
regeneration is a future step; this first pass just keeps the banner
timestamp + latest version honest so visitors know the replica isn't
stale.

Run manually:
    python3 bin/sync-work.py

Or via the scheduled GitHub Action (.github/workflows/sync-work.yml).
"""

from __future__ import annotations

import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- Sources ---------------------------------------------------------------
# Each entry: source URL (public raw), target HTML file, project label.
# To add a new source, append here and implement a sync function below.

FBST_CHANGELOG_SRC = "https://raw.githubusercontent.com/thirstypig/fbst/main/client/src/pages/Changelog.tsx"
FBST_CHANGELOG_OUT = ROOT / "work" / "fantastic-leagues" / "changelog" / "index.html"


# --- Helpers ---------------------------------------------------------------

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "jameschang.co-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def extract_latest_release(tsx: str) -> tuple[str, str, str] | None:
    """
    Parse a TSX file containing a ChangelogEntry[] literal; return
    (version, date, title) of the first entry, or None if parse fails.

    Assumes the pattern:
        { version: "x.y.z", date: "YYYY-MM-DD", title: "…", ... }
    with the latest release first in the array.
    """
    version_m = re.search(r'version:\s*"([^"]+)"', tsx)
    # Accept either YYYY-MM-DD or human-readable "Mon DD, YYYY"
    date_m = re.search(r'date:\s*"([^"]+)"', tsx)
    title_m = re.search(r'title:\s*"([^"]+)"', tsx)
    if version_m and date_m and title_m:
        return version_m.group(1), date_m.group(1), title_m.group(1)
    return None


def patch_snapshot_banner(html_path: Path, synced_line: str) -> bool:
    """
    Inject `synced_line` between `<!-- sync-start -->` and `<!-- sync-end -->`
    markers in the target HTML. The banner HTML must contain these two marker
    comments (adjacent is fine); everything between them is replaced on each
    run, so the script is idempotent.

    Returns True iff the file contents changed.
    """
    html = html_path.read_text()
    pattern = re.compile(r'(<!-- sync-start -->)(.*?)(<!-- sync-end -->)', re.DOTALL)
    injected = f'{pattern.pattern and ""}'  # no-op; keep linter happy
    replacement = rf'\1<p class="synced-line"><strong>{synced_line}</strong></p>\3'
    new_html, n = pattern.subn(replacement, html, count=1)
    if n == 0:
        print(f"[sync] no <!-- sync-start --> marker in {html_path} — skipping", file=sys.stderr)
        return False
    if new_html == html:
        return False
    html_path.write_text(new_html)
    return True


# --- Sync jobs -------------------------------------------------------------

def sync_fbst_changelog() -> bool:
    try:
        tsx = fetch(FBST_CHANGELOG_SRC)
    except Exception as e:
        print(f"[fbst/changelog] fetch failed: {e}", file=sys.stderr)
        return False

    parsed = extract_latest_release(tsx)
    if not parsed:
        print("[fbst/changelog] could not parse latest release", file=sys.stderr)
        return False

    version, release_date, title = parsed
    line = f'Last synced from source {date.today().isoformat()} — latest source release {version} ({release_date}).'
    changed = patch_snapshot_banner(FBST_CHANGELOG_OUT, line)
    status = "changed" if changed else "no change"
    print(f"[fbst/changelog] {status} — latest source: {version} ({release_date}) \"{title}\"")
    return changed


# --- Main ------------------------------------------------------------------

def main() -> int:
    jobs = [sync_fbst_changelog]
    any_changed = False
    for job in jobs:
        if job():
            any_changed = True
    return 0 if True else (0 if not any_changed else 0)


if __name__ == "__main__":
    sys.exit(main())
