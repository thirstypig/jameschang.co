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
    def test_loads_nine_projects(self):
        config = _projects.load_config()
        assert len(config) == 9
        slugs = {p["slug"] for p in config}
        assert slugs == {
            "aleph", "fantastic-leagues", "bahtzang-trader", "judge-tool",
            "tabledrop", "tastemakers", "thirsty-pig", "jameschang-co",
            "ktv-singer",
        }

    def test_every_project_has_required_fields(self):
        for project in _projects.load_config():
            assert "slug" in project
            assert "repo" in project
            assert project["repo"].startswith("thirstypig/")
            # New display fields drive the cron-rendered card markup.
            for field in ("name", "url", "url_label", "status_badge"):
                assert field in project, f"{project['slug']} missing {field}"


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


class TestShippingReposFor:
    """Union of shipping repos drives which repos we fetch events for."""

    def test_unions_and_dedupes_in_config_order(self):
        projects = [
            {"slug": "a", "repo": "o/a", "shipping_repos": ["o/a", "o/a-www"]},
            {"slug": "b", "repo": "o/b", "shipping_repos": ["o/a-www", "o/b"]},
        ]
        assert _projects.shipping_repos_for(projects) == ["o/a", "o/a-www", "o/b"]

    def test_falls_back_to_repo_when_no_shipping_repos(self):
        projects = [{"slug": "a", "repo": "o/solo"}]
        assert _projects.shipping_repos_for(projects) == ["o/solo"]

    def test_empty_projects_returns_empty(self):
        assert _projects.shipping_repos_for([]) == []


class TestFetchGithubEvents:
    """Per-repo aggregation: private-repo events are included (the whole point
    of Option A), and a single repo's failure is isolated, never fatal."""

    def test_aggregates_across_repos(self, monkeypatch):
        canned = {
            "o/pub": [{"type": "PushEvent", "repo": {"name": "o/pub"}}],
            "o/priv": [{"type": "PushEvent", "repo": {"name": "o/priv"}}],
        }
        monkeypatch.setattr(_projects, "fetch_repo_events",
                            lambda repo, token: canned.get(repo, []))
        out = _projects.fetch_github_events(token=None, repos=["o/pub", "o/priv"])
        assert len(out) == 2
        assert {e["repo"]["name"] for e in out} == {"o/pub", "o/priv"}

    def test_single_repo_failure_is_isolated(self, monkeypatch):
        # fetch_repo_events swallows network errors and returns [] — the
        # aggregate must still surface the healthy repo's events.
        def fake(repo, token):
            return [] if repo == "o/broken" else [{"type": "PushEvent", "repo": {"name": repo}}]
        monkeypatch.setattr(_projects, "fetch_repo_events", fake)
        out = _projects.fetch_github_events(token=None, repos=["o/ok", "o/broken"])
        assert len(out) == 1
        assert out[0]["repo"]["name"] == "o/ok"


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


class TestProjectClassification:
    """classify_projects(events_by_slug, threshold_days) splits projects into
    (active, backburner) by recency of most-recent shipping event."""

    @staticmethod
    def _ago(days):
        from datetime import datetime, timedelta, timezone
        return datetime.now(timezone.utc) - timedelta(days=days)

    def test_all_recent_events_all_active(self):
        events = {"a": self._ago(1), "b": self._ago(3), "c": self._ago(10)}
        active, back = _projects.classify_projects(events, threshold_days=14)
        assert set(active) == {"a", "b", "c"}
        assert back == []

    def test_all_old_events_all_backburner(self):
        events = {"a": self._ago(20), "b": self._ago(40)}
        active, back = _projects.classify_projects(events, threshold_days=14)
        assert active == []
        assert set(back) == {"a", "b"}

    def test_mixed_split_correctly(self):
        events = {
            "fresh": self._ago(2),
            "stale": self._ago(30),
            "edge": self._ago(13),
        }
        active, back = _projects.classify_projects(events, threshold_days=14)
        assert set(active) == {"fresh", "edge"}
        assert set(back) == {"stale"}

    def test_project_with_no_events_is_backburner(self):
        events = {"empty": None, "alive": self._ago(2)}
        active, back = _projects.classify_projects(events, threshold_days=14)
        assert active == ["alive"]
        assert back == ["empty"]

    def test_event_at_exactly_threshold_is_backburner(self):
        """Edge case pinned: event delta == threshold_days falls into
        back-burner (the comparison is strict greater-than the cutoff)."""
        from datetime import datetime, timedelta, timezone
        # Build an event whose timestamp matches the cutoff exactly. Use a
        # tiny epsilon-older value so the freshness check (latest > cutoff)
        # is unambiguous on the "older or equal" side.
        threshold = 14
        latest = datetime.now(timezone.utc) - timedelta(days=threshold, seconds=1)
        active, back = _projects.classify_projects({"x": latest}, threshold_days=threshold)
        assert active == []
        assert back == ["x"]


