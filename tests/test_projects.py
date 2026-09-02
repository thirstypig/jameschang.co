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

    def test_loads_thirteen_projects(self):
        config = _projects.load_config()
        assert len(config) == 13
        slugs = {p["slug"] for p in config}
        assert slugs == {
            "aleph", "fantastic-leagues", "bahtzang-trader", "judge-tool",
            "tabledrop", "tastemakers", "thirsty-pig", "jameschang-co",
            "ktv-singer", "vouch", "tip", "pasadenaworks", "family-sites",
        }

    def test_shipping_and_shipped_do_not_render_the_same_icon(self):
        """The two most confusable values in the vocabulary must look different.

        `shipping` (actively building) and `shipped` (done) differ by one
        letter and mean opposite things. render_badge's icon chain ends in a
        bare `else: icon = _SVG_CODE`, so every unhandled status inherits the
        code glyph that signifies active development — marking a finished
        project `shipped` advertised it as still being built.

        Note what is NOT asserted here: `shipped` has no
        `.nb-proj-badge--shipped` CSS rule, and that is deliberate —
        notebook.css comments the base rule as "base (neutral/shipped), then
        semantic modifiers", so shipped is meant to fall through to neutral.
        Only the icon was wrong.
        """
        import re as _re
        icon = lambda html: _re.search(r"<svg.*?</svg>", html, _re.S).group(0)
        assert icon(_projects.render_badge("shipped", "public")) != \
               icon(_projects.render_badge("shipping", "beta")), (
            "a finished project renders the same icon as one still shipping")

    def test_neutral_base_badge_is_documented_in_css(self):
        """Guards the design decision the test above leans on: if someone adds
        semantic colors for every status and drops the neutral base comment,
        the fall-through for `shipped` becomes accidental rather than chosen."""
        css_path = os.path.join(os.path.dirname(__file__), "..", "notebook.css")
        with open(css_path, encoding="utf-8") as f:
            css = f.read()
        assert "base (neutral/shipped)" in css, (
            "the neutral-base intent for `shipped` is no longer documented in "
            "notebook.css — either restore the comment or give shipped a "
            "semantic modifier")

    def test_config_pin_values_are_all_recognized(self):
        """At runtime an unrecognized `pin` degrades to activity
        classification with only a log line — which nobody reads on a green
        run. Catch the typo in CI, where it is loud."""
        bad = [(p["slug"], p["pin"]) for p in _projects.load_config()
               if p.get("pin") is not None and p["pin"] not in _projects.VALID_PINS]
        assert bad == [], f"unrecognized pin values in config: {bad}"

    def test_no_project_fakes_a_pin_by_emptying_shipping_repos(self):
        """Guards the alternative that was considered and rejected.

        Clearing shipping_repos[] also forces back-burner — but by starving
        the classifier of input rather than overriding its output. It blanks
        the card's rendered "shipped" line (stating something false), stops
        those repos being fetched at all, and blinds repo_key_mismatch() on
        exactly those repos. Section intent belongs in `pin`.

        Absence of the key is fine — shipping_repos_for() falls back to
        `repo`. An explicitly empty list is the smell.
        """
        offenders = [p["slug"] for p in _projects.load_config()
                     if "shipping_repos" in p and not p["shipping_repos"]]
        assert offenders == [], (
            f'{offenders} declare an empty shipping_repos[] — use "pin" to '
            f"force a section; never starve the classifier of its input")

    def test_family_sites_is_pinned_to_backburner(self):
        """The five family sites get frequent content edits, so the 7-day
        recency rule would keep promoting them to active. The pin is what
        holds them in back-burner; losing it is a silent regression that only
        shows up as a wrong-looking /now page."""
        config = {p["slug"]: p for p in _projects.load_config()}
        fam = config["family-sites"]
        assert fam["pin"] == _projects.PIN_BACKBURNER
        assert len(fam["shipping_repos"]) == 5

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


