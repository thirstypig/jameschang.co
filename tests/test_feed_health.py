"""Tests for bin/check-feed-health.py — transient error handling."""

import importlib
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

_health = importlib.import_module("check-feed-health")

VALID_HEARTBEATS = {
    "whoop": {"last_success_utc": "2099-01-01T00:00:00+00:00"},
}


class TestTransientErrorHandling:
    """main() must exit cleanly (code 0) on transient GitHub API errors.

    Without this guard, a GitHub 504 fails the workflow with a red X and
    creates the impression that feeds are broken when they're fine.
    """

    def _run_main_with_open_issues_error(self, error_msg):
        with (
            patch.object(_health, "load_heartbeats", return_value=VALID_HEARTBEATS),
            patch.object(_health, "ensure_label", return_value=None),
            patch.object(
                _health, "open_issues_by_feed",
                side_effect=RuntimeError(error_msg),
            ),
        ):
            import pytest
            with pytest.raises(SystemExit) as exc_info:
                _health.main()
            return exc_info.value.code

    def test_504_gateway_timeout_exits_zero(self):
        code = self._run_main_with_open_issues_error(
            "HTTP 504: 504 Gateway Timeout (https://api.github.com/graphql)"
        )
        assert code == 0

    def test_503_service_unavailable_exits_zero(self):
        code = self._run_main_with_open_issues_error("HTTP 503: Service Unavailable")
        assert code == 0

    def test_502_bad_gateway_exits_zero(self):
        code = self._run_main_with_open_issues_error("HTTP 502: Bad Gateway")
        assert code == 0

    def test_timeout_keyword_exits_zero(self):
        code = self._run_main_with_open_issues_error("Timeout error connecting to github")
        assert code == 0

    def test_non_transient_error_propagates(self):
        """A non-network error (e.g. auth failure) must still fail the workflow."""
        import pytest
        with (
            patch.object(_health, "load_heartbeats", return_value=VALID_HEARTBEATS),
            patch.object(_health, "ensure_label", return_value=None),
            patch.object(
                _health, "open_issues_by_feed",
                side_effect=RuntimeError("HTTP 401: Unauthorized"),
            ),
        ):
            with pytest.raises(RuntimeError, match="Unauthorized"):
                _health.main()
