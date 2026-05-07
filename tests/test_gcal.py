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

    def test_same_day_events_sort_by_time_of_day(self):
        """Two events on the same calendar day must order by their start time
        of day, not by iCal source order. A 3PM event renders before a 5PM
        event regardless of which one appeared first in the feed.
        Real-world case: Norton Simon at 3PM should appear before Joe Wong
        at 5PM on the same day."""
        # Build events out-of-order in the feed (5PM listed first) to prove
        # the sort overrides iCal insertion order.
        payload = (
            "BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\nUID:later@x\n"
            "SUMMARY:Five PM event\n"
            "DTSTART;TZID=America/Los_Angeles:20260509T170000\n"
            "DTEND;TZID=America/Los_Angeles:20260509T190000\n"
            "END:VEVENT\n"
            "BEGIN:VEVENT\nUID:earlier@x\n"
            "SUMMARY:Three PM event\n"
            "DTSTART;TZID=America/Los_Angeles:20260509T150000\n"
            "DTEND;TZID=America/Los_Angeles:20260509T170000\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )
        events = gcal.parse_ical(payload)
        out = gcal.filter_and_sort(events, date(2026, 5, 1))
        summaries = [e["summary"] for e in out]
        assert summaries == ["Three PM event", "Five PM event"]

    def test_all_day_event_sorts_as_midnight_against_timed(self):
        """All-day events get a synthetic midnight-PT start datetime, so they
        sort BEFORE timed events on the same day. (An all-day "weekend trip"
        shows above a 2pm meeting on the same start date.)"""
        payload = (
            "BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\nUID:a@x\nSUMMARY:All-day event\n"
            "DTSTART;VALUE=DATE:20260509\nDTEND;VALUE=DATE:20260510\n"
            "END:VEVENT\n"
            "BEGIN:VEVENT\nUID:b@x\nSUMMARY:Afternoon meeting\n"
            "DTSTART;TZID=America/Los_Angeles:20260509T140000\n"
            "DTEND;TZID=America/Los_Angeles:20260509T150000\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )
        events = gcal.parse_ical(payload)
        out = gcal.filter_and_sort(events, date(2026, 5, 1))
        summaries = [e["summary"] for e in out]
        assert summaries == ["All-day event", "Afternoon meeting"]

    def test_same_day_distinct_titles_render_separately(self):
        """Two events on the same day with DIFFERENT first-3-word prefixes
        render as separate cards (no grouping). 'Morning event' and 'Evening
        event' don't share a 3-word prefix, so they stay distinct."""
        payload = (
            "BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\nUID:a@x\nSUMMARY:Morning event with friends\n"
            "DTSTART;VALUE=DATE:20260801\nDTEND;VALUE=DATE:20260802\n"
            "END:VEVENT\n"
            "BEGIN:VEVENT\nUID:b@x\nSUMMARY:Evening dinner downtown\n"
            "DTSTART;VALUE=DATE:20260801\nDTEND;VALUE=DATE:20260802\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )
        events = gcal.parse_ical(payload)
        html = gcal.build_html(events, date(2026, 7, 1))
        assert html is not None
        assert html.count("nb-cal-card") == 2
        assert "Morning event with friends" in html
        assert "Evening dinner downtown" in html


class TestGroupByPrefix:
    """The grouping rule: consecutive events sharing the same first 3 words
    (lowercased, word-character runs only) collapse into one card spanning
    the union of start/end dates. Single-event groups pass through unchanged.
    """

    def _events_payload(self, *summaries_and_dates):
        """Helper: build a VCALENDAR with N events. summaries_and_dates is a
        flat list of (summary, YYYYMMDD start, YYYYMMDD end) tuples."""
        lines = ["BEGIN:VCALENDAR"]
        for i, (summary, start, end) in enumerate(summaries_and_dates):
            lines += [
                "BEGIN:VEVENT",
                f"UID:e{i}@x",
                f"SUMMARY:{summary}",
                f"DTSTART;VALUE=DATE:{start}",
                f"DTEND;VALUE=DATE:{end}",
                "END:VEVENT",
            ]
        lines.append("END:VCALENDAR")
        return "\n".join(lines)

    def test_first_n_words_key_uses_word_chars_only(self):
        # Punctuation, dashes, colons don't count as words
        assert gcal._first_n_words_key("Mini Takes The States - California") == ("mini", "takes", "the")
        assert gcal._first_n_words_key("Joe Wong in Chinese: 奈飞") == ("joe", "wong", "in")
        # Case-insensitive
        assert gcal._first_n_words_key("MINI TAKES the") == ("mini", "takes", "the")
        # Fewer than n words → None (no grouping key)
        assert gcal._first_n_words_key("Two words") is None

    def test_mini_style_grouping_5_entries_into_1_card(self):
        """The real-world MINI Takes The States case: 5 consecutive entries
        across Oct 2-4 collapse to one card spanning the range."""
        payload = self._events_payload(
            ("Mini Takes The States - California Day 1 - Monterey Rise", "20261002", "20261003"),
            ("Mini Takes The States - California Day 1 - Sonoma Evening", "20261002", "20261003"),
            ("Mini Takes The States - California Day 2 - Sonoma Rise", "20261003", "20261004"),
            ("Mini Takes The States - California Day 2 - Lake Tahoe", "20261003", "20261004"),
            ("Mini Takes The States - California Day 3 - Lake Tahoe", "20261004", "20261005"),
        )
        events = gcal.parse_ical(payload)
        html = gcal.build_html(events, date(2026, 9, 1))
        assert html is not None
        # 5 events → 1 card
        assert html.count("nb-cal-card") == 1
        # Title trimmed at first ' - '
        assert "Mini Takes The States" in html
        assert "California Day 1" not in html  # the verbose part dropped
        # Date range covers oct 2 (earliest start) to oct 4 (latest end day)
        assert 'data-cal-end="2026-10-04"' in html

    def test_smorgasburg_style_3_distinct_days_same_title(self):
        """Smorgasburg case: 3 entries with identical title on consecutive
        days collapse to one card spanning the 3-day range."""
        payload = self._events_payload(
            ("The Smorgasburg BBQ Invitational", "20260523", "20260524"),
            ("The Smorgasburg BBQ Invitational", "20260524", "20260525"),
            ("The Smorgasburg BBQ Invitational", "20260525", "20260526"),
        )
        events = gcal.parse_ical(payload)
        html = gcal.build_html(events, date(2026, 5, 1))
        assert html is not None
        assert html.count("nb-cal-card") == 1
        assert "The Smorgasburg BBQ Invitational" in html
        assert 'data-cal-end="2026-05-25"' in html

    def test_distinct_prefixes_dont_group(self):
        """'Joe Wong' and 'Norton Simon' on the same day don't share first 3
        words → render as two separate cards."""
        payload = self._events_payload(
            ("Joe Wong in Chinese", "20260509", "20260510"),
            ("Norton Simon Museum 2nd Saturday", "20260509", "20260510"),
        )
        events = gcal.parse_ical(payload)
        html = gcal.build_html(events, date(2026, 5, 1))
        assert html is not None
        assert html.count("nb-cal-card") == 2
        assert "Joe Wong in Chinese" in html
        assert "Norton Simon Museum 2nd Saturday" in html

    def test_far_apart_same_prefix_dont_group_via_consecutive_constraint(self):
        """Two events with matching first 3 words BUT separated in the sorted
        order by an unrelated event don't merge — the consecutive constraint
        protects against accidental merging of recurring weekly/monthly events."""
        payload = self._events_payload(
            ("Yankees vs Red Sox at home", "20260601", "20260602"),
            ("Joe Wong in Chinese", "20260615", "20260616"),  # interloper
            ("Yankees vs Red Sox in Boston", "20260701", "20260702"),
        )
        events = gcal.parse_ical(payload)
        html = gcal.build_html(events, date(2026, 5, 1))
        assert html is not None
        # Three groups of one each — no merging since Yankees events aren't consecutive
        assert html.count("nb-cal-card") == 3

    def test_single_event_group_passes_through_unchanged(self):
        """A standalone event (no neighbor with matching prefix) renders with
        its full original title — no trimming applied to single-event groups."""
        payload = self._events_payload(
            ("Nate Bargatze - Big Dumb Eyes World Tour - Netflix Fest", "20260510", "20260511"),
        )
        events = gcal.parse_ical(payload)
        html = gcal.build_html(events, date(2026, 5, 1))
        assert html is not None
        assert html.count("nb-cal-card") == 1
        # Full title kept (not trimmed at ' - ') because group size is 1
        assert "Big Dumb Eyes" in html

    def test_short_title_with_fewer_than_n_words_doesnt_group(self):
        """An event with only 2 words has no grouping key; consecutive 2-word
        events (even if they happen to share both words) stay as separate
        cards."""
        payload = self._events_payload(
            ("Open mic", "20260801", "20260802"),
            ("Open mic", "20260802", "20260803"),
        )
        events = gcal.parse_ical(payload)
        html = gcal.build_html(events, date(2026, 7, 1))
        assert html is not None
        assert html.count("nb-cal-card") == 2

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

    def test_no_source_tag_in_card(self):
        """Per-card source label was removed — the eyebrow at the top of /03
        ('via google calendar · auto-updated …') already signals where the
        events come from. Repeating it on every card is redundant."""
        events = gcal.parse_ical(load_fixture())
        html = gcal.build_html(events, date(2026, 6, 1))
        assert html is not None
        assert "from google calendar" not in html
        assert 'class="nb-cal-tag"' not in html

    def test_build_html_empty_returns_none(self):
        assert gcal.build_html([], date(2026, 6, 1)) is None