class TestHousekeepingRules:
    """todos/148 — a housekeeping commit must not promote a project to active.

    Two named rules, both applied to classification AND to the rendered line
    through the same code path in parse_events(), so a card can never read
    back-burner while displaying a recent commit.
    """

    @staticmethod
    def _now_iso():
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _push(self, *, sha="abc123", actor="thirstypig", repo="o/app", when=None):
        return {
            "type": "PushEvent",
            "created_at": when or self._now_iso(),
            "repo": {"name": repo},
            "actor": {"login": actor},
            "payload": {"head": sha, "ref": "refs/heads/main"},
        }

    # -- rule 2: the message patterns ---------------------------------------

    def test_matches_the_real_fan_out_shapes(self):
        """Both message shapes observed in the wild, from todos/148's table."""
        for subject in (
            "chore: sync port registry — pasadenaworks claims block 3180",
            "docs(ports): sync port registry — add vouch (3020) and spar (3110)",
            "Merge pull request #13 from thirstypig/chore/port-registry-3120",
            "chore: sync PORT REGISTRY",              # case-insensitive
            "chore: sync port  registry",             # \s* tolerates spacing
        ):
            assert _projects.is_chore_summary(subject), subject

    def test_does_not_match_real_work_that_looks_like_a_chore(self):
        """The whole reason a `chore:` prefix filter was rejected: these are
        genuine commits that share the prefix or the branch shape."""
        for subject in (
            "Merge pull request #12 from thirstypig/chore/test-coverage-and-doc-sync",
            "chore(docs): refresh generated stats after #20 (#21)",
            "chore: sync Google Calendar feed on /now page",  # bot rule's job, not this one
            "feat: add the roadmap adapter",
        ):
            assert not _projects.is_chore_summary(subject), subject

    def test_unenriched_summary_fails_open(self):
        """An event we could not enrich carries the generic summary and must
        count as real work — hiding shipping is worse than missing a chore."""
        assert not _projects.is_chore_summary("Pushed to main")
        assert not _projects.is_chore_summary("")
        assert not _projects.is_chore_summary(None)

    # -- rule 1: bot actors --------------------------------------------------

    def test_bot_pushes_are_dropped(self):
        events = [self._push(actor="github-actions[bot]")]
        assert _projects.parse_events(events, token=None)["o/app"] == []

    def test_bot_rule_needs_no_enrichment(self, monkeypatch):
        """The actor is already in the payload, so a bot push must be dropped
        without spending a /commits/{sha} fetch."""
        calls = []
        monkeypatch.setattr(_projects, "fetch_json",
                            lambda url, **kw: calls.append(url) or {})
        _projects.parse_events([self._push(actor="github-actions[bot]")], token="t")
        assert calls == [], f"spent {len(calls)} fetch(es) on a bot push"

    def test_human_pushes_survive(self):
        assert len(_projects.parse_events([self._push()], token=None)["o/app"]) == 1

    # -- the walk ------------------------------------------------------------

    def test_walks_past_a_chore_to_the_next_real_commit(self, monkeypatch):
        msgs = {"sha_chore": "chore: sync port registry — block 3180",
                "sha_real": "feat: the actual work"}
        monkeypatch.setattr(_projects, "fetch_json",
                            lambda url, **kw: {"commit": {"message": msgs[url.rsplit("/", 1)[1]]}})
        events = [self._push(sha="sha_chore", when="2026-08-30T12:00:00Z"),
                  self._push(sha="sha_real", when="2026-08-30T11:00:00Z")]
        kept = _projects.parse_events(events, token="t")["o/app"]
        assert [e["summary"] for e in kept] == ["feat: the actual work"]

    def test_all_chores_leaves_nothing(self, monkeypatch):
        monkeypatch.setattr(_projects, "fetch_json",
                            lambda url, **kw: {"commit": {"message": "chore: sync port registry"}})
        events = [self._push(sha="a", when="2026-08-30T12:00:00Z"),
                  self._push(sha="b", when="2026-08-30T11:00:00Z")]
        assert _projects.parse_events(events, token="t")["o/app"] == []

    def test_classification_and_rendering_cannot_disagree(self, monkeypatch):
        """The trap todos/148 names explicitly: a card reading 'back-burner'
        while displaying a recent commit. Both readers take the same dict, so
        an event filtered from one is filtered from both."""
        monkeypatch.setattr(_projects, "fetch_json",
                            lambda url, **kw: {"commit": {"message": "chore: sync port registry"}})
        by_repo = _projects.parse_events([self._push(sha="a")], token="t")
        project = {"slug": "demo", "repo": "o/app", "shipping_repos": ["o/app"]}
        assert _projects.most_recent_event_time(project, by_repo) is None
        assert _projects.events_for_project(project, by_repo) == []

    def test_enrichment_cap_is_respected_while_walking(self, monkeypatch):
        calls = []
        monkeypatch.setattr(_projects, "fetch_json", lambda url, **kw: (
            calls.append(url), {"commit": {"message": "chore: sync port registry"}})[1])
        monkeypatch.setattr(_projects, "MAX_COMMIT_ENRICHMENTS", 3)
        events = [self._push(sha=f"s{i}", when=f"2026-08-30T1{i}:00:00Z") for i in range(6)]
        _projects.parse_events(events, token="t")
        assert len(calls) <= 3, f"walk spent {len(calls)} fetches against a cap of 3"


