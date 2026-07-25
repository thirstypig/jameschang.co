"""Tests for bin/check-expiry.py and the credential expiry registry."""

import importlib
import json
import os
import subprocess
import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))
ROOT = os.path.join(os.path.dirname(__file__), "..")


_expiry = None

def _load_module():
    global _expiry
    if _expiry is None:
        _expiry = importlib.import_module("check-expiry")
    return _expiry


class TestRegistryIsPrivate:
    def test_registry_local_is_never_tracked(self):
        """admin/registry.local.json is the credential map — it must never be
        committed to this public repo."""
        out = subprocess.run(
            ["git", "ls-files", "admin/registry.local.json"],
            cwd=ROOT, capture_output=True, text=True,
        ).stdout.strip()
        assert out == "", "admin/registry.local.json is tracked — remove it and confirm .gitignore"

    def test_registry_local_is_gitignored(self):
        code = subprocess.run(
            ["git", "check-ignore", "admin/registry.local.json"],
            cwd=ROOT, capture_output=True, text=True,
        ).returncode
        assert code == 0, "admin/registry.local.json is not gitignored"


class TestDaysUntil:
    def test_future_date(self):
        m = _load_module()
        assert m.days_until("2026-01-31", date(2026, 1, 1)) == 30

    def test_today_is_zero(self):
        m = _load_module()
        assert m.days_until("2026-01-01", date(2026, 1, 1)) == 0

    def test_past_is_negative(self):
        m = _load_module()
        assert m.days_until("2025-12-30", date(2026, 1, 1)) == -2


class TestBandFor:
    def test_outside_all_thresholds_is_none(self):
        m = _load_module()
        assert m.band_for(31) is None

    def test_just_inside_widest(self):
        m = _load_module()
        assert m.band_for(30) == 30
        assert m.band_for(15) == 30

    def test_tighter_bands(self):
        m = _load_module()
        assert m.band_for(14) == 14
        assert m.band_for(7) == 7
        assert m.band_for(1) == 1

    def test_expired_is_tightest_band(self):
        m = _load_module()
        assert m.band_for(0) == 1
        assert m.band_for(-5) == 1


class TestValidateRegistry:
    def test_unknown_key_raises(self):
        m = _load_module()
        with pytest.raises(ValueError, match="unknown key"):
            m.validate_registry({"integrations": [{"id": "x", "expires": "UNKNOWN", "typo": 1}]})

    def test_missing_id_raises(self):
        m = _load_module()
        with pytest.raises(ValueError, match="id"):
            m.validate_registry({"integrations": [{"expires": "UNKNOWN"}]})

    def test_duplicate_id_raises(self):
        m = _load_module()
        with pytest.raises(ValueError, match="duplicate"):
            m.validate_registry({"integrations": [
                {"id": "x", "expires": "UNKNOWN"},
                {"id": "x", "expires": "UNKNOWN"},
            ]})

    def test_malformed_date_raises(self):
        m = _load_module()
        with pytest.raises(ValueError):
            m.validate_registry({"integrations": [{"id": "x", "expires": "2026-13-99"}]})

    def test_unknown_expires_is_allowed(self):
        m = _load_module()
        out = m.validate_registry({"integrations": [{"id": "x", "expires": "UNKNOWN"}]})
        assert out == [{"id": "x", "expires": "UNKNOWN"}]


class TestLoadRegistry:
    def test_reads_env_var(self):
        m = _load_module()
        payload = json.dumps({"integrations": [{"id": "x", "expires": "UNKNOWN"}]})
        with patch.dict(os.environ, {"EXPIRY_REGISTRY": payload}):
            assert m.load_registry() == [{"id": "x", "expires": "UNKNOWN"}]

    def test_missing_env_and_file_exits(self, tmp_path):
        m = _load_module()
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(m, "REGISTRY_FILE", str(tmp_path / "nope.json")):
            with pytest.raises(SystemExit) as exc:
                m.load_registry()
            assert exc.value.code == 1