class TestRenderCard:
    """Cron renders the full <article class="nb-card"> markup, including the
    nested TLDR markers so per-project sync continues to work."""

    PROJECT = {
        "slug": "demo",
        "name": "Demo",
        "url": "https://demo.example",
        "url_label": "demo.example ↗",
        "status_badge": "● shipping",
    }

    def test_active_card_has_status_badge_and_url(self):
        html = _projects.render_card(self.PROJECT, "tldr text", "", "May 7, 2026", compact=False)
        assert '<article class="nb-card">' in html
        assert 'class="nb-card-status"' in html
        assert 'demo.example' in html
        assert "<!-- TLDR-demo-START -->" in html
        assert "<!-- TLDR-demo-END -->" in html
        assert '<p class="nb-card-body">tldr text</p>' in html

    def test_backburner_card_is_compact_and_has_no_status(self):
        html = _projects.render_card(self.PROJECT, "tldr", "", "May 7, 2026", compact=True)
        assert '<article class="nb-card compact">' in html
        assert 'nb-card-status' not in html
        # nb-card-url is preserved for back-burner cards (matches prior layout).
        assert 'class="nb-card-url"' in html

    def test_card_escapes_unsafe_url(self):
        bad = dict(self.PROJECT, url="javascript:alert(1)")
        html = _projects.render_card(bad, "x", "", "May 7, 2026", compact=False)
        assert "javascript:" not in html

    def test_card_footer_wraps_shipped_and_timestamp(self):
        """nb-card-footer must contain both the shipped line and feed-updated so
        the CSS bleed-to-edges treatment applies to both elements together."""
        shipping = '<p class="nb-card-shipped">↑ shipped: link</p>\n'
        html = _projects.render_card(self.PROJECT, "tldr", shipping, "May 7, 2026", compact=False)
        footer_start = html.index('class="nb-card-footer"')
        footer_end = html.index("</div>", footer_start)
        footer_block = html[footer_start:footer_end]
        assert "nb-card-shipped" in footer_block
        assert "feed-updated" in footer_block

    def test_card_footer_present_even_without_shipped_line(self):
        """Footer div renders even when no shipping events exist (empty string)."""
        html = _projects.render_card(self.PROJECT, "tldr", "", "May 7, 2026", compact=False)
        assert 'class="nb-card-footer"' in html


class TestRenderBlock:
    def test_tldr_uses_nb_card_body(self):
        html = _projects.render_block("hello world", "", "Apr 27, 2026")
        assert '<p class="nb-card-body">hello world</p>' in html

    def test_keeps_feed_updated_footer(self):
        html = _projects.render_block("x", "", "Apr 27, 2026")
        assert 'class="feed-updated"' in html
        assert "Apr 27, 2026" in html

    def test_block_footer_wraps_shipped_and_timestamp(self):
        """render_block (used for per-project TLDR marker updates) must also
        wrap shipped + feed-updated in nb-card-footer."""
        shipping = '<p class="nb-card-shipped">↑ shipped: link</p>\n'
        html = _projects.render_block("tldr", shipping, "Apr 27, 2026")
        footer_start = html.index('class="nb-card-footer"')
        footer_end = html.index("</div>", footer_start)
        footer_block = html[footer_start:footer_end]
        assert "nb-card-shipped" in footer_block
        assert "feed-updated" in footer_block