class TestSelfRepoPin:
    """jameschang-co is pinned active because its own cron floods its feed.

    The bot rule (BOT_ACTORS) affects exactly ONE repo — jameschang.co is the
    only one github-actions[bot] pushes to. Filtering those leaves a feed where
    29 of 30 events are gone and human pushes have been buried past the API
    window, so recency stops describing the project. That is precisely the
    divergence `pin` exists for.
    """

    def test_self_slug_is_pinned_active(self):
        config = _projects.load_config()
        jc = [p for p in config if p["slug"] == _projects.SELF_SLUG][0]
        assert jc.get("pin") == _projects.PIN_ACTIVE, (
            "jameschang-co must stay pinned active — without it the bot rule "
            "drops its whole feed and the card reads back-burner on days real "
            "work shipped")

    def test_pinned_active_self_still_sorts_last_in_its_section(self):
        """The pin must not defeat pin_self_last(): the site should be active,
        but never the most prominent card on its own page."""
        config = _projects.load_config()
        pins = _projects.pins_from_config(config)
        active, backburner = _projects.classify_projects(
            {p["slug"]: None for p in config}, pinned=pins)
        assert _projects.SELF_SLUG in active
        assert active[-1] == _projects.SELF_SLUG, (
            f"expected {_projects.SELF_SLUG} last in active, got {active}")


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


