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
import re
import sys
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from _shared import (
    USER_AGENT,
    content_changed,
    escape_html,
    format_update_time,
    read_now_html,
    record_heartbeat,
    replace_marker,
    write_now_html,
)

PT = ZoneInfo("America/Los_Angeles")
MAX_UPCOMING = 20
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


# ── Grouping rule ────────────────────────────────────────────────
#
# Events whose SUMMARY shares the same first N words AND that are consecutive
# in the sorted-by-date list collapse into a single card. The merged card
# spans the union of start/end dates (so a 3-day MINI trip with sub-events
# per day renders as one card "Oct 2–4"). The "consecutive" constraint
# prevents far-apart events with coincidentally-matching prefixes (recurring
# games, weekly classes) from being lumped together.

GROUP_PREFIX_WORDS = 3
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _first_n_words_key(summary: str, n: int = GROUP_PREFIX_WORDS):
    """Lowercase tuple of the first n word-sequences (regex \\w+) in summary.
    Returns None if there are fewer than n words — single-word titles never
    group into a multi-event card."""
    words = _WORD_RE.findall((summary or "").lower())
    return tuple(words[:n]) if len(words) >= n else None


def group_consecutive_by_prefix(events: list[dict], n: int = GROUP_PREFIX_WORDS) -> list[list[dict]]:
    """Walk sorted events; group consecutive ones with matching prefix key."""
    groups: list[list[dict]] = []
    current_key = None
    current: list[dict] = []
    for ev in events:
        key = _first_n_words_key(ev.get("summary"), n)
        if key is not None and key == current_key:
            current.append(ev)
        else:
            if current:
                groups.append(current)
            current = [ev]
            current_key = key
    if current:
        groups.append(current)
    return groups


def merge_group(group: list[dict]) -> dict:
    """Collapse a group of events into one. Single-event groups pass through.
    Multi-event groups: title is the first event's summary trimmed at the
    first ' - ' / ' · ' / ': ' separator; URL + location come from the first
    event; date range spans from the earliest start to the latest end."""
    first = group[0]
    if len(group) == 1:
        return first
    merged = dict(first)
    summary = first.get("summary") or ""
    for sep in (" - ", " · ", ": "):
        if sep in summary:
            summary = summary.split(sep, 1)[0].strip()
            break
    merged["summary"] = summary
    merged["_start_local"] = min(e["_start_local"] for e in group)
    merged["_end_local"] = max(e["_end_local"] for e in group)
    return merged


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

    summary = " ".join((event.get("summary") or "Untitled event").split())
    # Google Calendar often embeds newlines in LOCATION (e.g., venue name on
    # one line, street address on the next). Collapse all whitespace to single
    # spaces so the rendered card reads as one inline string.
    location = " ".join((event.get("location") or "").split())
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
    """Return rendered HTML for the GCAL marker block, or None on empty.

    Pipeline: filter past events → sort ascending → group consecutive events
    sharing the first GROUP_PREFIX_WORDS-word prefix → merge each group into
    one card with spanning date range → cap at MAX_UPCOMING. The cap counts
    rendered cards (post-grouping), so if MINI's 5 calendar entries collapse
    to 1 card, that's 1 of 20 slots used."""
    sorted_events = filter_and_sort(events, today)
    groups = group_consecutive_by_prefix(sorted_events)
    merged = [merge_group(g) for g in groups]
    upcoming = merged[:MAX_UPCOMING]
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

    # Eyebrow ("via google calendar · auto-updated …") — same "Auto-updated"
    # phrase as other feeds so _shared.strip_volatile() removes the timestamp
    # before content_changed() compares. Without that, every hourly sync would
    # produce a timestamp-only commit even on no-op runs.
    upcoming_count = 0 if html is None else html.count("nb-cal-card")
    eyebrow = (
        f"via google calendar &middot; "
        f"Auto-updated {format_update_time()} &middot; "
        f"{upcoming_count} upcoming"
    )

    old_content = read_now_html()
    if f"<!-- {MARKER}-START -->" not in old_content:
        print(f"WARNING: {MARKER}-START / -END markers not present in now/index.html")
        record_heartbeat("gcal", error="markers missing")
        return

    new_content, _ = replace_marker(old_content, MARKER, rendered)
    if f"<!-- {MARKER}-EYEBROW-START -->" in new_content:
        new_content, _ = replace_marker(new_content, f"{MARKER}-EYEBROW", eyebrow)

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
