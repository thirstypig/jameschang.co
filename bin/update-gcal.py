#!/usr/bin/env python3
"""Fetch a public Google Calendar iCal feed and render upcoming events on /now.

Reads the calendar's secret-by-obscurity iCal URL from `GCAL_ICAL_URL`,
parses VEVENTs with a hand-rolled stdlib parser, and writes up to
`MAX_UPCOMING` events as `.nb-cal-card` blocks between the
`<!-- GCAL-START -->` / `<!-- GCAL-END -->` markers in `now/index.html`.

Each card carries `data-cal-end="YYYY-MM-DD"` so `now/now.js` auto-prunes
past events client-side. We also filter past events server-side, so the
auto-prune is a backstop for stale renders, not the primary filter.

Stdlib only — no `icalendar` pip dependency.
"""

import os
import sys
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from _shared import (
    USER_AGENT,
    content_changed,
    escape_html,
    read_now_html,
    record_heartbeat,
    replace_marker,
    write_now_html,
)

PT = ZoneInfo("America/Los_Angeles")
MAX_UPCOMING = 6
MARKER = "GCAL"
SOURCE_TAG = "from google calendar"
MONTH_ABBR = ["jan", "feb", "mar", "apr", "may", "jun",
              "jul", "aug", "sep", "oct", "nov", "dec"]
MONTH_FULL = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]

FALLBACK_HTML = '        <p class="feed-empty">No upcoming events on the calendar feed.</p>'


# ─────────── iCal fetch ───────────

def fetch_ical(url: str, timeout: int = 20) -> str:
    """GET the iCal payload. Errors do NOT include the URL (it's a secret)."""
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/calendar"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


# ─────────── iCal parsing ───────────

def unfold_lines(payload: str) -> list[str]:
    """Reassemble RFC 5545 line continuations.

    A line beginning with a single space or tab is a continuation of the
    previous line; the leading whitespace is dropped.
    """
    lines: list[str] = []
    for raw in payload.splitlines():
        if not raw:
            continue
        if raw[0] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def unescape_text(s: str) -> str:
    """Decode iCal TEXT escapes: \\, \\;, \\n, \\\\."""
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in (",", ";", "\\"):
                out.append(nxt)
                i += 2
                continue
            if nxt in ("n", "N"):
                out.append("\n")
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


def split_property(line: str) -> tuple[str, dict, str]:
    """Split an iCal content line into (name, params, value).

    `name` is upper-cased. `params` maps PARAM-NAME to its value
    (param values are NOT unescaped — they're plain ASCII tokens like
    TZID names or VALUE=DATE).
    """
    colon = line.find(":")
    if colon < 0:
        return line.upper(), {}, ""
    head = line[:colon]
    value = line[colon + 1:]
    # Split head on ; — first chunk is property name, rest are params
    chunks = head.split(";")
    name = chunks[0].upper()
    params: dict[str, str] = {}
    for chunk in chunks[1:]:
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            params[k.upper()] = v
    return name, params, value


def parse_dt(value: str, params: dict) -> tuple[datetime | date, bool]:
    """Parse an iCal date/datetime value.

    Returns (value, is_date_only). For datetime values the result is
    timezone-aware. For DATE-only values it's a `date`.
    """
    if params.get("VALUE", "").upper() == "DATE" or len(value) == 8:
        # YYYYMMDD
        return date(int(value[0:4]), int(value[4:6]), int(value[6:8])), True

    # YYYYMMDDTHHMMSS[Z]
    main = value
    is_utc = main.endswith("Z")
    if is_utc:
        main = main[:-1]
    if "T" not in main:
        # Bare date that didn't pass the 8-char check — fall back
        return date(int(main[0:4]), int(main[4:6]), int(main[6:8])), True
    d, t = main.split("T", 1)
    dt = datetime(
        int(d[0:4]), int(d[4:6]), int(d[6:8]),
        int(t[0:2]), int(t[2:4]), int(t[4:6]) if len(t) >= 6 else 0,
    )
    if is_utc:
        return dt.replace(tzinfo=timezone.utc), False
    tzid = params.get("TZID")
    if tzid:
        try:
            return dt.replace(tzinfo=ZoneInfo(tzid)), False
        except ZoneInfoNotFoundError:
            # Unknown TZID — fall through to floating local; treat as Pacific
            pass
    # Floating time — interpret as Pacific (site owner's locale)
    return dt.replace(tzinfo=PT), False


