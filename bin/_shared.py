"""Shared helpers for /now data-feed sync scripts.

Pure utility functions — no shared state, no side effects beyond file I/O.
"""

import json
import os
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

PACIFIC_TZ = ZoneInfo("America/Los_Angeles")


def format_update_time(now=None):
    """Return 'April 22, 2026 at 10:15 AM PDT' format for Auto-updated lines.

    Uses Pacific time (the site owner's home base). Accepts an optional
    datetime for testability; defaults to current time.
    """
    if now is None:
        now = datetime.now(PACIFIC_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=PACIFIC_TZ)
    else:
        now = now.astimezone(PACIFIC_TZ)
    return now.strftime("%B %d, %Y at %-I:%M %p %Z")

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
NOW_HTML = os.path.join(REPO_ROOT, "now", "index.html")
HEARTBEAT_FILE = os.path.join(REPO_ROOT, ".feeds-heartbeat.json")
USER_AGENT = "jameschang.co/1.0 (personal dashboard; +https://jameschang.co)"


def record_heartbeat(feed_name, error=None):
    """Record a timestamped heartbeat for a feed in .feeds-heartbeat.json."""
    data = {}
    if os.path.exists(HEARTBEAT_FILE):
        try:
            with open(HEARTBEAT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    now = datetime.now(timezone.utc).isoformat()
    existing = data.get(feed_name, {})
    entry = {"last_run_utc": now}
    if error:
        entry["last_error"] = str(error)[:200]
        if "last_success_utc" in existing:
            entry["last_success_utc"] = existing["last_success_utc"]
    else:
        entry["last_success_utc"] = now
    data[feed_name] = entry
    with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


_SAFE_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def safe_url(s, fallback="#"):
    """Return URL only if it has http(s) scheme; else fallback.

    Defends against javascript:/data:/file: URLs from upstream RSS feeds
    or third-party API responses that get rendered into <a href="…">.
    """
    if not s or not _SAFE_URL_RE.match(s):
        return fallback
    return s


def escape_html(s):
    """Escape all 5 HTML-significant characters (& < > " ')."""
    if s is None:
        return ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&#39;"))


def relative_time(iso_str):
    """Human-readable 'Nm ago' / 'Nh ago' / 'yesterday' / 'Nd ago'."""
    if not iso_str:
        return ""
    try:
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        t = datetime.fromisoformat(iso_str)
    except ValueError:
        return ""
    delta = datetime.now(timezone.utc) - t
    minutes = int(delta.total_seconds() / 60)
    if minutes < 60:
        return f"{minutes}m ago" if minutes > 0 else "just now"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days}d ago"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks}w ago"
    months = days // 30
    return f"{months}mo ago"


def relative_time_html(iso_str):
    """Return a <time datetime="..." data-rel> element for live-relative display.

    The server-rendered text (e.g. '7m ago') is the initial/no-JS fallback;
    the inline upgrader script in now/index.html recomputes textContent on
    page load and every minute thereafter, so the label stays truthful even
    when the last sync ran hours ago. Returns empty string for invalid input.
    """
    label = relative_time(iso_str)
    if not label or not iso_str:
        return ""
    # Normalize the datetime attribute to a UTC ISO-8601 string with Z suffix
    # so Date.parse() in the browser gets an unambiguous value.
    iso_norm = iso_str[:-1] + "+00:00" if iso_str.endswith("Z") else iso_str
    try:
        t_utc = datetime.fromisoformat(iso_norm).astimezone(timezone.utc)
    except ValueError:
        return ""
    stamp = t_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return f'<time datetime="{stamp}" data-rel>{label}</time>'


def replace_marker(content, marker_name, html):
    """Replace <!-- {MARKER}-START -->...<!-- {MARKER}-END --> in content.

    Validates exactly one occurrence exists. Returns (new_content, replaced).
    """
    pattern = rf"(<!-- {marker_name}-START -->).*?(<!-- {marker_name}-END -->)"
    count = len(re.findall(pattern, content, flags=re.DOTALL))
    if count == 0:
        print(f"WARNING: {marker_name}-START / -END markers not found in now/index.html")
        return content, False
    if count > 1:
        print(f"WARNING: {marker_name} markers found {count} times — expected 1. Skipping.")
        return content, False
    replacement = f"<!-- {marker_name}-START -->\n{html}\n        <!-- {marker_name}-END -->"
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    return new_content, True


