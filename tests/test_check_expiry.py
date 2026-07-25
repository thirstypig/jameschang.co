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

    def test_missing_expires_key_raises_valueerror(self):
        m = _load_module()
        with pytest.raises(ValueError, match="expires"):
            m.validate_registry({"integrations": [{"id": "x"}]})

    def test_non_string_expires_raises_valueerror(self):
        m = _load_module()
        with pytest.raises(ValueError, match="expires"):
            m.validate_registry({"integrations": [{"id": "x", "expires": 20260101}]})


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

    def test_empty_env_exits_zero(self):
        """An unset EXPIRY_REGISTRY secret arrives as an empty string; that is a
        clean no-op (nothing tracked yet), not an error, and must not fall
        through to issue management."""
        m = _load_module()
        with patch.dict(os.environ, {"EXPIRY_REGISTRY": ""}):
            with pytest.raises(SystemExit) as exc:
                m.load_registry()
            assert exc.value.code == 0

    def test_whitespace_only_env_exits_zero(self):
        m = _load_module()
        with patch.dict(os.environ, {"EXPIRY_REGISTRY": "   \n"}):
            with pytest.raises(SystemExit) as exc:
                m.load_registry()
            assert exc.value.code == 0


def _run_main(integrations, open_issues, today):
    """Run main() with load_registry / open_expiry_issues / _today / gh mocked.
    Returns the mocked gh so callers can assert on the calls it received."""
    m = _load_module()
    gh_mock = MagicMock(return_value="")
    with (
        patch.object(m, "load_registry", return_value=integrations),
        patch.object(m, "ensure_label", return_value=None),
        patch.object(m, "open_expiry_issues", return_value=open_issues),
        patch.object(m, "_today", return_value=today),
        patch.object(m, "gh", gh_mock),
    ):
        m.main()
    return gh_mock


def _subcommands(gh_mock):
    """The gh subcommand pairs actually invoked, e.g. ('issue','create')."""
    return [(c.args[0], c.args[1]) for c in gh_mock.call_args_list
            if len(c.args) >= 2 and c.args[0] == "issue"]


class TestExpiryLifecycle:
    def test_opens_issue_when_within_band_and_none_exists(self):
        entry = {"id": "x", "expires": "2026-01-20"}
        gh = _run_main([entry], {}, date(2026, 1, 1))  # 19 days out → band 30
        assert ("issue", "create") in _subcommands(gh)

    def test_no_issue_when_outside_all_thresholds(self):
        entry = {"id": "x", "expires": "2026-06-01"}
        gh = _run_main([entry], {}, date(2026, 1, 1))  # ~150 days out
        assert _subcommands(gh) == []

    def test_skips_unknown_dates(self):
        entry = {"id": "x", "expires": "UNKNOWN"}
        gh = _run_main([entry], {}, date(2026, 1, 1))
        assert _subcommands(gh) == []

    def test_escalates_when_band_tightens(self):
        entry = {"id": "x", "expires": "2026-01-06"}  # 5 days out → band 7
        gh = _run_main([entry], {"x": {"number": 12, "band": 30}}, date(2026, 1, 1))
        subs = _subcommands(gh)
        assert ("issue", "edit") in subs
        assert ("issue", "comment") in subs

    def test_no_escalation_when_band_unchanged(self):
        entry = {"id": "x", "expires": "2026-01-06"}  # band 7
        gh = _run_main([entry], {"x": {"number": 12, "band": 7}}, date(2026, 1, 1))
        assert _subcommands(gh) == []

    def test_closes_when_renewed_past_all_thresholds(self):
        entry = {"id": "x", "expires": "2026-06-01"}  # far out now
        gh = _run_main([entry], {"x": {"number": 12, "band": 7}}, date(2026, 1, 1))
        assert ("issue", "close") in _subcommands(gh)

    def test_orphan_issue_is_closed(self):
        gh = _run_main([], {"gone": {"number": 9, "band": 14}}, date(2026, 1, 1))
        assert ("issue", "close") in _subcommands(gh)

    def test_unknown_with_open_issue_is_closed(self):
        entry = {"id": "x", "expires": "UNKNOWN"}
        gh = _run_main([entry], {"x": {"number": 12, "band": 7}}, date(2026, 1, 1))
        assert ("issue", "close") in _subcommands(gh)


class TestTransientErrorHandling:
    def _run_with_open_error(self, msg):
        m = _load_module()
        with (
            patch.object(m, "load_registry", return_value=[{"id": "x", "expires": "UNKNOWN"}]),
            patch.object(m, "ensure_label", return_value=None),
            patch.object(m, "open_expiry_issues", side_effect=RuntimeError(msg)),
        ):
            with pytest.raises(SystemExit) as exc:
                m.main()
            return exc.value.code

    def test_504_exits_zero(self):
        assert self._run_with_open_error("HTTP 504: Gateway Timeout") == 0

    def test_auth_error_propagates(self):
        m = _load_module()
        with (
            patch.object(m, "load_registry", return_value=[{"id": "x", "expires": "UNKNOWN"}]),
            patch.object(m, "ensure_label", return_value=None),
            patch.object(m, "open_expiry_issues", side_effect=RuntimeError("HTTP 401: Unauthorized")),
        ):
            with pytest.raises(RuntimeError, match="Unauthorized"):
                m.main()


