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
    VALID_MATURITY = {"alpha", "beta", "public", "private"}
    VALID_STATUS = {"shipping", "live", "blocked", "shipped"}

    def test_loads_eleven_projects(self):
        config = _projects.load_config()
        assert len(config) == 11
        slugs = {p["slug"] for p in config}
        assert slugs == {
            "aleph", "fantastic-leagues", "bahtzang-trader", "judge-tool",
            "tabledrop", "tastemakers", "thirsty-pig", "jameschang-co",
            "ktv-singer", "vouch", "spar",
        }

    def test_all_projects_have_editorial_fields(self):
        """Every project must have desc + next_up to render the activity-first card."""
        config = _projects.load_config()
        for p in config:
            slug = p["slug"]
            assert p.get("desc"), f"{slug} missing desc"
            assert p.get("next_up"), f"{slug} missing next_up"

    def test_all_projects_have_valid_maturity(self):
        """Maturity drives the badge label; a typo would silently produce a broken badge."""
        config = _projects.load_config()
        for p in config:
            assert p.get("maturity") in self.VALID_MATURITY, (
                f"{p['slug']} has invalid maturity: {p.get('maturity')!r}"
            )

    def test_all_projects_have_valid_status_badge(self):
        config = _projects.load_config()
        for p in config:
            assert p.get("status_badge") in self.VALID_STATUS, (
                f"{p['slug']} has invalid status_badge: {p.get('status_badge')!r}"
            )

    def test_every_project_has_required_fields(self):
        for project in _projects.load_config():
            assert "slug" in project
            assert "repo" in project
            assert project["repo"].startswith("thirstypig/")
            # New display fields drive the cron-rendered card markup.
            for field in ("name", "url", "url_label", "status_badge"):
                assert field in project, f"{project['slug']} missing {field}"

    def test_self_slug_exists_in_config(self):
        """SELF_SLUG must match a real slug in projects-config.json.

        pin_self_last() silently does nothing when the slug is absent — so a
        rename in JSON would break the card ordering without any error.
        """
        slugs = {p["slug"] for p in _projects.load_config()}
        assert _projects.SELF_SLUG in slugs, (
            f"SELF_SLUG={_projects.SELF_SLUG!r} not found in projects-config.json slugs: {slugs}"
        )


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


class TestPinSelfLast:
    """pin_self_last always moves SELF_SLUG to the end of its section."""

    def test_pins_to_bottom_of_active(self):
        active = ["jameschang-co", "aleph", "fl"]
        back = ["judge-tool"]
        _projects.pin_self_last("jameschang-co", active, back)
        assert active[-1] == "jameschang-co"
        assert back == ["judge-tool"]

    def test_pins_to_bottom_of_backburner(self):
        active = ["aleph"]
        back = ["jameschang-co", "judge-tool"]
        _projects.pin_self_last("jameschang-co", active, back)
        assert back[-1] == "jameschang-co"
        assert active == ["aleph"]

    def test_noop_when_already_last(self):
        active = ["aleph", "jameschang-co"]
        _projects.pin_self_last("jameschang-co", active)
        assert active == ["aleph", "jameschang-co"]

    def test_noop_when_slug_absent(self):
        active = ["aleph", "fl"]
        back = ["judge-tool"]
        _projects.pin_self_last("jameschang-co", active, back)
        assert active == ["aleph", "fl"]
        assert back == ["judge-tool"]