class TestRepoKeyMismatch:
    """todos/149: a renamed source repo silently demotes its project.

    GitHub redirects /repos/{old}/events to the new name, so the fetch returns
    a normal 200 with real data — but every event is stamped with the NEW
    name, while most_recent_event_time() looks events up by the CONFIG string.
    The key misses, the project reads as "no events", and it falls to
    back-burner behind a green heartbeat.

    The invariant being guarded is narrower than "was it renamed": it is
    "does the configured string equal the key parse_events will file these
    events under". That is why the comparison is exact — a case-only drift
    breaks attribution just as completely as a rename.
    """

    def test_returns_new_name_when_events_are_attributed_elsewhere(self):
        events = [{"type": "PushEvent", "repo": {"name": "thirstypig/TIP"}}]
        assert _projects.repo_key_mismatch("thirstypig/spar", events) == "thirstypig/TIP"

    def test_returns_none_when_names_agree(self):
        events = [{"type": "PushEvent", "repo": {"name": "o/app"}}]
        assert _projects.repo_key_mismatch("o/app", events) is None

    def test_returns_none_for_empty_events(self):
        """A repo with no events carries no name to compare, so a rename on a
        genuinely quiet repo is undetectable. That is acceptable: with no
        activity, the classification (back-burner) is correct anyway."""
        assert _projects.repo_key_mismatch("o/app", []) is None

    def test_case_only_difference_is_reported(self):
        """Not a rename, but it breaks the dict lookup identically."""
        events = [{"type": "PushEvent", "repo": {"name": "o/MyApp"}}]
        assert _projects.repo_key_mismatch("o/myapp", events) == "o/MyApp"

    def test_malformed_events_are_skipped_not_crashed(self):
        events = [{"type": "PushEvent"}, {"repo": {}}, {"repo": {"name": ""}}]
        assert _projects.repo_key_mismatch("o/app", events) is None

    def test_fetch_records_mismatch_and_still_returns_the_data(self, monkeypatch):
        """Report-only, deliberately NOT self-healing: re-keying to the
        returned name would keep the card correct and thereby remove the only
        pressure to fix the config — masking the drift the warning exists to
        surface."""
        monkeypatch.setattr(_projects, "_repo_key_mismatches", [])
        monkeypatch.setattr(_projects, "fetch_json",
                            lambda url, headers=None, timeout=None:
                            [{"type": "PushEvent", "repo": {"name": "o/new"}}])
        out = _projects.fetch_repo_events("o/old", token=None)
        assert out == [{"type": "PushEvent", "repo": {"name": "o/new"}}]  # data untouched
        assert _projects._repo_key_mismatches == [("o/old", "o/new")]

    def test_heartbeat_is_clean_when_no_mismatches(self, monkeypatch):
        monkeypatch.setattr(_projects, "_repo_key_mismatches", [])
        assert _projects.mismatch_heartbeat_kwargs() == {}

    def test_events_keyed_under_new_name_are_lost_by_both_lookups(self):
        """The raw damage the detector warns about, asserted directly.

        Every other test in this class proves the WARNING fires. None proves
        the underlying loss is real, so a future refactor that normalizes keys
        (and thereby fixes the bug) would leave eight tests guarding a problem
        that no longer exists. This one fails loudly in that case.
        """
        project = {"slug": "tip", "repo": "thirstypig/spar",
                   "shipping_repos": ["thirstypig/spar"]}
        events_by_repo = {"thirstypig/TIP": [{
            "summary": "Pushed to main", "url": "https://github.com/x",
            "time": "2026-08-04T12:00:00Z", "_repo": "thirstypig/TIP"}]}
        assert _projects.events_for_project(project, events_by_repo) == []
        assert _projects.most_recent_event_time(project, events_by_repo) is None

    def test_heartbeat_is_partial_success_when_mismatched(self, monkeypatch):
        """partial_success=True refreshes last_success_utc AND records the
        note — so the 48h staleness monitor does not false-trip, but the
        mismatch becomes visible in .feeds-heartbeat.json instead of nowhere."""
        monkeypatch.setattr(_projects, "_repo_key_mismatches",
                            [("thirstypig/spar", "thirstypig/TIP")])
        kwargs = _projects.mismatch_heartbeat_kwargs()
        assert kwargs["partial_success"] is True
        assert "thirstypig/spar" in kwargs["error"]
        assert "thirstypig/TIP" in kwargs["error"]


