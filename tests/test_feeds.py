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

class TestRecoveryColor:
    def test_none_returns_muted(self):
        assert recovery_color(None) == "muted"

    def test_high_score_green(self):
        assert recovery_color(67) == "green"
        assert recovery_color(100) == "green"
        assert recovery_color(80) == "green"

    def test_mid_score_yellow(self):
        assert recovery_color(34) == "yellow"
        assert recovery_color(50) == "yellow"
        assert recovery_color(66) == "yellow"

    def test_low_score_red(self):
        assert recovery_color(0) == "red"
        assert recovery_color(33) == "red"
        assert recovery_color(1) == "red"

    def test_boundary_67(self):
        assert recovery_color(67) == "green"
        assert recovery_color(66) == "yellow"

    def test_boundary_34(self):
        assert recovery_color(34) == "yellow"
        assert recovery_color(33) == "red"


# ── ordinal (from update-public-feeds.py) ────────────────────────

class TestOrdinal:
    def test_first(self):
        assert ordinal(1) == "1st"

    def test_second(self):
        assert ordinal(2) == "2nd"

    def test_third(self):
        assert ordinal(3) == "3rd"

    def test_fourth(self):
        assert ordinal(4) == "4th"

    def test_teens_are_th(self):
        assert ordinal(11) == "11th"
        assert ordinal(12) == "12th"
        assert ordinal(13) == "13th"

    def test_twenty_first(self):
        assert ordinal(21) == "21st"

    def test_twenty_second(self):
        assert ordinal(22) == "22nd"

    def test_twenty_third(self):
        assert ordinal(23) == "23rd"

    def test_hundredth(self):
        assert ordinal(100) == "100th"

    def test_hundred_eleventh(self):
        assert ordinal(111) == "111th"

    def test_hundred_twelfth(self):
        assert ordinal(112) == "112th"

    def test_hundred_thirteenth(self):
        assert ordinal(113) == "113th"

    def test_hundred_twenty_first(self):
        assert ordinal(121) == "121st"
