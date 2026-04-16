"""Shared helpers for /now data-feed sync scripts.

Used by update-whoop.py, update-spotify.py, and update-public-feeds.py.
Pure utility functions — no shared state, no side effects beyond file I/O.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
NOW_HTML = os.path.join(REPO_ROOT, "now", "index.html")
USER_AGENT = "jameschang.co/1.0 (personal dashboard; +https://jameschang.co)"


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


def content_changed(old_content, new_content):
    """Check if content changed meaningfully (ignoring Auto-updated date lines)."""
    date_pattern = r"Auto-updated [A-Z][a-z]+ \d+, \d{4}"
    old_stripped = re.sub(date_pattern, "", old_content)
    new_stripped = re.sub(date_pattern, "", new_content)
    return old_stripped != new_stripped


def read_now_html():
    """Read now/index.html and return content string."""
    with open(NOW_HTML, "r", encoding="utf-8") as f:
        return f.read()


def write_now_html(content):
    """Write content to now/index.html."""
    with open(NOW_HTML, "w", encoding="utf-8") as f:
        f.write(content)


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
        msg += " (could not parse error body)"
    return msg