class TestProjectPinning:
    """`pin` in projects-config.json overrides the activity-recency rule.

    The recency rule answers "was this touched recently?" — but the section
    headings claim something stronger: "am I still building this?" Those
    diverge for a maintenance-mode project (edited often, not being expanded).
    `pin` is the explicit, named escape hatch for that divergence.
    """

    @staticmethod
    def _ago(days):
        from datetime import datetime, timedelta, timezone
        return datetime.now(timezone.utc) - timedelta(days=days)

    def test_pin_backburner_overrides_recent_activity(self):
        """The motivating case: family-sites is pushed to constantly but is
        explicitly maintenance-only. Recency alone would call it active."""
        events = {"family-sites": self._ago(0), "real": self._ago(1)}
        active, back = _projects.classify_projects(
            events, threshold_days=7, pinned={"family-sites": "backburner"})
        assert active == ["real"]
        assert back == ["family-sites"]

    def test_pin_active_overrides_stale_activity(self):
        """Inverse direction: a project being actively worked somewhere the
        GitHub events don't show (design, research, a private mirror)."""
        events = {"quiet": self._ago(90)}
        active, back = _projects.classify_projects(
            events, threshold_days=7, pinned={"quiet": "active"})
        assert active == ["quiet"]
        assert back == []

    def test_pin_active_promotes_project_with_no_events_at_all(self):
        events = {"nothing": None}
        active, back = _projects.classify_projects(
            events, threshold_days=7, pinned={"nothing": "active"})
        assert active == ["nothing"]
        assert back == []

    def test_unpinned_projects_still_follow_recency_rule(self):
        """A pin must be surgical — it changes only the slug it names."""
        events = {"pinned": self._ago(0), "fresh": self._ago(1), "stale": self._ago(30)}
        active, back = _projects.classify_projects(
            events, threshold_days=7, pinned={"pinned": "backburner"})
        assert active == ["fresh"]
        assert set(back) == {"pinned", "stale"}

    def test_omitting_pinned_argument_preserves_legacy_behavior(self):
        """Backward compatibility: every existing caller passes no `pinned`."""
        events = {"a": self._ago(1), "b": self._ago(30)}
        assert (_projects.classify_projects(events, threshold_days=7)
                == _projects.classify_projects(events, threshold_days=7, pinned={}))

    def test_unknown_pin_value_falls_back_to_recency_and_warns(self, capsys):
        """A typo ("back-burner", "backburnner") must not silently vanish into
        the recency default — that is exactly the silent-misclassification
        failure class documented in todos/149. Fail loudly in the cron log,
        but never crash the sync over a config typo."""
        events = {"typo": self._ago(0)}
        active, back = _projects.classify_projects(
            events, threshold_days=7, pinned={"typo": "back-burner"})
        assert active == ["typo"]        # fell through to the recency rule
        assert back == []
        assert "back-burner" in capsys.readouterr().out  # but it was reported

    def test_pin_constants_are_the_only_accepted_values(self):
        assert _projects.VALID_PINS == frozenset(
            {_projects.PIN_ACTIVE, _projects.PIN_BACKBURNER})

    def test_every_slug_lands_in_exactly_one_section(self):
        """Coverage, not just placement.

        The pin branches are new code on the ONLY path that decides section
        membership. A slug that falls out of both lists disappears from /now
        silently — the page renders, the workflow is green, the heartbeat is
        clean, and the card is simply gone. Nothing else asserts totality.
        """
        events = {"pin_up": self._ago(30), "pin_down": self._ago(0),
                  "fresh": self._ago(1), "stale": self._ago(30), "silent": None}
        active, back = _projects.classify_projects(
            events, threshold_days=7,
            pinned={"pin_up": _projects.PIN_ACTIVE,
                    "pin_down": _projects.PIN_BACKBURNER})
        assert sorted(active + back) == sorted(events), "a slug went missing"
        assert not (set(active) & set(back)), "a slug rendered in both sections"