_VOLATILE_DATE_RE = re.compile(
    r"Auto-updated [A-Z][a-z]+ \d+, \d{4}(?: at \d{1,2}:\d{2} [AP]M [A-Z]{2,4})?"
)
# Match the visible text inside a <time data-rel> element ("17h ago", "just now"
# etc.). The text reformats on every wall-clock minute via now/now.js, so
# without stripping it here every cron run sees a "diff" on a no-op rebuild
# and pushes a timestamp-only commit.
_VOLATILE_REL_TIME_RE = re.compile(
    r"(<time\b[^>]*\bdata-rel\b[^>]*>)[^<]*(</time>)"
)


def strip_volatile(content):
    """Strip time-volatile substrings so content-equality checks compare the
    upstream payload, not the wall-clock-driven 'Nm ago' / 'Auto-updated …'
    decorations. Keeps the surrounding <time datetime="..." data-rel> shell so
    structural diffs (added/removed feed entries) are still detected."""
    content = _VOLATILE_DATE_RE.sub("", content)
    content = _VOLATILE_REL_TIME_RE.sub(r"\1\2", content)
    return content


def content_changed(old_content, new_content):
    """Check if content changed meaningfully (ignoring time-volatile substrings)."""
    return strip_volatile(old_content) != strip_volatile(new_content)


def read_now_html():
    """Read now/index.html and return content string."""
    with open(NOW_HTML, "r", encoding="utf-8") as f:
        return f.read()


def write_now_html(content):
    """Write content to now/index.html.

    Also refreshes the top-of-page "Updated [timestamp]" eyebrow marker
    so every feed-sync keeps that line current as a side-effect — no
    separate writer needed.
    """
    content = _refresh_page_updated_marker(content)
    with open(NOW_HTML, "w", encoding="utf-8") as f:
        f.write(content)


def _refresh_page_updated_marker(content):
    """Update the <!-- PAGE-UPDATED-START -->...<!-- PAGE-UPDATED-END --> marker
    with the current timestamp. Silent if markers absent (so callers that
    render in-memory-only content aren't affected)."""
    pattern = r"<!-- PAGE-UPDATED-START -->.*?<!-- PAGE-UPDATED-END -->"
    replacement = f"<!-- PAGE-UPDATED-START -->{format_update_time()}<!-- PAGE-UPDATED-END -->"
    return re.sub(pattern, replacement, content, flags=re.DOTALL)


def fetch_json(url, timeout=15, headers=None):
    """GET JSON from a URL. Returns parsed dict or raises."""
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    req = Request(url, headers=hdrs)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def fetch_text(url, timeout=15):
    """GET text from a URL. Returns string or raises."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def sanitize_error(e):
    """Extract a safe error message from an HTTPError, stripping tokens."""
    msg = f"HTTP {e.code}"
    try:
        body = e.read().decode("utf-8", errors="replace")
        parsed = json.loads(body)
        safe_keys = {"error", "error_description", "error_hint", "status_code"}
        sanitized = {k: v for k, v in parsed.items() if k in safe_keys}
        msg += f" — {json.dumps(sanitized)}"
    except Exception:
        # Defensive: error bodies from upstream APIs come in unpredictable
        # shapes (HTML error pages, plain text, malformed JSON). Any parse
        # failure should yield a generic message rather than re-raising
        # mid-cron — the goal is to surface "request failed" cleanly.
        msg += " (could not parse error body)"
    return msg


def require_env(*names):
    """Verify required env vars are set; print missing list + exit 1 if any
    are absent. Replaces opaque KeyError tracebacks for cold-run failures
    (an agent or human running this script locally without the right
    env exported should see "Missing env vars: X, Y", not 30 lines of
    Python traceback)."""
    import sys as _sys
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        print(f"ERROR: missing env vars: {', '.join(missing)}", file=_sys.stderr)
        _sys.exit(1)
