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