class TestRenderCardLinks:
    """Optional `links[]` — for a card representing more than one live site.

    render_card supports exactly one link (the project name), which is fine
    for a single-product card. The grouped family-sites card breaks that
    assumption: five live domains, and before this the only way to name them
    was unclickable prose in `desc`.
    """

    BASE = {
        "slug": "demo", "name": "Demo", "url": "", "url_label": "",
        "status_badge": "live", "maturity": "public",
        "desc": "A demo.", "next_up": "Ship it.",
    }

    def test_renders_each_link_with_its_label(self):
        project = dict(self.BASE, links=[
            {"label": "one.com", "url": "https://one.com"},
            {"label": "two.com", "url": "https://two.com"}])
        html = _projects.render_card(project, [], "Aug 5, 2026")
        assert 'class="nb-proj-links"' in html
        assert '<a href="https://one.com"' in html
        assert ">one.com</a>" in html
        assert ">two.com</a>" in html

    def test_links_open_in_a_new_tab_safely(self):
        project = dict(self.BASE, links=[{"label": "x", "url": "https://x.com"}])
        html = _projects.render_card(project, [], "Aug 5, 2026")
        assert 'rel="noopener"' in html and 'target="_blank"' in html

    def test_no_links_row_when_absent_or_empty(self):
        """Every other card in config has no links[] and must be unchanged."""
        for project in (self.BASE, dict(self.BASE, links=[])):
            assert "nb-proj-links" not in _projects.render_card(
                project, [], "Aug 5, 2026")

    def test_unsafe_link_url_is_neutralized(self):
        """Same safe_url discipline as the project name — config is authored
        by hand today, but the renderer must not be the weak link."""
        project = dict(self.BASE, links=[
            {"label": "evil", "url": "javascript:alert(1)"}])
        html = _projects.render_card(project, [], "Aug 5, 2026")
        assert "javascript:" not in html

    def test_link_label_is_escaped(self):
        project = dict(self.BASE, links=[
            {"label": "<script>x</script>", "url": "https://x.com"}])
        html = _projects.render_card(project, [], "Aug 5, 2026")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_entry_missing_a_url_is_skipped_not_rendered_dead(self):
        project = dict(self.BASE, links=[
            {"label": "no-url"}, {"label": "ok.com", "url": "https://ok.com"}])
        html = _projects.render_card(project, [], "Aug 5, 2026")
        assert "no-url" not in html
        assert ">ok.com</a>" in html

    def test_family_sites_config_links_all_five_domains(self):
        """The card exists to point at five live sites; if the links row ever
        drops one, the site it names becomes unreachable from /now."""
        config = {p["slug"]: p for p in _projects.load_config()}
        links = config["family-sites"].get("links") or []
        assert len(links) == 5, f"expected 5 family-site links, got {len(links)}"
        html = _projects.render_card(config["family-sites"], [], "Aug 5, 2026")
        for entry in links:
            assert entry["url"] in html, f"{entry['label']} missing from the card"


class TestPinsFromConfig:
    """Building the {slug: pin} map is its own step, so it can be tested.

    It was previously an inline `if p.get("pin")` comprehension in main(),
    which silently dropped a present-but-falsy value: `"pin": ""` never
    reached classify_projects, so the documented fail-loudly contract quietly
    did not apply to it. Presence in the config is what matters, not
    truthiness — validation is classify_projects's job, not this function's.
    """

    def test_includes_recognized_pins(self):
        projects = [{"slug": "a", "pin": "backburner"}, {"slug": "b", "pin": "active"}]
        assert _projects.pins_from_config(projects) == {
            "a": "backburner", "b": "active"}

    def test_omits_projects_with_no_pin_key(self):
        assert _projects.pins_from_config([{"slug": "a"}]) == {}

    def test_keeps_an_empty_string_so_it_can_be_reported(self):
        """The bug this function was extracted to fix."""
        assert _projects.pins_from_config([{"slug": "a", "pin": ""}]) == {"a": ""}

    def test_keeps_an_explicit_null_so_it_can_be_reported(self):
        assert _projects.pins_from_config([{"slug": "a", "pin": None}]) == {"a": None}

    def test_a_falsy_pin_survives_into_a_warning(self, capsys):
        """End to end: config -> map -> classifier warning, the path that
        was broken. A blank pin must be reported, then fall back to recency."""
        from datetime import datetime, timedelta, timezone
        pinned = _projects.pins_from_config([{"slug": "blank", "pin": ""}])
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        active, back = _projects.classify_projects(
            {"blank": recent}, threshold_days=7, pinned=pinned)
        assert active == ["blank"]                      # fell back to recency
        assert "unrecognized pin" in capsys.readouterr().out


