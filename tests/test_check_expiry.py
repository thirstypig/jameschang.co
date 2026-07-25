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
