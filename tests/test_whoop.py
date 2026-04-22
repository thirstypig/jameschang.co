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
    def test_full_data(self):
        recovery = {"recovery_score": 81, "hrv": 30, "resting_hr": 64}
        sleep = {"hours": 7, "minutes": 30, "efficiency": 94}
        cycle = {"day_strain": 12.5}
        html = build_html(recovery, sleep, cycle)
        assert "Recovery: 81%" in html
        assert "whoop-green" in html
        assert "HRV: 30ms" in html
        assert "Sleep: 7h 30m" in html
        assert "Efficiency: 94%" in html
        assert "Day Strain: 12.5" in html

    def test_recovery_none_shows_dash(self):
        recovery = {"recovery_score": None, "hrv": None, "resting_hr": None}
        html = build_html(recovery, None, None)
        assert "whoop-muted" in html
        assert "\u2014" in html  # em dash for missing values

    def test_no_data_still_has_updated_line(self):
        html = build_html(None, None, None)
        assert "Auto-updated" in html
        assert "WHOOP" in html

    def test_yellow_recovery(self):
        recovery = {"recovery_score": 50, "hrv": 25, "resting_hr": 70}
        html = build_html(recovery, None, None)
        assert "whoop-yellow" in html

    def test_red_recovery(self):
        recovery = {"recovery_score": 20, "hrv": 15, "resting_hr": 80}
        html = build_html(recovery, None, None)
        assert "whoop-red" in html