class TestPinBackburnerLast:
    """A project pinned to back-burner sorts to the BOTTOM of that section.

    _backburner_key ranks projects that have events by recency, newest first.
    That is the right ranking for a project that landed there organically —
    its recency is meaningful. For a pinned project it is meaningless: the
    pin exists precisely because recency does not describe it. Left alone,
    the most frequently pushed pinned project wins the most prominent slot in
    the section, which inverts the intent (observed live: family-sites, in
    permanent maintenance mode, sorted ahead of Tastemakers and Judge Tool).

    Post-sort mutation rather than a sort-key sentinel, matching
    pin_self_last() and for the same reasons — see
    docs/solutions/logic-errors/self-referential-repo-event-floating-project-card.md.
    """

    def test_pinned_project_moves_below_organic_backburner(self):
        back = ["family-sites", "tastemakers", "ktv-singer", "judge-tool"]
        _projects.pin_backburner_last({"family-sites": _projects.PIN_BACKBURNER}, back)
        assert back == ["tastemakers", "ktv-singer", "judge-tool", "family-sites"]

    def test_relative_order_of_unpinned_projects_is_preserved(self):
        back = ["a", "pinned", "b", "c"]
        _projects.pin_backburner_last({"pinned": _projects.PIN_BACKBURNER}, back)
        assert back == ["a", "b", "c", "pinned"]

    def test_multiple_pins_keep_their_relative_order_at_the_bottom(self):
        back = ["p1", "organic", "p2"]
        _projects.pin_backburner_last(
            {"p1": _projects.PIN_BACKBURNER, "p2": _projects.PIN_BACKBURNER}, back)
        assert back == ["organic", "p1", "p2"]

    def test_pin_active_entries_are_ignored(self):
        """Only back-burner pins sink; an active pin has no business here."""
        back = ["a", "b"]
        _projects.pin_backburner_last({"a": _projects.PIN_ACTIVE}, back)
        assert back == ["a", "b"]

    def test_noop_with_no_pins(self):
        back = ["a", "b", "c"]
        _projects.pin_backburner_last({}, back)
        assert back == ["a", "b", "c"]

    def test_self_slug_still_wins_the_last_position(self):
        """pin_self_last runs after this, so jameschang-co stays absolutely
        last even when a pinned project is also sinking."""
        back = ["jameschang-co", "family-sites", "tastemakers"]
        _projects.pin_backburner_last({"family-sites": _projects.PIN_BACKBURNER}, back)
        _projects.pin_self_last(_projects.SELF_SLUG, back)
        assert back[-1] == "jameschang-co"
        assert back == ["tastemakers", "family-sites", "jameschang-co"]


class TestPinDoesNotAlterRenderedEvidence:
    """A pin overrides the DECISION, downstream of measurement.

    The card must still render the project's real most-recent commit, so a
    reader sees the raw signal and can disagree with the label. This is the
    property that separates an honest override from a lie, and it is exactly
    what the rejected `shipping_repos: []` approach destroys. The concrete
    regression: someone "optimizes" the sync by skipping event fetches for
    pinned projects, and every pinned card silently starts claiming
    "no recent activity" for work that shipped this morning.
    """

    EVENT = [{"summary": "Update the bio photo",
              "url": "https://github.com/thirstypig/rhyschang/commit/abc123",
              "time": "2026-08-04T18:00:00Z",
              "_repo": "thirstypig/rhyschang"}]

    def test_pinned_backburner_project_still_renders_its_real_activity(self):
        pinned_down = [p for p in _projects.load_config()
                       if p.get("pin") == _projects.PIN_BACKBURNER]
        assert pinned_down, "no back-burner-pinned project in config to exercise"
        for project in pinned_down:
            html = _projects.render_card(project, self.EVENT, "Aug 5, 2026")
            assert "nb-proj-activity--empty" not in html, (
                f"{project['slug']} is pinned but its evidence was suppressed")
            assert "Update the bio photo" in html
            assert "github.com" in html


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
        assert "what&#39;s coming next" in html
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


