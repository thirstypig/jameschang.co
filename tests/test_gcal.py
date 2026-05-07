"""Unit tests for bin/update-gcal.py — iCal parser + renderer."""

import importlib
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

gcal = importlib.import_module("update-gcal")

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "sample.ics")


def load_fixture():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return f.read()


# ── parser ───────────────────────────────────────────────────────

class TestParseIcal:
    def test_parse_ical_basic(self):
        events = gcal.parse_ical(load_fixture())
        assert len(events) == 4
        first = events[0]
        assert first["summary"] == "Joe Wong in Chinese"
        assert first["dtstart"] is not None
        assert first["uid"] == "event-1@example.com"

    def test_parse_handles_line_continuations(self):
        payload = (
            "BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "SUMMARY:This is a very long\n"
            " summary that wraps\n"
            "\tacross three lines\n"
            "DTSTART;VALUE=DATE:20260601\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )
        events = gcal.parse_ical(payload)
        assert len(events) == 1
        # RFC 5545 line folding: CRLF + single leading WSP is removed entirely.
        # Author must include the space themselves in the next line if needed.
        assert events[0]["summary"] == "This is a very longsummary that wrapsacross three lines"

    def test_parse_handles_escapes(self):
        events = gcal.parse_ical(load_fixture())
        # LOCATION:Pasadena Ice House\, Pasadena\, CA → commas decode literally
        assert events[0]["location"] == "Pasadena Ice House, Pasadena, CA"

    def test_parse_unescape_text_newlines_and_backslash(self):
        # \n decodes to literal newline, \\ to backslash
        assert gcal.unescape_text("line1\\nline2") == "line1\nline2"
        assert gcal.unescape_text("path\\\\to") == "path\\to"
        assert gcal.unescape_text("a\\;b\\,c") == "a;b,c"

    def test_parse_date_only_event(self):
        events = gcal.parse_ical(load_fixture())
        all_day = next(e for e in events if e["summary"] == "All-day all-hands")
        assert all_day["start_is_date"] is True
        assert all_day["dtstart"] == date(2026, 6, 10)
        assert all_day["dtend"] == date(2026, 6, 11)

    def test_parse_tzid_event(self):
        events = gcal.parse_ical(load_fixture())
        joe = events[0]
        assert isinstance(joe["dtstart"], datetime)
        assert joe["dtstart"].tzinfo is not None
        # 17:00 in Los_Angeles
        assert joe["dtstart"].hour == 17
        assert joe["start_is_date"] is False

    def test_parse_utc_event(self):
        events = gcal.parse_ical(load_fixture())
        utc_ev = next(e for e in events if e["summary"] == "UTC meeting")
        assert utc_ev["dtstart"].tzinfo is not None
        assert utc_ev["dtstart"].utcoffset().total_seconds() == 0


# ── filter / sort ────────────────────────────────────────────────

class TestFilter:
    def test_filters_past_events(self):
        events = gcal.parse_ical(load_fixture())
        # All fixture events are in 2026-06; "today" in 2026-12 → all dropped
        out = gcal.filter_and_sort(events, date(2026, 12, 1))
        assert out == []

    def test_keeps_future_events(self):
        events = gcal.parse_ical(load_fixture())
        out = gcal.filter_and_sort(events, date(2026, 6, 1))
        assert len(out) == 4
        # Sorted by start ascending
        starts = [e["_start_local"] for e in out]
        assert starts == sorted(starts)

    def test_keeps_event_starting_today(self):
        events = gcal.parse_ical(load_fixture())
        out = gcal.filter_and_sort(events, date(2026, 6, 8))
        # The 6/8 datetime event survives
        assert any(e["summary"] == "Joe Wong in Chinese" for e in out)

    def test_same_day_events_all_render(self):
        """Two events on the same calendar day → both render as separate cards.
        Every calendar entry shows up; no dedupe. Order is by start time
        ascending (filter_and_sort guarantees that)."""
        payload = (
            "BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\nUID:a@x\nSUMMARY:Morning event\n"
            "DTSTART;VALUE=DATE:20260801\nDTEND;VALUE=DATE:20260802\n"
            "END:VEVENT\n"
            "BEGIN:VEVENT\nUID:b@x\nSUMMARY:Evening event\n"
            "DTSTART;VALUE=DATE:20260801\nDTEND;VALUE=DATE:20260802\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )
        events = gcal.parse_ical(payload)
        html = gcal.build_html(events, date(2026, 7, 1))
        assert html is not None
        # Both same-day events render
        assert html.count("nb-cal-card") == 2
        assert "Morning event" in html
        assert "Evening event" in html

    def test_caps_at_max_upcoming(self):
        # Build (MAX_UPCOMING + 5) events so the cap is actually exercised.
        # Use a date range broad enough to spread across two months without
        # tripping the day-of-month upper bound.
        n = gcal.MAX_UPCOMING + 5
        lines = ["BEGIN:VCALENDAR"]
        for i in range(n):
            month = 7 + (i // 28)
            day = 1 + (i % 28)
            lines += [
                "BEGIN:VEVENT",
                f"UID:e{i}@x",
                f"SUMMARY:Event {i}",
                f"DTSTART;VALUE=DATE:2026{month:02d}{day:02d}",
                f"DTEND;VALUE=DATE:2026{month:02d}{day:02d}",
                "END:VEVENT",
            ]
        lines.append("END:VCALENDAR")
        events = gcal.parse_ical("\n".join(lines))
        html = gcal.build_html(events, date(2026, 7, 1))
        assert html is not None
        # Render count is exactly the cap, even though more events were available.
        assert html.count("nb-cal-card") == gcal.MAX_UPCOMING
        # Pin the documented value so a future bump is intentional, not silent.
        assert gcal.MAX_UPCOMING == 20


# ── render ───────────────────────────────────────────────────────

class TestRender:
    def test_renders_data_cal_end(self):
        events = gcal.parse_ical(load_fixture())
        html = gcal.build_html(events, date(2026, 6, 1))
        assert html is not None
        # Every card carries a data-cal-end attribute
        cards = html.split('class="nb-cal-card"')
        # First chunk is preamble (empty); the rest are cards. Each card chunk
        # must contain data-cal-end="YYYY-MM-DD"
        # Easier: count cards == count(data-cal-end=)
        assert html.count("nb-cal-card") == html.count("data-cal-end=")
        assert html.count("nb-cal-card") >= 4

    def test_escape_html_summary(self):
        payload = (
            "BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "SUMMARY:<script>alert('x')</script>\n"
            "DTSTART;VALUE=DATE:20260801\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )
        events = gcal.parse_ical(payload)
        html = gcal.build_html(events, date(2026, 7, 1))
        assert html is not None
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_no_url_no_anchor(self):
        payload = (
            "BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "SUMMARY:No link event\n"
            "DTSTART;VALUE=DATE:20260801\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )
        events = gcal.parse_ical(payload)
        html = gcal.build_html(events, date(2026, 7, 1))
        assert html is not None
        # No <a href=…>No link event…</a> wrapper since URL was absent
        assert 'href="">' not in html
        # The summary should appear unwrapped
        assert "No link event" in html
        # Confirm no anchor at all in this rendering (URL missing)
        assert '<a href=' not in html

    def test_multi_line_location_collapses_whitespace(self):
        """Google Calendar often returns LOCATION with embedded newlines —
        venue name then street address. The renderer must collapse to a single
        inline string so the rendered card doesn't look ragged in the source."""
        payload = (
            "BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "SUMMARY:Sketching at the museum\n"
            "DTSTART;VALUE=DATE:20260801\n"
            "LOCATION:Norton Simon Museum\\n411 West Colorado Boulevard\\, Pasadena\\, CA 91105\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )
        events = gcal.parse_ical(payload)
        html = gcal.build_html(events, date(2026, 7, 1))
        assert html is not None
        # No literal newlines should leak into the rendered card
        assert "Norton Simon Museum\n" not in html
        assert "Norton Simon Museum 411" in html  # collapsed to single space
        # Comma is escaped inside iCal LOCATION but should decode to a literal
        assert "Pasadena, CA 91105" in html

    def test_with_url_renders_anchor(self):
        events = gcal.parse_ical(load_fixture())
        html = gcal.build_html(events, date(2026, 6, 1))
        assert html is not None
        assert 'href="https://example.com/joe-wong"' in html
        assert 'rel="noopener"' in html
        assert 'target="_blank"' in html

    def test_javascript_url_not_rendered_as_anchor(self):
        payload = (
            "BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "SUMMARY:Bad URL event\n"
            "URL:javascript:alert(1)\n"
            "DTSTART;VALUE=DATE:20260801\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )
        events = gcal.parse_ical(payload)
        html = gcal.build_html(events, date(2026, 7, 1))
        assert html is not None
        assert "javascript:" not in html
        assert "<a " not in html

    def test_multi_day_all_day_renders_range(self):
        events = gcal.parse_ical(load_fixture())
        html = gcal.build_html(events, date(2026, 6, 1))
        assert html is not None
        # Multi-day BBQ contest: DTSTART 6/12, DTEND 6/14 (exclusive) → 6/12-6/13
        assert "Multi-day BBQ" in html
        assert 'data-cal-end="2026-06-13"' in html

    def test_source_tag_present(self):
        events = gcal.parse_ical(load_fixture())
        html = gcal.build_html(events, date(2026, 6, 1))
        assert html is not None
        assert "from google calendar" in html

    def test_build_html_empty_returns_none(self):
        assert gcal.build_html([], date(2026, 6, 1)) is None