def parse_ical(payload: str) -> list[dict]:
    """Return a list of VEVENT dicts.

    Each dict has keys: summary, location, url, uid, dtstart, dtend,
    start_is_date, end_is_date. Missing fields are empty string / None.
    """
    lines = unfold_lines(payload)
    events: list[dict] = []
    cur: dict | None = None
    for line in lines:
        name, params, value = split_property(line)
        if name == "BEGIN" and value.upper() == "VEVENT":
            cur = {
                "summary": "",
                "location": "",
                "url": "",
                "uid": "",
                "dtstart": None,
                "dtend": None,
                "start_is_date": False,
                "end_is_date": False,
            }
            continue
        if name == "END" and value.upper() == "VEVENT":
            if cur is not None:
                events.append(cur)
            cur = None
            continue
        if cur is None:
            continue
        if name == "SUMMARY":
            cur["summary"] = unescape_text(value)
        elif name == "LOCATION":
            cur["location"] = unescape_text(value)
        elif name == "URL":
            cur["url"] = value.strip()
        elif name == "UID":
            cur["uid"] = value.strip()
        elif name == "DTSTART":
            try:
                cur["dtstart"], cur["start_is_date"] = parse_dt(value, params)
            except (ValueError, IndexError):
                pass
        elif name == "DTEND":
            try:
                cur["dtend"], cur["end_is_date"] = parse_dt(value, params)
            except (ValueError, IndexError):
                pass
    return events


# ─────────── Filtering / rendering ───────────

def event_local_dates(event: dict) -> tuple[date, date]:
    """Return (start_date_local, end_date_inclusive_local) in Pacific time.

    For DATE-only events DTEND is exclusive per RFC 5545 — we subtract one
    day so a single-day all-day event has start==end and a Mon→Wed all-day
    event renders as Mon-Tue. For datetime events we treat DTEND as the
    last moment of the event and use its local calendar date.

    If DTEND is missing, end == start.
    """
    s = event["dtstart"]
    e = event.get("dtend") or s
    s_is_date = event.get("start_is_date")
    e_is_date = event.get("end_is_date")

    s_local = s.astimezone(PT).date() if isinstance(s, datetime) else s
    if isinstance(e, datetime):
        e_local = e.astimezone(PT).date()
    else:
        # all-day end is exclusive
        e_local = e - timedelta(days=1) if e_is_date and e > (s if s_is_date else s_local) else e
        if not isinstance(e_local, date):
            e_local = s_local
    if e_local < s_local:
        e_local = s_local
    return s_local, e_local


def filter_and_sort(events: list[dict], today: date) -> list[dict]:
    """Drop events whose end date is before `today`; sort by start ascending."""
    out = []
    for ev in events:
        if ev.get("dtstart") is None:
            continue
        try:
            s_local, e_local = event_local_dates(ev)
        except Exception:
            continue
        if e_local < today:
            continue
        ev["_start_local"] = s_local
        ev["_end_local"] = e_local
        out.append(ev)
    out.sort(key=lambda e: (e["_start_local"], e["_end_local"]))
    return out


def fmt_time_label(dt: datetime) -> str:
    """'5:00 PM' style, Pacific time."""
    local = dt.astimezone(PT)
    return local.strftime("%-I:%M %p")


def fmt_aria_range(s: date, e: date) -> str:
    if s == e:
        return f"{MONTH_FULL[s.month - 1]} {s.day}"
    if s.month == e.month:
        return f"{MONTH_FULL[s.month - 1]} {s.day} to {e.day}"
    return f"{MONTH_FULL[s.month - 1]} {s.day} to {MONTH_FULL[e.month - 1]} {e.day}"


