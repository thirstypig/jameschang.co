"""Unit tests for bin/update-whoop.py — WHOOP data fetchers and rendering."""

import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

_whoop = importlib.import_module("update-whoop")
fetch_latest_recovery = _whoop.fetch_latest_recovery
fetch_latest_sleep = _whoop.fetch_latest_sleep
fetch_latest_cycle = _whoop.fetch_latest_cycle
build_html = _whoop.build_html


# ── fetch_latest_recovery ────────────────────────────────────────

class TestFetchLatestRecovery:
    def test_parses_recovery_data(self, monkeypatch):
        fake = {"records": [{"score": {
            "recovery_score": 81.0,
            "hrv_rmssd_milli": 30.5,
            "resting_heart_rate": 64.0,
        }}]}
        monkeypatch.setattr(_whoop, "api_get", lambda token, path, params=None: fake)
        result = fetch_latest_recovery("fake")
        assert result["recovery_score"] == 81.0
        assert result["hrv"] == 30.5
        assert result["resting_hr"] == 64.0

    def test_returns_none_on_empty_records(self, monkeypatch):
        monkeypatch.setattr(_whoop, "api_get", lambda token, path, params=None: {"records": []})
        assert fetch_latest_recovery("fake") is None

    def test_handles_missing_score_fields(self, monkeypatch):
        fake = {"records": [{"score": {}}]}
        monkeypatch.setattr(_whoop, "api_get", lambda token, path, params=None: fake)
        result = fetch_latest_recovery("fake")
        assert result["recovery_score"] is None
        assert result["hrv"] is None


# ── fetch_latest_sleep ───────────────────────────────────────────

class TestFetchLatestSleep:
    def test_calculates_sleep_duration(self, monkeypatch):
        fake = {"records": [{"score": {
            "stage_summary": {
                "total_in_bed_time_milli": 8 * 3_600_000,  # 8 hours
                "total_awake_time_milli": 30 * 60_000,      # 30 minutes
            },
            "sleep_efficiency_percentage": 94.0,
        }}]}
        monkeypatch.setattr(_whoop, "api_get", lambda token, path, params=None: fake)
        result = fetch_latest_sleep("fake")
        assert result["hours"] == 7
        assert result["minutes"] == 30
        assert result["efficiency"] == 94.0

    def test_returns_none_on_empty(self, monkeypatch):
        monkeypatch.setattr(_whoop, "api_get", lambda token, path, params=None: {"records": []})
        assert fetch_latest_sleep("fake") is None

    def test_handles_zero_sleep(self, monkeypatch):
        fake = {"records": [{"score": {"stage_summary": {
            "total_in_bed_time_milli": 0,
            "total_awake_time_milli": 0,
        }}}]}
        monkeypatch.setattr(_whoop, "api_get", lambda token, path, params=None: fake)
        result = fetch_latest_sleep("fake")
        assert result["hours"] == 0
        assert result["minutes"] == 0

    def test_awake_exceeds_in_bed_clamps_to_zero(self, monkeypatch):
        """If awake > in_bed (bad data), sleep should be 0, not negative."""
        fake = {"records": [{"score": {"stage_summary": {
            "total_in_bed_time_milli": 1_000_000,
            "total_awake_time_milli": 5_000_000,
        }}}]}
        monkeypatch.setattr(_whoop, "api_get", lambda token, path, params=None: fake)
        result = fetch_latest_sleep("fake")
        assert result["hours"] == 0
        assert result["minutes"] == 0

    def test_skips_nap_picks_main_sleep(self, monkeypatch):
        """A recent 30-min nap must not shadow last night's main sleep — the
        bug that showed '0h 30m' on /now while the app showed 5h 29m."""
        fake = {"records": [
            {"nap": True, "end": "2026-06-02T15:00:00.000Z", "score": {"stage_summary": {
                "total_in_bed_time_milli": 30 * 60_000,
                "total_awake_time_milli": 0,
            }}},
            {"nap": False, "end": "2026-06-02T07:00:00.000Z", "score": {"stage_summary": {
                "total_in_bed_time_milli": 6 * 3_600_000,
                "total_awake_time_milli": 31 * 60_000,
            }, "sleep_efficiency_percentage": 90.0}},
        ]}
        monkeypatch.setattr(_whoop, "api_get", lambda token, path, params=None: fake)
        result = fetch_latest_sleep("fake")
        assert (result["hours"], result["minutes"]) == (5, 29)  # 6h - 31m
        assert result["efficiency"] == 90.0

    def test_picks_most_recent_main_sleep_by_end(self, monkeypatch):
        """With two non-nap sleeps, the later `end` wins regardless of order."""
        fake = {"records": [
            {"nap": False, "end": "2026-05-30T07:00:00.000Z", "score": {"stage_summary": {
                "total_in_bed_time_milli": 4 * 3_600_000, "total_awake_time_milli": 0}}},
            {"nap": False, "end": "2026-06-02T07:00:00.000Z", "score": {"stage_summary": {
                "total_in_bed_time_milli": 8 * 3_600_000, "total_awake_time_milli": 0}}},
        ]}
        monkeypatch.setattr(_whoop, "api_get", lambda token, path, params=None: fake)
        result = fetch_latest_sleep("fake")
        assert result["hours"] == 8

    def test_all_naps_returns_none(self, monkeypatch):
        """If every recent record is a nap, report no main sleep (tile shows —)."""
        fake = {"records": [{"nap": True, "end": "2026-06-02T15:00:00.000Z", "score": {
            "stage_summary": {"total_in_bed_time_milli": 30 * 60_000, "total_awake_time_milli": 0}}}]}
        monkeypatch.setattr(_whoop, "api_get", lambda token, path, params=None: fake)
        assert fetch_latest_sleep("fake") is None