class TestConfigPinsReachTheClassifier:
    """The config -> classifier seam, which nothing else covers.

    main() builds the `pinned` mapping with a one-line dict comprehension:

        pinned = {p["slug"]: p["pin"] for p in projects if p.get("pin")}

    TestProjectPinning proves classify_projects() honors a pin.
    TestLoadConfig proves the config declares one. Neither touches the wire
    between them — delete that line and every one of those tests still
    passes while /now silently renders the pinned projects in the wrong
    section. That is the regression this prevents.
    """

    def test_backburner_pins_survive_a_full_render(self, monkeypatch):
        from datetime import datetime, timezone
        from urllib.error import URLError

        captured = {}
        config = _projects.load_config()
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        repos = _projects.shipping_repos_for(config)

        # Give EVERY repo a push from just now. Under the recency rule alone
        # every project would be active, so any project still landing in
        # back-burner got there via its pin and nothing else.
        monkeypatch.setattr(_projects, "fetch_github_events", lambda token, rs: [
            {"type": "PushEvent", "created_at": now_iso, "repo": {"name": r},
             "payload": {"ref": "refs/heads/main", "head": "deadbeef"}}
            for r in rs])
        monkeypatch.setattr(_projects, "_events_ok", len(repos))
        monkeypatch.setattr(_projects, "_events_err", 0)
        monkeypatch.setattr(_projects, "_repo_key_mismatches", [])

        def _offline(*a, **kw):        # skip the /commits/{sha} enrichment
            raise URLError("offline")
        monkeypatch.setattr(_projects, "fetch_json", _offline)
        monkeypatch.setattr(_projects, "content_changed", lambda old, new: True)
        monkeypatch.setattr(_projects, "record_heartbeat", lambda slug, **kw: None)
        monkeypatch.setattr(_projects, "write_now_html",
                            lambda c: captured.__setitem__("html", c))

        _projects.main()

        assert "html" in captured, "main() never reached write_now_html"
        html = captured["html"]

        def block(name):
            return html.split(f"<!-- {name}-START -->")[1] \
                       .split(f"<!-- {name}-END -->")[0]

        active_block, back_block = block("ACTIVE-PROJECTS"), block("BACKBURNER-PROJECTS")
        pinned_seen = 0
        for project in config:
            marker = f"<!-- TLDR-{project['slug']}-START -->"
            pin = project.get("pin")
            if pin == _projects.PIN_BACKBURNER:
                pinned_seen += 1
                assert marker in back_block, f"{project['slug']} pin was dropped"
                assert marker not in active_block
            elif pin == _projects.PIN_ACTIVE:
                pinned_seen += 1
                assert marker in active_block, f"{project['slug']} pin was dropped"
            else:
                assert marker in active_block, (
                    f"{project['slug']} has a fresh event and no pin, so it "
                    f"should be active — the fixture may have drifted")
        assert pinned_seen, "config declares no pins; this test proves nothing"


JARGON_MARKERS = [
    r"`", r"/api/", r"\.(md|tsx?|mjs|py|json)\b", r"session \d+",
    r"\b(IDOR|JWT|CSRF|XSS|SSE|CORS)\b",
    r"\b(Redis|PgBouncer|WebSocket|pdf-lib|Laravel|Socket\.IO|Alpaca|Retell)\b",
    r"\b(middleware|endpoint|schema|migration|backend|repo)\b",
]


class TestCardCopyIsNonTechnical:
    """Card copy on /now is written for non-technical readers."""

    def test_no_jargon_in_card_copy(self):
        import re
        config = _projects.load_config()
        offenders = []
        for project in config:
            fields = [project.get("desc", ""), project.get("next_up", "")]
            fields += project.get("roadmap_items") or []
            for text in fields:
                for pattern in JARGON_MARKERS:
                    if re.search(pattern, text, re.IGNORECASE):
                        offenders.append((project["slug"], pattern, text))
        assert offenders == [], f"technical language in card copy: {offenders}"


class TestRoadmapLabelCopy:
    """The /now roadmap label is reader-facing copy, not a technical term."""

    def test_label_is_plain_english(self):
        project = {
            "slug": "demo", "name": "Demo", "url": "https://example.com",
            "url_label": "example.com", "status_badge": "shipping",
            "maturity": "beta", "desc": "A demo.", "next_up": "Ship it.",
            "roadmap_items": ["First thing", "Second thing"],
        }
        html = _projects.render_card(project, [], "just now")
        assert "what&#39;s coming next" in html
        assert "upcoming roadmap features" not in html