class TestOpenExpiryIssuesParsing:
    def test_parses_band_marker_from_body(self):
        m = _load_module()
        listing = json.dumps([
            {"number": 3, "title": "Credential expiring: x", "body": "blah <!-- expiry-band:7 -->"},
            {"number": 4, "title": "Unrelated issue", "body": ""},
        ])
        with patch.object(m, "gh", return_value=listing):
            out = m.open_expiry_issues()
        assert out == {"x": {"number": 3, "band": 7}}

    def test_missing_marker_defaults_to_widest_band(self):
        m = _load_module()
        listing = json.dumps([{"number": 5, "title": "Credential expiring: y", "body": "no marker"}])
        with patch.object(m, "gh", return_value=listing):
            out = m.open_expiry_issues()
        assert out == {"y": {"number": 5, "band": 30}}


class TestDryRunWriteGuard:
    def test_write_subcommands_short_circuit_under_dry_run(self):
        m = _load_module()
        for sub in ("create", "close", "comment", "edit"):
            with patch.object(m, "DRY_RUN", True), \
                 patch.object(m.subprocess, "run") as run_mock:
                out = m.gh("issue", sub, "1", "--body", "x")
                assert out == "", f"{sub} did not short-circuit under DRY_RUN"
                run_mock.assert_not_called()

    def test_read_subcommand_still_runs_under_dry_run(self):
        m = _load_module()
        with patch.object(m, "DRY_RUN", True), \
             patch.object(m.subprocess, "run") as run_mock:
            run_mock.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            m.gh("issue", "list", "--json", "number")
            run_mock.assert_called_once()


class TestComputeStatus:
    def test_disjoint_bands_and_needs_date(self):
        m = _load_module()
        integrations = [
            {"id": "a", "expires": "2026-01-06"},   # 5 days  -> within_7
            {"id": "b", "expires": "2026-01-12"},   # 11 days -> within_14
            {"id": "c", "expires": "2026-01-25"},   # 24 days -> within_30
            {"id": "d", "expires": "2026-03-01"},   # far     -> uncounted
            {"id": "e", "expires": "UNKNOWN"},      #         -> needs_date
        ]
        out = m.compute_status(integrations, date(2026, 1, 1))
        assert out == {"expiry": {"within_7": 1, "within_14": 1,
                                  "within_30": 1, "needs_date": 1}}

    def test_expired_counts_as_within_7(self):
        m = _load_module()
        out = m.compute_status([{"id": "x", "expires": "2025-12-20"}], date(2026, 1, 1))
        assert out["expiry"]["within_7"] == 1

    def test_output_has_only_count_keys(self):
        """The doorbell must never emit ids or dates — only the four counts."""
        m = _load_module()
        out = m.compute_status(
            [{"id": "super-secret-cred", "expires": "2026-01-02",
              "renew_url": "https://example.com"}],
            date(2026, 1, 1))
        assert set(out) == {"expiry"}
        assert set(out["expiry"]) == {"within_7", "within_14", "within_30", "needs_date"}
        assert all(isinstance(v, int) for v in out["expiry"].values())


class TestWriteStatusJson:
    def test_dry_run_does_not_write(self, tmp_path, capsys):
        m = _load_module()
        target = tmp_path / "status.json"
        with patch.object(m, "STATUS_FILE", str(target)), \
             patch.object(m, "DRY_RUN", True):
            m.write_status_json([{"id": "x", "expires": "UNKNOWN"}], date(2026, 1, 1))
        assert not target.exists()
        assert "status.json would be" in capsys.readouterr().out

    def test_real_run_writes_counts(self, tmp_path):
        m = _load_module()
        target = tmp_path / "status.json"
        with patch.object(m, "STATUS_FILE", str(target)), \
             patch.object(m, "DRY_RUN", False):
            m.write_status_json([{"id": "x", "expires": "UNKNOWN"}], date(2026, 1, 1))
        written = json.loads(target.read_text())
        assert written == {"expiry": {"within_7": 0, "within_14": 0,
                                      "within_30": 0, "needs_date": 1}}


class TestStatusJsonIsPublicSafe:
    def test_committed_status_json_has_no_secrets(self):
        """admin/status.json is committed to a PUBLIC repo — counts only."""
        _idx = importlib.import_module("build-docs-index")
        path = os.path.join(ROOT, "admin", "status.json")
        data = json.loads(open(path, encoding="utf-8").read())
        assert set(data) == {"expiry"}
        assert set(data["expiry"]) == {"within_7", "within_14", "within_30", "needs_date"}
        assert _idx.find_secret_values(open(path, encoding="utf-8").read()) == []
