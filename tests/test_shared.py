"""Unit tests for bin/_shared.py — the shared utility module for feed sync scripts."""

import json
import os
import sys
import tempfile

# Add bin/ to path so we can import _shared
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

from _shared import (
    _refresh_page_updated_marker,
    content_changed,
    escape_html,
    record_heartbeat,
    relative_time,
    relative_time_html,
    replace_marker,
    sanitize_error,
)


# ── escape_html ──────────────────────────────────────────────────

class TestEscapeHtml:
    def test_ampersand(self):
        assert escape_html("AT&T") == "AT&amp;T"

    def test_less_than(self):
        assert escape_html("<script>") == "&lt;script&gt;"

    def test_double_quote(self):
        assert escape_html('say "hello"') == "say &quot;hello&quot;"

    def test_single_quote(self):
        assert escape_html("it's") == "it&#39;s"

    def test_all_five_characters(self):
        assert escape_html("&<>\"'") == "&amp;&lt;&gt;&quot;&#39;"

    def test_none_returns_empty(self):
        assert escape_html(None) == ""

    def test_empty_string(self):
        assert escape_html("") == ""

    def test_no_special_chars(self):
        assert escape_html("hello world") == "hello world"

    def test_already_escaped_gets_double_escaped(self):
        assert escape_html("&amp;") == "&amp;amp;"


# ── relative_time ────────────────────────────────────────────────

class TestRelativeTime:
    def test_empty_string(self):
        assert relative_time("") == ""

    def test_none(self):
        assert relative_time(None) == ""

    def test_invalid_iso(self):
        assert relative_time("not-a-date") == ""

    def test_z_suffix_handled(self):
        # Should not raise — Z suffix is converted to +00:00
        from datetime import datetime, timezone
        recent = (datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")
        result = relative_time(recent)
        assert result in ("just now", "0m ago", "1m ago", "2m ago")

    def test_just_now(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        result = relative_time(now)
        assert result in ("just now", "0m ago", "1m ago")

    def test_hours_ago(self):
        from datetime import datetime, timedelta, timezone
        two_hours = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        assert relative_time(two_hours) == "2h ago"

    def test_yesterday(self):
        from datetime import datetime, timedelta, timezone
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1, hours=1)).isoformat()
        assert relative_time(yesterday) == "yesterday"

    def test_days_ago(self):
        from datetime import datetime, timedelta, timezone
        four_days = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        assert relative_time(four_days) == "4d ago"

    def test_weeks_ago(self):
        from datetime import datetime, timedelta, timezone
        two_weeks = (datetime.now(timezone.utc) - timedelta(weeks=2)).isoformat()
        assert relative_time(two_weeks) == "2w ago"

    def test_months_ago(self):
        from datetime import datetime, timedelta, timezone
        sixty_days = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        assert relative_time(sixty_days) == "2mo ago"


# ── relative_time_html ───────────────────────────────────────────

