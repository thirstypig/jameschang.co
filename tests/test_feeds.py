"""Unit tests for pure functions in the feed sync scripts."""

import importlib
import os
import sys

# Add bin/ to path so we can import the scripts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

# Hyphenated filenames require importlib
_whoop = importlib.import_module("update-whoop")
_public = importlib.import_module("update-public-feeds")

recovery_color = _whoop.recovery_color
ordinal = _public.ordinal


# ── recovery_color (from update-whoop.py) ────────────────────────
# Returns notebook .nb-stat .v color classes: pos / warn / danger / muted.
# Maps to WHOOP green / yellow / red / no-data zones.

class TestRecoveryColor:
    def test_none_returns_muted(self):
        assert recovery_color(None) == "muted"

    def test_high_score_pos(self):
        assert recovery_color(67) == "pos"
        assert recovery_color(100) == "pos"
        assert recovery_color(80) == "pos"

    def test_mid_score_warn(self):
        assert recovery_color(34) == "warn"
        assert recovery_color(50) == "warn"
        assert recovery_color(66) == "warn"

    def test_low_score_danger(self):
        assert recovery_color(0) == "danger"
        assert recovery_color(33) == "danger"
        assert recovery_color(1) == "danger"

    def test_boundary_67(self):
        assert recovery_color(67) == "pos"
        assert recovery_color(66) == "warn"

    def test_boundary_34(self):
        assert recovery_color(34) == "warn"
        assert recovery_color(33) == "danger"


# ── ordinal (from update-public-feeds.py) ────────────────────────

class TestOrdinal:
    """1, 2, 3, 11–13 (teens-are-th), and 21 prove the algorithm — every
    other case is a rotation of those, so we keep coverage tight."""

    def test_basic_suffixes(self):
        assert ordinal(1) == "1st"
        assert ordinal(2) == "2nd"
        assert ordinal(3) == "3rd"
        assert ordinal(4) == "4th"

    def test_teens_are_th(self):
        assert ordinal(11) == "11th"
        assert ordinal(12) == "12th"
        assert ordinal(13) == "13th"

    def test_twenties_resume_normal_pattern(self):
        assert ordinal(21) == "21st"
        assert ordinal(22) == "22nd"
        assert ordinal(23) == "23rd"

    def test_hundred_teens_still_th(self):
        assert ordinal(111) == "111th"
        assert ordinal(112) == "112th"
        assert ordinal(113) == "113th"

    def test_hundred_twenty_first(self):
        assert ordinal(121) == "121st"
