"""Unit tests for bin/update-projects.py — TLDR extraction + splice behavior."""

import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

_projects = importlib.import_module("update-projects")


class TestExtractTldr:
    def test_extracts_content_between_markers(self):
        md = """# Title

## Current status

<!-- now-tldr -->
Line one.
Line two.
<!-- /now-tldr -->

## Other section
"""
        out = _projects.extract_tldr(md)
        assert out == "Line one.\nLine two."

    def test_returns_none_if_no_marker(self):
        assert _projects.extract_tldr("# Title\n\nNo marker here.") is None

    def test_returns_none_on_empty_input(self):
        assert _projects.extract_tldr("") is None
        assert _projects.extract_tldr(None) is None

    def test_strips_surrounding_whitespace(self):
        md = "<!-- now-tldr -->\n\n   Content   \n\n<!-- /now-tldr -->"
        assert _projects.extract_tldr(md) == "Content"

    def test_handles_inline_markers(self):
        """Markers on the same line as content should still work."""
        md = "<!-- now-tldr -->Single line<!-- /now-tldr -->"
        assert _projects.extract_tldr(md) == "Single line"

    def test_only_matches_first_block(self):
        """If someone accidentally pastes two blocks, use the first one."""
        md = "<!-- now-tldr -->first<!-- /now-tldr -->\n<!-- now-tldr -->second<!-- /now-tldr -->"
        assert _projects.extract_tldr(md) == "first"


class TestLoadConfig:
    def test_loads_seven_projects(self):
        config = _projects.load_config()
        assert len(config) == 7
        slugs = {p["slug"] for p in config}
        assert slugs == {
            "aleph", "fantastic-leagues", "bahtzang-trader", "judge-tool",
            "tabledrop", "tastemakers", "thirsty-pig",
        }

    def test_every_project_has_required_fields(self):
        for project in _projects.load_config():
            assert "slug" in project
            assert "repo" in project
            assert "file" in project
            assert project["repo"].startswith("thirstypig/")