class TestRelativeTimeHtml:
    """Progressive-enhancement helper: wraps relative_time in a <time
    datetime="..." data-rel> element so client-side JS can recompute the
    label at view time instead of freezing it at sync time."""

    def test_returns_empty_on_empty_input(self):
        assert relative_time_html("") == ""
        assert relative_time_html(None) == ""

    def test_returns_empty_on_invalid_input(self):
        assert relative_time_html("not-a-date") == ""

    def test_wraps_recent_time_in_time_element(self):
        from datetime import datetime, timedelta, timezone
        recent = (datetime.now(timezone.utc) - timedelta(minutes=7)).isoformat()
        out = relative_time_html(recent)
        assert out.startswith('<time datetime="')
        assert 'data-rel' in out
        assert '>7m ago</time>' in out

    def test_normalizes_datetime_to_utc_z_suffix(self):
        """The datetime attribute must be parseable by Date.parse() unambiguously."""
        # Input with explicit +00:00 offset should normalize to Z.
        iso_with_offset = "2026-04-22T19:50:00+00:00"
        out = relative_time_html(iso_with_offset)
        assert 'datetime="2026-04-22T19:50:00Z"' in out

    def test_normalizes_z_suffix_input(self):
        iso_z = "2026-04-22T19:50:00Z"
        out = relative_time_html(iso_z)
        assert 'datetime="2026-04-22T19:50:00Z"' in out

    def test_converts_non_utc_offset_to_utc(self):
        """A Pacific-offset input should serialize as the equivalent UTC moment."""
        iso_pdt = "2026-04-22T12:50:00-07:00"  # = 19:50:00 UTC
        out = relative_time_html(iso_pdt)
        assert 'datetime="2026-04-22T19:50:00Z"' in out

    def test_label_matches_plain_relative_time(self):
        """The inner textContent must equal relative_time() output exactly —
        it's the no-JS fallback, so parity matters."""
        from datetime import datetime, timedelta, timezone
        t = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        html = relative_time_html(t)
        plain = relative_time(t)
        assert f'>{plain}</time>' in html


# ── replace_marker ───────────────────────────────────────────────

class TestReplaceMarker:
    def test_basic_replacement(self):
        content = "before <!-- TEST-START -->old stuff<!-- TEST-END --> after"
        new, replaced = replace_marker(content, "TEST", "<p>new</p>")
        assert replaced is True
        assert "<!-- TEST-START -->" in new
        assert "<p>new</p>" in new
        assert "<!-- TEST-END -->" in new
        assert "old stuff" not in new

    def test_preserves_surrounding_content(self):
        content = "HEADER <!-- X-START -->middle<!-- X-END --> FOOTER"
        new, replaced = replace_marker(content, "X", "replaced")
        assert new.startswith("HEADER ")
        assert new.endswith(" FOOTER")

    def test_missing_markers_returns_unchanged(self):
        content = "no markers here"
        new, replaced = replace_marker(content, "MISSING", "data")
        assert replaced is False
        assert new == content

    def test_duplicate_markers_returns_unchanged(self):
        content = (
            "<!-- DUP-START -->a<!-- DUP-END --> "
            "<!-- DUP-START -->b<!-- DUP-END -->"
        )
        new, replaced = replace_marker(content, "DUP", "data")
        assert replaced is False
        assert new == content

    def test_multiline_content_replaced(self):
        content = "<!-- ML-START -->\nline1\nline2\n<!-- ML-END -->"
        new, replaced = replace_marker(content, "ML", "<p>single</p>")
        assert replaced is True
        assert "<p>single</p>" in new
        assert "line1" not in new

    def test_empty_replacement(self):
        content = "<!-- E-START -->old<!-- E-END -->"
        new, replaced = replace_marker(content, "E", "")
        assert replaced is True
        assert "old" not in new


# ── content_changed ──────────────────────────────────────────────

class TestContentChanged:
    def test_identical_content(self):
        assert content_changed("hello", "hello") is False

    def test_different_content(self):
        assert content_changed("hello", "world") is True

    def test_only_date_changed(self):
        old = '<p>Auto-updated April 18, 2026</p>'
        new = '<p>Auto-updated April 19, 2026</p>'
        assert content_changed(old, new) is False

    def test_date_plus_real_change(self):
        old = '<p>Auto-updated April 18, 2026</p><p>score: 80</p>'
        new = '<p>Auto-updated April 19, 2026</p><p>score: 90</p>'
        assert content_changed(old, new) is True

    def test_no_date_in_content(self):
        assert content_changed("<p>a</p>", "<p>b</p>") is True


# ── _refresh_page_updated_marker ─────────────────────────────────