class TestRenderBadge:
    def test_known_status_emits_modifier_class(self):
        html = _projects.render_badge("shipping", "beta")
        assert "nb-proj-badge--shipping" in html
        assert "Shipping" in html

    def test_shipping_uses_code_icon(self):
        """shipping must use the ti-code SVG (bracket paths, no circle)."""
        html = _projects.render_badge("shipping", "alpha")
        assert 'M7 8l-4 4 4 4' in html   # distinctive code icon path
        assert '<circle' not in html      # globe/lock/clock all have circles

    def test_maturity_appended_with_middot(self):
        html = _projects.render_badge("shipping", "beta")
        assert "Beta" in html
        assert "&middot;" in html

    def test_live_public_uses_globe_icon(self):
        html = _projects.render_badge("live", "public")
        assert "nb-proj-badge--live" in html
        assert "Live" in html and "Public" in html
        # globe SVG has a <circle> — code/lock/clock don't at the same position
        assert "<circle" in html

    def test_live_private_uses_lock_icon(self):
        html = _projects.render_badge("live", "private")
        assert "Private" in html
        # lock SVG has a <circle cx="12" cy="16"> not a globe's <circle cx="12" cy="12">
        assert 'cy="16"' in html

    def test_blocked_uses_clock_icon(self):
        html = _projects.render_badge("blocked", "alpha")
        assert "nb-proj-badge--blocked" in html
        assert "polyline" in html  # clock's hand polyline

    def test_returns_empty_for_falsy_status(self):
        assert _projects.render_badge("") == ""
        assert _projects.render_badge(None) == ""

    def test_sanitizes_unsafe_chars_from_class(self):
        html = _projects.render_badge("in progress!", "beta")
        assert '"in progress!"' not in html
        assert "nb-proj-badge" in html

    def test_escapes_display_text(self):
        html = _projects.render_badge("<script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestRenderActivityBox:
    def _event(self):
        from datetime import datetime, timezone
        return {
            "summary": "feat: ship a thing",
            "url": "https://github.com/thirstypig/demo/commit/abc",
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def test_emits_activity_box_with_label(self):
        html = _projects.render_activity_box([self._event()])
        assert 'class="nb-proj-activity"' in html
        assert "nb-proj-activity-label" in html

    def test_empty_events_emits_empty_state(self):
        html = _projects.render_activity_box([])
        assert "nb-proj-activity--empty" in html

    def test_uses_bare_time_element_with_data_rel(self):
        html = _projects.render_activity_box([self._event()])
        assert "<time" in html and "data-rel" in html

    def test_link_present_in_activity_body(self):
        html = _projects.render_activity_box([self._event()])
        assert "feat: ship a thing" in html
        assert "nb-proj-activity-body" in html


class TestRenderCard:
    """Cron renders the full <article class="nb-proj-card"> markup, including
    nested TLDR markers so per-project boundary detection continues to work."""

    PROJECT = {
        "slug": "demo",
        "name": "Demo",
        "url": "https://demo.example",
        "url_label": "demo.example",
        "status_badge": "shipping",
        "maturity": "beta",
        "desc": "A demo project for testing.",
        "next_up": "Ship the next thing.",
    }

    def test_card_has_proj_card_class_and_name(self):
        html = _projects.render_card(self.PROJECT, [], "May 7, 2026")
        assert '<article class="nb-proj-card">' in html
        assert 'class="nb-proj-name"' in html
        assert "Demo" in html

    def test_card_has_domain_and_tldr_markers(self):
        html = _projects.render_card(self.PROJECT, [], "May 7, 2026")
        assert "demo.example" in html
        assert "<!-- TLDR-demo-START -->" in html
        assert "<!-- TLDR-demo-END -->" in html

    def test_card_has_badge_with_maturity(self):
        html = _projects.render_card(self.PROJECT, [], "May 7, 2026")
        assert "nb-proj-badge--shipping" in html
        assert "Beta" in html

    def test_card_has_desc_and_next_up(self):
        html = _projects.render_card(self.PROJECT, [], "May 7, 2026")
        assert 'class="nb-proj-desc"' in html
        assert "A demo project for testing." in html
        assert 'class="nb-proj-next"' in html
        assert "Ship the next thing." in html

    def test_activity_box_precedes_description(self):
        """Activity-first: the shipped box must appear before the description."""
        html = _projects.render_card(self.PROJECT, [], "May 7, 2026")
        assert html.index("nb-proj-activity") < html.index("nb-proj-desc")

    def test_card_escapes_unsafe_url(self):
        bad = dict(self.PROJECT, url="javascript:alert(1)")
        html = _projects.render_card(bad, [], "May 7, 2026")
        assert "javascript:" not in html

    def test_card_without_url_falls_back_to_hash_and_omits_domain(self):
        """A project with no live URL yet (blank url + url_label) — Vouch's
        shape when it was added — must render the name link as href="#" (never
        an empty href="") and must NOT emit a dangling nb-proj-domain arrow.

        Regression guard: any refactor of the url/url_label branch that starts
        emitting href="" or a label-less domain span would break every
        URL-less card. Vouch is the first/only such caller in config today."""
        urlless = dict(self.PROJECT, url="", url_label="")
        html = _projects.render_card(urlless, [], "May 7, 2026")
        assert '<a href="#">' in html      # safe fallback link
        assert 'href=""' not in html       # never an empty href
        assert "nb-proj-domain" not in html  # no stray "↗" with no label
        assert 'class="nb-proj-name"' in html  # name still renders

    def test_card_renders_roadmap_items_when_present(self):
        """Config-driven content: roadmap_items from config must render into HTML."""
        project = dict(self.PROJECT, roadmap_items=[
            "Feature A", "Feature B", "Feature C"
        ])
        html = _projects.render_card(project, [], "May 7, 2026")
        assert '<div class="nb-proj-roadmap">' in html
        assert "upcoming roadmap features" in html
        assert "<li>Feature A</li>" in html
        assert "<li>Feature B</li>" in html
        assert "<li>Feature C</li>" in html

    def test_card_escapes_roadmap_items(self):
        """Roadmap items must be escaped to prevent XSS."""
        project = dict(self.PROJECT, roadmap_items=[
            "Feature <script>alert(1)</script>"
        ])
        html = _projects.render_card(project, [], "May 7, 2026")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_card_omits_roadmap_when_empty(self):
        """Roadmap section is optional: no div rendered if items are empty."""
        project = dict(self.PROJECT, roadmap_items=[])
        html = _projects.render_card(project, [], "May 7, 2026")
        assert "nb-proj-roadmap" not in html

    def test_card_omits_roadmap_when_absent(self):
        """Roadmap section is optional: no div rendered if field is missing."""
        project = self.PROJECT  # No roadmap_items field
        html = _projects.render_card(project, [], "May 7, 2026")
        assert "nb-proj-roadmap" not in html
        assert "nb-proj-desc" in html  # Other content still renders


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


class TestRenderCardIdempotency:
    """Config-driven content must survive re-rendering: running the script
    twice with unchanged config should produce identical output (modulo timestamps).

    This guards against the trap where hand-edits to marker blocks survive the
    first run but disappear on the second—the script should always regenerate
    from config, never merge with or preserve existing HTML.
    """

    def test_render_card_is_deterministic(self):
        """Same project + events → same HTML."""
        project = {
            "slug": "aleph",
            "name": "Aleph",
            "url": "https://alephco.io",
            "url_label": "alephco.io",
            "status_badge": "shipping",
            "maturity": "beta",
            "desc": "Compliance platform.",
            "next_up": "Onboard beta users.",
            "roadmap_items": ["Item A", "Item B"],
        }
        html1 = _projects.render_card(project, [], "June 25, 2026")
        html2 = _projects.render_card(project, [], "June 25, 2026")
        assert html1 == html2

    def test_config_change_affects_output(self):
        """Verify that config fields DO appear in the rendered output."""
        project = {
            "slug": "demo",
            "name": "Demo",
            "url": "https://demo.example",
            "url_label": "demo.example",
            "status_badge": "live",
            "maturity": "alpha",
            "desc": "Original desc",
            "next_up": "Original next_up",
            "roadmap_items": ["Original Item"],
        }
        html = _projects.render_card(project, [], "June 25, 2026")
        assert "Original desc" in html
        assert "Original next_up" in html
        assert "Original Item" in html

        # Change config: roadmap items should change in output
        project["roadmap_items"] = ["New Item 1", "New Item 2"]
        html2 = _projects.render_card(project, [], "June 25, 2026")
        assert "New Item 1" in html2
        assert "New Item 2" in html2
        assert "Original Item" not in html2


class TestSystemicEventFailureSkipsHeartbeat:
    """Regression: a dead TLDR_FETCH_TOKEN 401s EVERY repo events fetch. When all
    fetches error and none succeed, main() must leave /now untouched and skip the
    heartbeat so the staleness monitor flags it — instead of silently
    reclassifying every project as back-burner behind a fresh heartbeat. An
    ISOLATED single-repo failure must NOT trigger this bail. See
    docs/solutions/integration-issues/feed-heartbeat-on-noop-path-hides-upstream-api-failure.md."""

    def test_fetch_repo_events_tallies_ok_vs_error(self, monkeypatch):
        from urllib.error import URLError
        monkeypatch.setattr(_projects, "_events_ok", 0)
        monkeypatch.setattr(_projects, "_events_err", 0)

        def fake_fetch_json(url, headers=None, timeout=None):
            if "broken" in url:
                raise URLError("boom")
            return [{"type": "PushEvent", "repo": {"name": "o/ok"}}]

        monkeypatch.setattr(_projects, "fetch_json", fake_fetch_json)
        _projects.fetch_github_events(token=None, repos=["o/ok", "o/broken"])
        # One succeeded, one errored → NOT systemic; the bail condition is false.
        assert _projects._events_ok == 1
        assert _projects._events_err == 1
        assert not (_projects._events_ok == 0 and _projects._events_err > 0)

    def test_all_fetches_error_skips_heartbeat_and_leaves_page(self, monkeypatch):
        calls = {"heartbeat": 0, "write": 0}

        def fake_events(token, repos):
            # Simulate every repo 401'ing (dead PAT): zero ok, all err.
            _projects._events_ok = 0
            _projects._events_err = len(repos) or 1
            return []

        monkeypatch.setattr(_projects, "fetch_github_events", fake_events)
        monkeypatch.setattr(_projects, "record_heartbeat",
                            lambda slug, **kw: calls.__setitem__("heartbeat", calls["heartbeat"] + 1))
        monkeypatch.setattr(_projects, "write_now_html",
                            lambda content: calls.__setitem__("write", calls["write"] + 1))
        monkeypatch.setattr(_projects, "_events_ok", 0)
        monkeypatch.setattr(_projects, "_events_err", 0)

        _projects.main()

        assert calls["heartbeat"] == 0, "heartbeat must not be recorded when all fetches error"
        assert calls["write"] == 0, "page must not be rewritten when all fetches error"