def render_card(event: dict) -> str:
    """Render a single VEVENT as a `.nb-cal-card` block."""
    s_local: date = event["_start_local"]
    e_local: date = event["_end_local"]

    summary = event.get("summary") or "Untitled event"
    location = (event.get("location") or "").strip()
    url = (event.get("url") or "").strip()
    use_url = url.startswith("http://") or url.startswith("https://")

    # Date stamp on the left card
    mo = MONTH_ABBR[s_local.month - 1]
    day = f"{s_local.day:02d}"
    aria = fmt_aria_range(s_local, e_local)

    # Right-side "where + when" line
    is_datetime = isinstance(event.get("dtstart"), datetime) and not event.get("start_is_date")
    if s_local == e_local:
        if is_datetime:
            time_label = fmt_time_label(event["dtstart"])
            stamp = event["dtstart"].astimezone(PT).strftime("%Y-%m-%dT%H:%M")
            when_html = f'<time datetime="{stamp}">{mo} {s_local.day}, {time_label}</time>'
        else:
            when_html = f'<time datetime="{s_local.isoformat()}">{mo} {s_local.day}</time>'
    else:
        e_mo = MONTH_ABBR[e_local.month - 1]
        if s_local.month == e_local.month:
            when_html = (
                f'<time datetime="{s_local.isoformat()}">{mo} {s_local.day}</time>'
                f'&ndash;<time datetime="{e_local.isoformat()}">{e_local.day}</time>'
            )
        else:
            when_html = (
                f'<time datetime="{s_local.isoformat()}">{mo} {s_local.day}</time>'
                f'&ndash;<time datetime="{e_local.isoformat()}">{e_mo} {e_local.day}</time>'
            )

    summary_inner = escape_html(summary)
    if use_url:
        what_html = (
            f'<a href="{escape_html(url)}" rel="noopener" target="_blank">{summary_inner}</a>'
        )
    else:
        what_html = summary_inner

    where_parts = []
    if location:
        where_parts.append(escape_html(location))
    where_parts.append(when_html)
    where_html = " &middot; ".join(where_parts)

    lines = [
        f'        <div class="nb-cal-card" data-cal-end="{e_local.isoformat()}">',
        f'          <div class="nb-cal-date" aria-label="{escape_html(aria)}">',
        f'            <div class="mo">{mo}</div>',
        f'            <div class="day">{day}</div>',
        '          </div>',
        '          <div>',
        f'            <div class="nb-cal-tag">{SOURCE_TAG}</div>',
        f'            <div class="nb-cal-what">{what_html}</div>',
        f'            <div class="nb-cal-where">{where_html}</div>',
        '          </div>',
        '        </div>',
    ]
    return "\n".join(lines)


def build_html(events: list[dict], today: date) -> str | None:
    """Return rendered HTML for the GCAL marker block, or None on empty."""
    upcoming = filter_and_sort(events, today)[:MAX_UPCOMING]
    if not upcoming:
        return None
    return "\n".join(render_card(ev) for ev in upcoming)


# ─────────── Main ───────────

def main():
    url = os.environ.get("GCAL_ICAL_URL")
    if not url:
        print("ERROR: GCAL_ICAL_URL not set", file=sys.stderr)
        sys.exit(1)

    try:
        payload = fetch_ical(url)
    except HTTPError as e:
        print(f"GCAL fetch HTTP error: {e.code}", file=sys.stderr)
        record_heartbeat("gcal", error=f"HTTP {e.code}")
        return
    except (URLError, TimeoutError) as e:
        # Don't leak the URL — only the exception class name
        print(f"GCAL fetch error: {type(e).__name__}", file=sys.stderr)
        record_heartbeat("gcal", error=type(e).__name__)
        return
    except Exception as e:  # pragma: no cover — defensive
        print(f"GCAL fetch unexpected error: {type(e).__name__}", file=sys.stderr)
        record_heartbeat("gcal", error=type(e).__name__)
        return

    try:
        events = parse_ical(payload)
    except Exception as e:
        print(f"GCAL parse error: {type(e).__name__}", file=sys.stderr)
        record_heartbeat("gcal", error=f"parse: {type(e).__name__}")
        return

    today = datetime.now(PT).date()
    html = build_html(events, today)
    rendered = html if html else FALLBACK_HTML

    old_content = read_now_html()
    if f"<!-- {MARKER}-START -->" not in old_content:
        print(f"WARNING: {MARKER}-START / -END markers not present in now/index.html")
        record_heartbeat("gcal", error="markers missing")
        return

    new_content, _ = replace_marker(old_content, MARKER, rendered)

    # Always heartbeat success — fetch + parse worked even if no upcoming events.
    record_heartbeat("gcal", error=None)

    if not content_changed(old_content, new_content):
        print(f"GCAL: no meaningful changes ({len(events)} events parsed).")
        return

    write_now_html(new_content)
    upcoming_count = 0 if html is None else html.count("nb-cal-card")
    print(f"GCAL: rendered {upcoming_count} upcoming event(s).")


if __name__ == "__main__":
    main()