# ── fetch_latest_cycle ───────────────────────────────────────────

class TestFetchLatestCycle:
    def test_parses_strain(self, monkeypatch):
        fake = {"records": [{"score": {"strain": 12.5}}]}
        monkeypatch.setattr(_whoop, "api_get", lambda token, path, params=None: fake)
        result = fetch_latest_cycle("fake")
        assert result["day_strain"] == 12.5

    def test_returns_none_on_empty(self, monkeypatch):
        monkeypatch.setattr(_whoop, "api_get", lambda token, path, params=None: {"records": []})
        assert fetch_latest_cycle("fake") is None


# ── build_html ───────────────────────────────────────────────────

class TestWhoopBuildHtml:
    """build_html now emits a 4-tile nb-grid-4 (recovery/hrv/resting hr/sleep)
    plus a feed-updated line that surfaces day-strain and sleep-efficiency.
    See bin/update-whoop.py:build_html for the markup."""

    def test_full_data(self):
        recovery = {"recovery_score": 81, "hrv": 30, "resting_hr": 64}
        sleep = {"hours": 7, "minutes": 30, "efficiency": 94}
        cycle = {"day_strain": 12.5}
        html = build_html(recovery, sleep, cycle)
        # Grid container + 4 tiles
        assert '<div class="nb-grid-4">' in html
        assert html.count('<div class="nb-stat">') == 4
        # Recovery tile with pos color (score 81 = green zone)
        assert '<div class="k">recovery</div>' in html
        assert '<div class="v pos">81%</div>' in html
        # HRV / RHR / Sleep tiles
        assert '<div class="k">hrv</div>' in html
        assert "30 ms" in html
        assert '<div class="k">resting hr</div>' in html
        assert "64 bpm" in html
        assert '<div class="k">sleep</div>' in html
        assert "7h 30m" in html
        # Strain + efficiency surface in the feed-updated line
        assert "day strain 12.5" in html
        assert "sleep efficiency 94%" in html

    def test_recovery_none_shows_dash(self):
        recovery = {"recovery_score": None, "hrv": None, "resting_hr": None}
        html = build_html(recovery, None, None)
        assert '<div class="v muted">\u2014</div>' in html

    def test_no_data_still_has_updated_line(self):
        html = build_html(None, None, None)
        assert '<p class="feed-updated">Auto-updated' in html
        assert "WHOOP" in html
        # Even with no data, the 4 stat tiles still render with "\u2014"
        assert html.count('<div class="nb-stat">') == 4

    def test_warn_recovery(self):
        recovery = {"recovery_score": 50, "hrv": 25, "resting_hr": 70}
        html = build_html(recovery, None, None)
        assert '<div class="v warn">50%</div>' in html

    def test_danger_recovery(self):
        recovery = {"recovery_score": 20, "hrv": 15, "resting_hr": 80}
        html = build_html(recovery, None, None)
        assert '<div class="v danger">20%</div>' in html


