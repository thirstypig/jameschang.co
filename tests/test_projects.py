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

    def test_renders_markdown_bold_to_strong(self):
        md = "<!-- now-tldr -->**Just shipped:** the thing<!-- /now-tldr -->"
        assert _projects.extract_tldr(md) == "<strong>Just shipped:</strong> the thing"

    def test_renders_markdown_code_to_code_tag(self):
        md = "<!-- now-tldr -->config at `bin/projects-config.json` updates daily<!-- /now-tldr -->"
        assert _projects.extract_tldr(md) == "config at <code>bin/projects-config.json</code> updates daily"

    def test_escapes_raw_html_in_tldr(self):
        """A literal <VenueChips> reference in CLAUDE.md must not leak as a real tag."""
        md = "<!-- now-tldr -->renders via <VenueChips> component<!-- /now-tldr -->"
        out = _projects.extract_tldr(md)
        assert "&lt;VenueChips&gt;" in out
        assert "<VenueChips>" not in out

    def test_handles_bold_spanning_multiple_words(self):
        md = "<!-- now-tldr -->**Current focus: the design system rollout** is going<!-- /now-tldr -->"
        out = _projects.extract_tldr(md)
        assert out == "<strong>Current focus: the design system rollout</strong> is going"


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
            assert project["repo"].startswith("thirstypig/")


class TestParseEventsPullRequest:
    """PR events with stripped payloads (private-repo sanitization) must be
    dropped so readers never see 'PR opened: (untitled)' linking to '#'."""

    @staticmethod
    def _now_iso():
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _pr_event(self, *, title, html_url, action="opened"):
        return {
            "type": "PullRequestEvent",
            "created_at": self._now_iso(),
            "repo": {"name": "thirstypig/demo"},
            "payload": {
                "action": action,
                "pull_request": {"title": title, "html_url": html_url},
            },
        }

    def test_keeps_pr_event_with_full_payload(self):
        events = [self._pr_event(title="Fix bug", html_url="https://github.com/x/pull/1")]
        result = _projects.parse_events(events, token=None)
        assert "thirstypig/demo" in result
        entry = result["thirstypig/demo"][0]
        assert entry["summary"] == "PR opened: Fix bug"
        assert entry["url"] == "https://github.com/x/pull/1"

    def test_drops_pr_event_with_stripped_payload(self):
        """Private-repo PR events arrive with null title + null html_url."""
        events = [self._pr_event(title=None, html_url=None)]
        result = _projects.parse_events(events, token=None)
        assert result == {} or result.get("thirstypig/demo", []) == []

    def test_drops_pr_event_missing_url_only(self):
        events = [self._pr_event(title="Has title", html_url=None)]
        result = _projects.parse_events(events, token=None)
        assert result.get("thirstypig/demo", []) == []

    def test_drops_pr_event_missing_title_only(self):
        events = [self._pr_event(title=None, html_url="https://example/pr/1")]
        result = _projects.parse_events(events, token=None)
        assert result.get("thirstypig/demo", []) == []

    def test_keeps_healthy_push_event_alongside(self):
        """Regression guard: filtering PR events must not affect PushEvents."""
        push = {
            "type": "PushEvent",
            "created_at": self._now_iso(),
            "repo": {"name": "thirstypig/demo"},
            "payload": {"head": "abc123", "ref": "refs/heads/main"},
        }
        stripped_pr = self._pr_event(title=None, html_url=None)
        result = _projects.parse_events([push, stripped_pr], token=None)
        entries = result["thirstypig/demo"]
        assert len(entries) == 1
        assert entries[0]["url"] == "https://github.com/thirstypig/demo/commit/abc123"


class TestRenderShippingList:
    """Notebook-design markup contract for the shipping line."""

    def _event(self):
        from datetime import datetime, timezone
        return {
            "summary": "feat: ship a thing",
            "url": "https://github.com/thirstypig/demo/commit/abc",
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def test_emits_nb_card_shipped(self):
        html = _projects.render_shipping_list([self._event()])
        assert 'class="nb-card-shipped"' in html
        assert '<span class="accent">' in html
        assert "shipped:" in html

    def test_drops_legacy_classes(self):
        html = _projects.render_shipping_list([self._event()])
        assert "shipping-recent" not in html
        assert "gh-when" not in html
        # Legacy "Recently shipped" copy is replaced by the accent arrow label
        assert "Recently shipped" not in html

    def test_uses_bare_time_element(self):
        """data-rel attr drives live-relative upgrade — no class needed."""
        html = _projects.render_shipping_list([self._event()])
        assert "<time" in html and "data-rel" in html

    def test_empty_events_returns_empty_string(self):
        assert _projects.render_shipping_list([]) == ""


class TestRenderBlock:
    def test_tldr_uses_nb_card_body(self):
        html = _projects.render_block("hello world", "", "Apr 27, 2026")
        assert '<p class="nb-card-body">hello world</p>' in html

    def test_keeps_feed_updated_footer(self):
        html = _projects.render_block("x", "", "Apr 27, 2026")
        assert 'class="feed-updated"' in html
        assert "Apr 27, 2026" in html