class TestPageUpdatedMarker:
    def test_replaces_content_between_markers(self):
        content = "<p>Updated <!-- PAGE-UPDATED-START -->stale<!-- PAGE-UPDATED-END --></p>"
        out = _refresh_page_updated_marker(content)
        assert "stale" not in out
        assert "<!-- PAGE-UPDATED-START -->" in out
        assert "<!-- PAGE-UPDATED-END -->" in out
        # Should contain a timestamp matching the format "Month Day, Year at H:MM AM/PM TZ"
        import re
        assert re.search(r"[A-Z][a-z]+ \d+, \d{4} at \d{1,2}:\d{2} [AP]M [A-Z]{2,4}", out)

    def test_no_markers_leaves_content_untouched(self):
        content = "<p>Nothing to see here</p>"
        assert _refresh_page_updated_marker(content) == content


# ── sanitize_error ───────────────────────────────────────────────

class TestSanitizeError:
    def _make_http_error(self, code, body):
        """Create a mock HTTPError with a readable body."""
        import io
        from urllib.error import HTTPError
        err = HTTPError(
            url="https://example.com",
            code=code,
            msg="Error",
            hdrs={},
            fp=io.BytesIO(body.encode()),
        )
        return err

    def test_json_error_body(self):
        err = self._make_http_error(401, '{"error": "invalid_grant", "secret_token": "LEAKED"}')
        result = sanitize_error(err)
        assert "HTTP 401" in result
        assert "invalid_grant" in result
        assert "LEAKED" not in result  # secret_token is not in safe_keys

    def test_non_json_body(self):
        err = self._make_http_error(500, "Internal Server Error")
        result = sanitize_error(err)
        assert "HTTP 500" in result
        assert "could not parse" in result

    def test_safe_keys_only(self):
        err = self._make_http_error(400, json.dumps({
            "error": "bad_request",
            "error_description": "missing param",
            "access_token": "SECRET123",
        }))
        result = sanitize_error(err)
        assert "bad_request" in result
        assert "missing param" in result
        assert "SECRET123" not in result


# ── record_heartbeat ─────────────────────────────────────────────

class TestRecordHeartbeat:
    def test_creates_new_file(self, tmp_path, monkeypatch):
        hb_file = tmp_path / ".feeds-heartbeat.json"
        import _shared
        monkeypatch.setattr(_shared, "HEARTBEAT_FILE", str(hb_file))

        record_heartbeat("test_feed")

        data = json.loads(hb_file.read_text())
        assert "test_feed" in data
        assert "last_run_utc" in data["test_feed"]
        assert "last_success_utc" in data["test_feed"]

    def test_error_preserves_last_success(self, tmp_path, monkeypatch):
        hb_file = tmp_path / ".feeds-heartbeat.json"
        import _shared
        monkeypatch.setattr(_shared, "HEARTBEAT_FILE", str(hb_file))

        record_heartbeat("feed1")
        data = json.loads(hb_file.read_text())
        success_time = data["feed1"]["last_success_utc"]

        record_heartbeat("feed1", error="API down")
        data = json.loads(hb_file.read_text())
        assert data["feed1"]["last_success_utc"] == success_time
        assert data["feed1"]["last_error"] == "API down"

    def test_survives_corrupt_json(self, tmp_path, monkeypatch):
        """If the heartbeat file contains invalid JSON, record_heartbeat
        should silently recover and write a fresh valid file."""
        hb_file = tmp_path / ".feeds-heartbeat.json"
        hb_file.write_text("{corrupt json!!! not valid")
        import _shared
        monkeypatch.setattr(_shared, "HEARTBEAT_FILE", str(hb_file))

        record_heartbeat("whoop")

        data = json.loads(hb_file.read_text())
        assert "whoop" in data
        assert "last_success_utc" in data["whoop"]

    def test_multiple_feeds(self, tmp_path, monkeypatch):
        hb_file = tmp_path / ".feeds-heartbeat.json"
        import _shared
        monkeypatch.setattr(_shared, "HEARTBEAT_FILE", str(hb_file))

        record_heartbeat("whoop")
        record_heartbeat("spotify")

        data = json.loads(hb_file.read_text())
        assert "whoop" in data
        assert "spotify" in data