class TestWhoopIdempotency:
    """WHOOP rendering must be deterministic: same input → same output.

    Guards against the trap where cron runs might accidentally corrupt
    or delete WHOOP data formatting.
    """

    def test_build_html_is_deterministic(self):
        """Same recovery/sleep/cycle → identical HTML output."""
        recovery = {"recovery_score": 81, "hrv": 30, "resting_hr": 64}
        sleep = {"hours": 7, "minutes": 30, "efficiency": 94}
        cycle = {"day_strain": 12.5}
        html1 = build_html(recovery, sleep, cycle)
        html2 = build_html(recovery, sleep, cycle)
        assert html1 == html2

    def test_none_data_is_deterministic(self):
        """None data must also produce consistent output."""
        html1 = build_html(None, None, None)
        html2 = build_html(None, None, None)
        assert html1 == html2

    def test_partial_data_is_deterministic(self):
        """Partial data (e.g., recovery + sleep, no cycle) stays consistent."""
        recovery = {"recovery_score": 75, "hrv": 28, "resting_hr": 62}
        sleep = {"hours": 6, "minutes": 45, "efficiency": 88}
        html1 = build_html(recovery, sleep, None)
        html2 = build_html(recovery, sleep, None)
        assert html1 == html2


# ── API-error handling (silent-403 regression) ───────────────────

class TestWhoopApiErrorSkipsHeartbeat:
    """A 403 on the data endpoints (token refresh still succeeds) must NOT refresh
    the health heartbeat and must leave /now untouched — otherwise a broken feed
    renders em-dash placeholders behind a fresh heartbeat and the staleness
    monitor never fires. Same failure class as the July 2026 Spotify outage;
    see docs/solutions/integration-issues/feed-heartbeat-on-noop-path-hides-upstream-api-failure.md."""

    def test_api_error_skips_heartbeat_and_leaves_page(self, monkeypatch):
        calls = {"heartbeat": 0, "write": 0}
        monkeypatch.setattr(_whoop, "require_env", lambda *a, **k: None)
        monkeypatch.setattr(_whoop, "get_access_token", lambda: ("tok", None))

        def fake_recovery(token):
            _whoop._api_error = True  # simulate api_get hitting a 403
            return None

        monkeypatch.setattr(_whoop, "fetch_latest_recovery", fake_recovery)
        monkeypatch.setattr(_whoop, "fetch_latest_sleep", lambda token: None)
        monkeypatch.setattr(_whoop, "fetch_latest_cycle", lambda token: None)
        monkeypatch.setattr(_whoop, "record_heartbeat",
                            lambda slug, **kw: calls.__setitem__("heartbeat", calls["heartbeat"] + 1))
        monkeypatch.setattr(_whoop, "write_now_html",
                            lambda content: calls.__setitem__("write", calls["write"] + 1))
        monkeypatch.setattr(_whoop, "_api_error", False)

        _whoop.main()

        assert calls["heartbeat"] == 0, "heartbeat must not be recorded on API error"
        assert calls["write"] == 0, "page must not be rewritten on API error"
