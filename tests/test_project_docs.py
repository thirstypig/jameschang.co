"""Unit tests for bin/update-project-docs.py — markdown parsers + renderers
+ per-project adapters + sync_one fail-safe + adapter architecture."""

import importlib
import json
import os
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

_docs = importlib.import_module("update-project-docs")


# ---------------------------------------------------------------------------
# Changelog parser (default heading-line convention)
# ---------------------------------------------------------------------------

class TestParseChangelog:
    def test_returns_empty_on_empty_or_no_headings(self):
        assert _docs.parse_changelog("") == []
        assert _docs.parse_changelog(None) == []
        assert _docs.parse_changelog("# Title\n\nNo H2 here.") == []

    def test_parses_single_release_with_tag(self):
        md = (
            "## v0.12.0 — 2026-04-14 — security\n"
            "### Code review batch\n\n"
            "- Fixed SoQL injection\n"
            "- Added auth middleware\n"
        )
        releases = _docs.parse_changelog(md)
        assert len(releases) == 1
        r = releases[0]
        assert r["version"] == "v0.12.0"
        assert r["date"] == "2026-04-14"
        assert r["tags"] == ["security"]
        assert r["title"] == "Code review batch"
        assert r["bullets"] == ["Fixed SoQL injection", "Added auth middleware"]

    def test_parses_multiple_tags_comma_separated(self):
        md = "## v0.5.0 — 2026-03-01 — security, improvement\n### Title\n\n- item\n"
        r = _docs.parse_changelog(md)[0]
        assert r["tags"] == ["security", "improvement"]

    def test_no_tags_when_third_segment_missing(self):
        md = "## v0.1.0 — 2026-01-01\n### Title\n\n- item\n"
        r = _docs.parse_changelog(md)[0]
        assert r["tags"] == []

    def test_date_can_include_trailing_suffix(self):
        md = "## v0.57.0 — 2026-04-13 · Session 63 — feature\n### Launch readiness\n\n- thing\n"
        r = _docs.parse_changelog(md)[0]
        assert r["version"] == "v0.57.0"
        assert r["date"] == "2026-04-13 · Session 63"
        assert r["tags"] == ["feature"]

    def test_ascii_double_hyphen_fallback(self):
        md = "## v0.1.0 -- 2026-01-01 -- feature\n### Title\n\n- item\n"
        r = _docs.parse_changelog(md)[0]
        assert r["version"] == "v0.1.0"
        assert r["date"] == "2026-01-01"
        assert r["tags"] == ["feature"]

    def test_parses_multiple_releases_in_document_order(self):
        md = (
            "## v0.2.0 — 2026-02-01 — feature\n### Second\n\n- two\n\n"
            "## v0.1.0 — 2026-01-01 — feature\n### First\n\n- one\n"
        )
        releases = _docs.parse_changelog(md)
        assert [r["version"] for r in releases] == ["v0.2.0", "v0.1.0"]

    def test_bullet_continuation_lines_get_joined(self):
        md = (
            "## v0.1.0 — 2026-01-01 — feature\n### Title\n\n"
            "- Long bullet that\n"
            "  continues on the next indented line\n"
            "- Second bullet\n"
        )
        bullets = _docs.parse_changelog(md)[0]["bullets"]
        assert bullets == [
            "Long bullet that continues on the next indented line",
            "Second bullet",
        ]

    def test_release_without_title_h3_still_parses(self):
        md = "## v0.1.0 — 2026-01-01 — feature\n\n- naked bullet\n"
        r = _docs.parse_changelog(md)[0]
        assert r["title"] == ""
        assert r["bullets"] == ["naked bullet"]


class TestRenderChangelog:
    def test_returns_empty_string_on_empty_list(self):
        assert _docs.render_changelog([]) == ""

    def test_emits_release_article_with_head_and_body(self):
        releases = [{
            "version": "v0.1.0", "date": "2026-01-01",
            "tags": ["feature"], "title": "Hello",
            "bullets": ["Did the thing"],
        }]
        html = _docs.render_changelog(releases)
        assert '<article class="release">' in html
        assert '<span class="release-version">v0.1.0</span>' in html
        assert '<span class="release-date">2026-01-01</span>' in html
        assert '<span class="release-tag feature">feature</span>' in html
        assert '<h3 class="release-title">Hello</h3>' in html
        assert '<li>Did the thing</li>' in html

    def test_renders_multiple_tag_spans(self):
        releases = [{
            "version": "v1", "date": "2026-01-01",
            "tags": ["security", "improvement"], "title": "T",
            "bullets": [],
        }]
        html = _docs.render_changelog(releases)
        assert '<span class="release-tag security">security</span>' in html
        assert '<span class="release-tag improvement">improvement</span>' in html

    def test_unknown_tag_gets_sanitized_class(self):
        releases = [{
            "version": "v1", "date": "2026-01-01",
            "tags": ["custom thing!"], "title": "T", "bullets": [],
        }]
        html = _docs.render_changelog(releases)
        assert '<span class="release-tag customthing">custom thing!</span>' in html

    def test_escapes_html_in_title_and_bullets(self):
        releases = [{
            "version": "v1", "date": "2026-01-01", "tags": [],
            "title": "<dangerous>",
            "bullets": ["<script>alert(1)</script>"],
        }]
        html = _docs.render_changelog(releases)
        assert "<dangerous>" not in html
        assert "&lt;dangerous&gt;" in html
        assert "<script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html

    def test_renders_bold_and_code_in_bullets(self):
        releases = [{
            "version": "v1", "date": "2026-01-01", "tags": [],
            "title": "T",
            "bullets": ["**Security:** use `safe_url()`"],
        }]
        html = _docs.render_changelog(releases)
        assert "<strong>Security:</strong> use <code>safe_url()</code>" in html


# ---------------------------------------------------------------------------
# Convention roadmap parser
# ---------------------------------------------------------------------------

class TestParseRoadmap:
    def test_returns_empty_on_empty_or_no_headings(self):
        assert _docs.parse_roadmap("") == []
        assert _docs.parse_roadmap(None) == []
        assert _docs.parse_roadmap("# Title\n\nNo H2 modules.") == []

    def test_parses_module_name_and_percent(self):
        md = "## CPSIA / CPC — 60%\nDescription paragraph.\n"
        modules = _docs.parse_roadmap(md)
        assert len(modules) == 1
        assert modules[0]["name"] == "CPSIA / CPC"
        assert modules[0]["percent"] == 60
        assert modules[0]["description"] == "Description paragraph."

    def test_percent_must_be_integer_0_to_999(self):
        valid = "## Foo — 0%\n\n## Bar — 100%\n"
        modules = _docs.parse_roadmap(valid)
        assert [m["percent"] for m in modules] == [0, 100]

    def test_parses_workflow_section(self):
        md = (
            "## Module — 50%\n"
            "Brief description.\n\n"
            "### Workflow\n"
            "1. First step\n"
            "2. Second step\n"
        )
        m = _docs.parse_roadmap(md)[0]
        assert m["workflow"] == ["First step", "Second step"]

    def test_parses_features_section_with_states(self):
        md = (
            "## Module — 50%\n\n"
            "### Features\n"
            "- [x] Done item\n"
            "- [ ] Planned item\n"
            "- [~] Deferred item\n"
        )
        m = _docs.parse_roadmap(md)[0]
        assert m["features"] == [
            ("done", "Done item"),
            ("planned", "Planned item"),
            ("deferred", "Deferred item"),
        ]

    def test_description_collapses_to_single_paragraph(self):
        md = (
            "## Module — 25%\n"
            "First sentence of description.\n"
            "Second line continues it.\n\n"
            "### Workflow\n"
            "1. Step\n"
        )
        m = _docs.parse_roadmap(md)[0]
        assert m["description"] == "First sentence of description. Second line continues it."


class TestRenderRoadmap:
    def test_returns_empty_on_empty_list(self):
        assert _docs.render_roadmap([]) == ""

    def test_emits_module_block_with_head_and_progress(self):
        modules = [{
            "name": "CPSIA / CPC", "percent": 60,
            "description": "Generate CPCs.",
            "workflow": ["Step one"],
            "features": [("done", "Feature A"), ("planned", "Feature B")],
        }]
        html = _docs.render_roadmap(modules)
        assert '<div class="module">' in html
        assert '<h3 class="module-name">CPSIA / CPC</h3>' in html
        assert '<span class="module-progress">Progress: 60%</span>' in html
        assert '<p class="module-desc">Generate CPCs.</p>' in html
        assert '<div class="module-workflow">' in html
        assert '<li>Step one</li>' in html
        assert '<ul class="feature-list">' in html
        assert '<li class="done">Feature A</li>' in html
        assert '<li class="planned">Feature B</li>' in html

    def test_omits_optional_blocks_when_empty(self):
        modules = [{
            "name": "Foo", "percent": 0, "description": "",
            "workflow": [], "features": [],
        }]
        html = _docs.render_roadmap(modules)
        assert '<h3 class="module-name">Foo</h3>' in html
        assert 'module-desc' not in html
        assert 'module-workflow' not in html
        assert 'feature-list' not in html

    def test_no_percent_omits_progress_badge(self):
        """JT phases + FL phases use percent=None — renderer must skip the badge."""
        modules = [{
            "name": "PHASE 1: Security Hardening", "percent": None,
            "description": "", "workflow": [],
            "features": [("done", "X")],
        }]
        html = _docs.render_roadmap(modules)
        assert '<h3 class="module-name">PHASE 1: Security Hardening</h3>' in html
        assert "module-progress" not in html
        assert "Progress:" not in html

    def test_deferred_class_emitted_for_squiggle_state(self):
        modules = [{
            "name": "X", "percent": 0, "description": "",
            "workflow": [], "features": [("deferred", "Later thing")],
        }]
        html = _docs.render_roadmap(modules)
        assert '<li class="deferred">Later thing</li>' in html


# ---------------------------------------------------------------------------
# Aleph roadmap adapter
# ---------------------------------------------------------------------------

class TestParseAlephRoadmap:
    """Aleph adapter — parses docs/plans/roadmap.md with H3 modules, **Workflow:**
    + **Features:** bold-text section markers, and a Project Health table for
    percentages."""

    def test_returns_empty_on_blank_input(self):
        assert _docs.parse_aleph_roadmap("") == []
        assert _docs.parse_aleph_roadmap(None) == []

    def test_extracts_percent_from_project_health_table(self):
        md = (
            "# Roadmap\n\n"
            "## Project Health\n\n"
            "| Area | Progress |\n"
            "|------|----------|\n"
            "| CPSIA / CPC | 100% |\n"
            "| Platform | ~70% |\n\n"
            "## Compliance Module Roadmaps\n\n"
            "### CPSIA / CPC\n\n"
            "Children's product safety...\n"
        )
        modules = _docs.parse_aleph_roadmap(md)
        assert len(modules) == 1
        assert modules[0]["name"] == "CPSIA / CPC"
        assert modules[0]["percent"] == 100

    def test_module_without_health_row_has_no_percent(self):
        md = (
            "## Project Health\n\n"
            "| Area | Progress |\n"
            "|------|----------|\n"
            "| CPSIA / CPC | 100% |\n\n"
            "## Compliance Module Roadmaps\n\n"
            "### Brand New Module\n\n"
            "Just added.\n"
        )
        m = _docs.parse_aleph_roadmap(md)[0]
        assert m["name"] == "Brand New Module"
        assert m["percent"] is None

    def test_parses_workflow_and_features_via_bold_markers(self):
        md = (
            "## Compliance Module Roadmaps\n\n"
            "### CPSIA / CPC\n\n"
            "Description paragraph.\n\n"
            "**Workflow:**\n"
            "1. **Add Product** — Register the children's product.\n"
            "2. **Upload Lab Test** — Attach the PDF.\n\n"
            "**Features:**\n"
            "- [x] Product creation\n"
            "- [ ] Cohort form\n"
            "- [~] e-Filing live\n"
        )
        m = _docs.parse_aleph_roadmap(md)[0]
        assert "Description paragraph." in m["description"]
        assert m["workflow"] == [
            "**Add Product** — Register the children's product.",
            "**Upload Lab Test** — Attach the PDF.",
        ]
        assert m["features"] == [
            ("done", "Product creation"),
            ("planned", "Cohort form"),
            ("deferred", "e-Filing live"),
        ]

    def test_anchors_module_discovery_to_compliance_section(self):
        """H3s inside ## Project Health (or other ## sections before the
        Compliance Module Roadmaps anchor) must NOT be parsed as modules.

        Without the anchor, e.g. a `### Notes` subsection in Project Health
        would leak into the modules list."""
        md = (
            "## Project Health\n\n"
            "### Notes\n\n"
            "Some prose that should NOT be a module.\n\n"
            "## Compliance Module Roadmaps\n\n"
            "### CPSIA / CPC\n\n"
            "Real module.\n"
        )
        modules = _docs.parse_aleph_roadmap(md)
        names = [m["name"] for m in modules]
        assert "Notes" not in names
        assert "CPSIA / CPC" in names


# ---------------------------------------------------------------------------
# Judge Tool roadmap adapter
# ---------------------------------------------------------------------------

class TestParseJTRoadmap:
    """JT adapter — parses docs/PRODUCTION_ROADMAP.md with `## PHASE N: Name`
    headings + task-list bodies. No per-phase percent."""

    def test_returns_empty_on_blank_input(self):
        assert _docs.parse_jt_roadmap("") == []
        assert _docs.parse_jt_roadmap(None) == []
        assert _docs.parse_jt_roadmap("# Title\nNo phases.") == []

    def test_parses_single_phase(self):
        md = (
            "# Roadmap\n\n"
            "## PHASE 1: Security Hardening (Do First)\n\n"
            "- [x] CSP shipped\n"
            "- [ ] Rate limit\n"
            "- [~] Per-user PINs\n"
        )
        modules = _docs.parse_jt_roadmap(md)
        assert len(modules) == 1
        m = modules[0]
        assert m["name"] == "Security Hardening (Do First)"
        assert m["percent"] is None
        assert m["description"] == ""
        assert m["workflow"] == []
        assert m["features"] == [
            ("done", "CSP shipped"),
            ("planned", "Rate limit"),
            ("deferred", "Per-user PINs"),
        ]

    def test_phase_with_h3_subsections_extracts_task_items_only(self):
        """PHASE 6 in the live file has H3 subsections with prose tables.
        Non-task-list bullets must be silently dropped."""
        md = (
            "## PHASE 6: Analytics\n\n"
            "### Current setup\n\n"
            "**What we track:**\n"
            "- Google Analytics 4\n"
            "- AuditLog model\n\n"
            "**Rationale:** prose paragraph\n\n"
            "- [x] Real task item\n"
            "- [ ] Another planned\n"
        )
        m = _docs.parse_jt_roadmap(md)[0]
        # Only the [x] and [ ] items count; bare bullets are ignored.
        assert m["features"] == [
            ("done", "Real task item"),
            ("planned", "Another planned"),
        ]

    def test_multiple_phases_preserve_document_order(self):
        md = (
            "## PHASE 1: Alpha\n- [x] one\n\n"
            "## PHASE 2: Beta\n- [ ] two\n\n"
            "## PHASE 3: Gamma\n- [~] three\n"
        )
        modules = _docs.parse_jt_roadmap(md)
        assert [m["name"] for m in modules] == ["Alpha", "Beta", "Gamma"]


# ---------------------------------------------------------------------------
# Fantastic Leagues Tsx roadmap adapter
# ---------------------------------------------------------------------------

class TestParseFLRoadmap:
    """FL adapter — extracts productRoadmap from Roadmap.tsx via regex +
    brace-counted slicing. Brittle by design (adapter to source we don't own)."""

    def test_returns_empty_on_blank_or_missing_array(self):
        assert _docs.parse_fl_roadmap("") == []
        assert _docs.parse_fl_roadmap("import React from 'react';\n") == []
        assert _docs.parse_fl_roadmap("const otherThing = [1, 2, 3];") == []

    def test_parses_single_phase_with_items(self):
        tsx = (
            'const productRoadmap: RoadmapPhase[] = [\n'
            '  {\n'
            '    id: "engagement",\n'
            '    label: "In-Season Engagement",\n'
            '    timeframe: "April – September 2026",\n'
            '    items: [\n'
            '      { title: "In-App Chat", status: "done" },\n'
            '      { title: "Push Notifications", status: "planned" },\n'
            '    ],\n'
            '  },\n'
            '];\n'
        )
        modules = _docs.parse_fl_roadmap(tsx)
        assert len(modules) == 1
        m = modules[0]
        assert m["name"] == "In-Season Engagement"
        assert m["description"] == "April – September 2026"
        assert m["percent"] is None
        assert m["features"] == [
            ("done", "In-App Chat"),
            ("planned", "Push Notifications"),
        ]

    def test_in_progress_status_collapses_to_planned(self):
        """FL source uses 'in-progress' but our .module CSS only styles
        done/planned/deferred. Document the lossy mapping explicitly."""
        tsx = (
            'const productRoadmap: RoadmapPhase[] = [\n'
            '  { label: "X", items: [ { title: "T", status: "in-progress" } ] },\n'
            '];\n'
        )
        m = _docs.parse_fl_roadmap(tsx)[0]
        assert m["features"] == [("planned", "T")]

    def test_handles_nested_braces_in_descriptions(self):
        """Item descriptions can contain `{` and `}` (e.g. code snippets in
        prose). Brace-counter must NOT mistake string braces for object braces."""
        tsx = (
            'const productRoadmap: RoadmapPhase[] = [\n'
            '  {\n'
            '    label: "Phase",\n'
            '    items: [\n'
            '      { title: "A {with} braces", description: "more {} text", status: "done" },\n'
            '    ],\n'
            '  },\n'
            '];\n'
        )
        m = _docs.parse_fl_roadmap(tsx)[0]
        assert m["features"] == [("done", "A {with} braces")]

    def test_multiple_phases(self):
        tsx = (
            'const productRoadmap: RoadmapPhase[] = [\n'
            '  { label: "Alpha", items: [{ title: "a1", status: "done" }] },\n'
            '  { label: "Beta",  items: [{ title: "b1", status: "planned" }] },\n'
            '];\n'
        )
        modules = _docs.parse_fl_roadmap(tsx)
        assert [m["name"] for m in modules] == ["Alpha", "Beta"]


class TestFLHelpers:
    """The brace/bracket-counter helpers underpin the FL parser — pin their
    behavior so future refactors can't silently break Tsx extraction."""

    def test_slice_balanced_handles_nested_brackets(self):
        s = "before [a, [b, c], d] after"
        out = _docs._slice_balanced(s, s.index("["), "[", "]")
        assert out == "a, [b, c], d"

    def test_slice_balanced_ignores_brackets_in_strings(self):
        s = 'x = ["[fake]", "real"]'
        out = _docs._slice_balanced(s, s.index("["), "[", "]")
        assert out == '"[fake]", "real"'

    def test_iter_top_level_objects_yields_each(self):
        body = ' { a: 1 }, { b: 2, c: { nested: true } } '
        out = list(_docs._iter_top_level_objects(body))
        assert len(out) == 2
        assert out[0] == "{ a: 1 }"
        assert out[1] == "{ b: 2, c: { nested: true } }"


# ---------------------------------------------------------------------------
# Adapter pattern + factory
# ---------------------------------------------------------------------------

class TestMakeAdapter:
    """make_adapter returns a closure that fetches + parses + returns
    (parsed, error_or_none). Used by every PROJECT_DOCS entry."""

    def test_returns_parsed_data_on_success(self):
        with patch.object(_docs, "fetch_file", return_value="## Foo — 50%\n"):
            adapter = _docs.make_adapter("repo", "path.md", _docs.parse_roadmap)
            parsed, error = adapter(token=None)
        assert error is None
        assert parsed[0]["name"] == "Foo"

    def test_returns_source_missing_error_on_fetch_failure(self):
        with patch.object(_docs, "fetch_file", return_value=None):
            adapter = _docs.make_adapter("r", "p", _docs.parse_roadmap)
            parsed, error = adapter(token=None)
        assert parsed is None
        assert "source missing" in error
        assert "r/p" in error

    def test_returns_unparseable_error_on_empty_parse(self):
        with patch.object(_docs, "fetch_file", return_value="no headings"):
            adapter = _docs.make_adapter("r", "p", _docs.parse_roadmap)
            parsed, error = adapter(token=None)
        assert parsed is None
        assert error == "empty or unparseable"


# ---------------------------------------------------------------------------
# Inline helpers
# ---------------------------------------------------------------------------

class TestRenderInline:
    def test_escapes_then_renders_bold_and_code(self):
        assert _docs.render_inline("plain") == "plain"
        assert _docs.render_inline("**bold**") == "<strong>bold</strong>"
        assert _docs.render_inline("`code`") == "<code>code</code>"

    def test_escapes_angle_brackets_first(self):
        out = _docs.render_inline("Uses <Component>")
        assert "<Component>" not in out
        assert "&lt;Component&gt;" in out


class TestSanitizeClass:
    def test_lowercases_and_strips_non_alnum(self):
        assert _docs._sanitize_class("Feature Tag!") == "featuretag"
        assert _docs._sanitize_class("a-b_c") == "a-bc"


# ---------------------------------------------------------------------------
# sync_one fail-safe behavior (adapter signature)
# ---------------------------------------------------------------------------

class TestSyncOneFailSafe:
    """sync_one must NEVER crash on bad input; missing source/markers/parse
    yields 'skipped' or 'error' and records a per-doc heartbeat warning."""

    def _isolated_heartbeat(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(path)
        return path

    def _adapter_returning(self, parsed, error):
        """Build a stub adapter for tests."""
        def adapter(token):
            return parsed, error
        return adapter

    def test_source_missing_returns_skipped_no_heartbeat_on_bootstrap(self):
        """Bootstrap path: feed has never succeeded → source-missing must NOT
        write a heartbeat. Otherwise the staleness monitor would open a false-
        positive GitHub issue on day 1."""
        path = self._isolated_heartbeat()
        try:
            adapter = self._adapter_returning(None, "source missing: repo/path.md")
            with patch("_shared.HEARTBEAT_FILE", path):
                result = _docs.sync_one("aleph", "changelog", adapter, token=None)
            assert result == "skipped"
            assert not os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_source_missing_records_error_when_feed_known(self):
        """Ongoing path: feed has succeeded before → source-missing records
        `last_error` while preserving `last_success_utc`."""
        path = self._isolated_heartbeat()
        try:
            seed = {
                "project-docs:aleph-changelog": {
                    "last_success_utc": "2026-01-01T00:00:00+00:00",
                }
            }
            with open(path, "w") as f:
                json.dump(seed, f)
            adapter = self._adapter_returning(None, "source missing")
            with patch("_shared.HEARTBEAT_FILE", path):
                result = _docs.sync_one("aleph", "changelog", adapter, token=None)
            assert result == "skipped"
            data = json.loads(open(path).read())
            entry = data["project-docs:aleph-changelog"]
            assert "last_error" in entry
            assert entry["last_success_utc"] == "2026-01-01T00:00:00+00:00"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_unknown_doctype_returns_error(self):
        path = self._isolated_heartbeat()
        try:
            adapter = self._adapter_returning([{"any": "data"}], None)
            with patch("_shared.HEARTBEAT_FILE", path):
                result = _docs.sync_one("x", "todos", adapter, token=None)
            assert result == "error"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_destination_missing_returns_error(self):
        path = self._isolated_heartbeat()
        try:
            parsed = [{"version": "v1", "date": "2026-01-01",
                       "tags": [], "title": "T", "bullets": ["x"]}]
            adapter = self._adapter_returning(parsed, None)
            with patch.object(_docs, "dest_path", return_value="/nope/missing/path.html"), \
                 patch("_shared.HEARTBEAT_FILE", path):
                result = _docs.sync_one("aleph", "changelog", adapter, token=None)
            assert result == "error"
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestSyncOneAppliesPublicCopy:
    """Roadmap docs pass through the copy layer; drops become a non-fatal note."""

    def _isolated_heartbeat(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(path)
        return path

    def test_roadmap_drops_are_recorded_as_partial_success(self, tmp_path):
        hb = self._isolated_heartbeat()
        dest = tmp_path / "index.html"
        dest.write_text(
            "<html><!-- ROADMAP-START -->old<!-- ROADMAP-END --></html>",
            encoding="utf-8")
        modules = [_module("Security Hardening (Do First)"), _module("Nice-to-Haves")]

        def adapter(token):
            return modules, None

        try:
            with patch("_shared.HEARTBEAT_FILE", hb), \
                 patch.object(_docs, "load_roadmap_copy",
                              return_value={"judge-tool":
                                            {"public_phases": ["Nice-to-Haves"]}}), \
                 patch.object(_docs, "dest_path", return_value=str(dest)):
                result = _docs.sync_one("judge-tool", "roadmap", adapter, token=None)

            assert result == "ok"
            with open(hb, encoding="utf-8") as f:
                entry = json.load(f)["project-docs:judge-tool-roadmap"]
            # partial_success → BOTH fields present
            assert "last_success_utc" in entry
            assert "Security Hardening" in entry["last_error"]
            assert "Security Hardening" not in dest.read_text(encoding="utf-8")
        finally:
            if os.path.exists(hb):
                os.unlink(hb)

    def test_clean_roadmap_records_no_error(self, tmp_path):
        hb = self._isolated_heartbeat()
        dest = tmp_path / "index.html"
        dest.write_text(
            "<html><!-- ROADMAP-START -->old<!-- ROADMAP-END --></html>",
            encoding="utf-8")

        def adapter(token):
            return [_module("Nice-to-Haves")], None

        try:
            with patch("_shared.HEARTBEAT_FILE", hb), \
                 patch.object(_docs, "load_roadmap_copy", return_value={}), \
                 patch.object(_docs, "dest_path", return_value=str(dest)):
                _docs.sync_one("judge-tool", "roadmap", adapter, token=None)
            with open(hb, encoding="utf-8") as f:
                entry = json.load(f)["project-docs:judge-tool-roadmap"]
            assert "last_error" not in entry
        finally:
            if os.path.exists(hb):
                os.unlink(hb)

    def test_changelog_never_enters_the_copy_layer(self, tmp_path):
        hb = self._isolated_heartbeat()
        dest = tmp_path / "index.html"
        dest.write_text(
            "<html><!-- CHANGELOG-START -->x<!-- CHANGELOG-END --></html>",
            encoding="utf-8")

        def adapter(token):
            return [], None

        try:
            with patch("_shared.HEARTBEAT_FILE", hb), \
                 patch.object(_docs, "apply_public_copy") as spy, \
                 patch.object(_docs, "dest_path", return_value=str(dest)):
                _docs.sync_one("aleph", "changelog", adapter, token=None)
            spy.assert_not_called()
        finally:
            if os.path.exists(hb):
                os.unlink(hb)


# ---------------------------------------------------------------------------
# Replace marker (variant)
# ---------------------------------------------------------------------------

class TestReplaceMarkerIn:
    def test_replaces_content_between_markers(self):
        content = "before\n<!-- CHANGELOG-START -->\nold\n<!-- CHANGELOG-END -->\nafter"
        new, ok = _docs.replace_marker_in(content, "CHANGELOG", "new content", "test.html")
        assert ok is True
        assert "new content" in new
        assert "old" not in new
        assert "before" in new and "after" in new

    def test_missing_markers_returns_false(self):
        content = "no markers here"
        new, ok = _docs.replace_marker_in(content, "CHANGELOG", "x", "test.html")
        assert ok is False
        assert new == content

    def test_duplicate_markers_returns_false(self):
        content = (
            "<!-- CHANGELOG-START -->a<!-- CHANGELOG-END -->\n"
            "<!-- CHANGELOG-START -->b<!-- CHANGELOG-END -->"
        )
        new, ok = _docs.replace_marker_in(content, "CHANGELOG", "x", "test.html")
        assert ok is False


# ---------------------------------------------------------------------------
# Idempotency — render functions must be deterministic
# ---------------------------------------------------------------------------

class TestProjectDocsIdempotency:
    """Render functions must be deterministic: same input → same output.

    Guards against the trap where re-rendering changes output unexpectedly,
    causing false diffs and unnecessary commits.
    """

    def test_render_changelog_is_deterministic(self):
        """Same releases → identical HTML."""
        releases = [
            {
                "version": "1.0.0",
                "date": "2026-06-25",
                "title": "Initial release",
                "tags": ["major"],
                "bullets": ["Feature A", "Feature B"],
            },
            {
                "version": "0.9.0",
                "date": "2026-06-20",
                "title": "Beta",
                "tags": ["beta"],
                "bullets": ["Early access"],
            },
        ]
        html1 = _docs.render_changelog(releases)
        html2 = _docs.render_changelog(releases)
        assert html1 == html2

    def test_render_changelog_empty_is_deterministic(self):
        """Empty releases → consistent output."""
        html1 = _docs.render_changelog([])
        html2 = _docs.render_changelog([])
        assert html1 == html2

    def test_render_roadmap_is_deterministic(self):
        """Same modules → identical HTML."""
        modules = [
            {
                "name": "Phase 1",
                "percent": 100,
                "description": "Initial features",
                "workflow": None,
                "features": [
                    {"title": "Feature A", "icon": None},
                    {"title": "Feature B", "icon": None},
                ],
            },
            {
                "name": "Phase 2",
                "percent": 50,
                "description": "Expansion",
                "workflow": None,
                "features": [{"title": "Feature C", "icon": None}],
            },
        ]
        html1 = _docs.render_roadmap(modules)
        html2 = _docs.render_roadmap(modules)
        assert html1 == html2

    def test_render_roadmap_empty_is_deterministic(self):
        """Empty modules → consistent output."""
        html1 = _docs.render_roadmap([])
        html2 = _docs.render_roadmap([])
        assert html1 == html2


# ---------------------------------------------------------------------------
# Config sanity — PROJECT_DOCS shape + destination bootstrap invariants
# ---------------------------------------------------------------------------

class TestProjectDocsConfig:
    def test_expected_entries_present(self):
        """PROJECT_DOCS pins the (slug, doctype) sync targets — update this
        test when adding or removing a sync target."""
        entries = {(slug, doctype) for slug, doctype, _adapter in _docs.PROJECT_DOCS}
        assert entries == {
            ("aleph", "changelog"),
            ("aleph", "roadmap"),
            ("fantastic-leagues", "changelog"),
            ("fantastic-leagues", "roadmap"),
            ("judge-tool", "changelog"),
            ("judge-tool", "roadmap"),
        }

    def test_every_adapter_is_callable(self):
        """Architectural invariant: every PROJECT_DOCS entry's adapter must be
        a callable returning a 2-tuple. Without this, sync_one would crash."""
        for slug, doctype, adapter in _docs.PROJECT_DOCS:
            assert callable(adapter), f"{slug}/{doctype} adapter is not callable"

    # Destinations that should have markers + page on disk TODAY. JT roadmap +
    # FL roadmap are intentionally absent — the adapters are built but the
    # destination wiring (markers on JT roadmap page; creating FL roadmap
    # sub-page) is deferred. Update this list as destinations come online.
    WIRED_DESTINATIONS = [
        ("aleph", "changelog"),
        ("aleph", "roadmap"),
        ("fantastic-leagues", "changelog"),
        ("fantastic-leagues", "roadmap"),
        ("judge-tool", "changelog"),
        ("judge-tool", "roadmap"),
    ]

    def test_wired_destinations_exist_with_markers(self):
        """Bootstrap requirement for the subset of destinations that ARE
        wired today: every page exists with the expected marker pair."""
        repo_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
        for slug, doctype in self.WIRED_DESTINATIONS:
            dest = os.path.join(repo_root, "projects", slug, doctype, "index.html")
            assert os.path.exists(dest), f"Missing destination page: {dest}"
            with open(dest, "r", encoding="utf-8") as f:
                body = f.read()
            marker = doctype.upper()
            assert f"<!-- {marker}-START -->" in body, f"{dest} missing {marker}-START"
            assert f"<!-- {marker}-END -->" in body, f"{dest} missing {marker}-END"


def _module(name, features=None, description="", workflow=None):
    return {
        "name": name, "percent": None, "description": description,
        "workflow": workflow or [], "features": features or [],
    }


class TestApplyPublicCopyPhaseAllowlist:
    def test_unlisted_phase_is_dropped(self):
        config = {"judge-tool": {"public_phases": ["Nice-to-Haves"]}}
        modules = [_module("Security Hardening (Do First)"), _module("Nice-to-Haves")]
        kept, dropped = _docs.apply_public_copy(
            "judge-tool", modules, config)
        assert [m["name"] for m in kept] == ["Nice-to-Haves"]
        assert any("Security Hardening" in d for d in dropped)

    def test_project_absent_from_config_passes_through(self):
        modules = [_module("CPSIA / CPC"), _module("Prop 65")]
        kept, dropped = _docs.apply_public_copy(
            "fantastic-leagues", modules, {})
        assert [m["name"] for m in kept] == ["CPSIA / CPC", "Prop 65"]
        assert dropped == []

    def test_no_public_phases_key_keeps_all_phases(self):
        # Rules present for the slug but empty: no public_phases key (Rule 1
        # off) and no plain_english key (Rule 2 off, distinct from Rule 2
        # being ON with an empty map — see TestApplyPublicCopyPlainEnglish
        # .test_unmapped_module_name_drops_whole_module, which fail-closes).
        config = {"aleph": {}}
        modules = [_module("CPSIA / CPC"), _module("Prop 65")]
        kept, dropped = _docs.apply_public_copy("aleph", modules, config)
        assert len(kept) == 2


class TestApplyPublicCopyPlainEnglish:
    def test_mapped_feature_is_replaced_and_state_preserved(self):
        config = {"aleph": {"plain_english": {
            "CPSIA / CPC": "Children's product safety",
            "CPC PDF generation (pdf-lib)": "Generate the certificate as a PDF",
        }}}
        modules = [_module("CPSIA / CPC",
                           features=[("planned", "CPC PDF generation (pdf-lib)")])]
        kept, dropped = _docs.apply_public_copy("aleph", modules, config)
        assert kept[0]["name"] == "Children's product safety"
        assert kept[0]["features"] == [("planned", "Generate the certificate as a PDF")]
        assert dropped == []

    def test_unmapped_feature_is_dropped_and_reported(self):
        config = {"aleph": {"plain_english": {"CPSIA / CPC": "Children's product safety"}}}
        modules = [_module("CPSIA / CPC",
                           features=[("planned", "Server-side cohort enforcement")])]
        kept, dropped = _docs.apply_public_copy("aleph", modules, config)
        assert kept[0]["features"] == []
        assert any("Server-side cohort enforcement" in d for d in dropped)

    def test_unmapped_module_name_drops_whole_module(self):
        config = {"aleph": {"plain_english": {}}}
        modules = [_module("CPSIA / CPC", features=[("planned", "x")])]
        kept, dropped = _docs.apply_public_copy("aleph", modules, config)
        assert kept == []
        assert any("CPSIA / CPC" in d for d in dropped)

    def test_description_and_workflow_are_translated(self):
        config = {"aleph": {"plain_english": {
            "CPSIA / CPC": "Children's product safety",
            "Raw description.": "Plain description.",
            "Add Product": "Add the product",
        }}}
        modules = [_module("CPSIA / CPC", description="Raw description.",
                           workflow=["Add Product"])]
        kept, _ = _docs.apply_public_copy("aleph", modules, config)
        assert kept[0]["description"] == "Plain description."
        assert kept[0]["workflow"] == ["Add the product"]

    def test_public_phases_without_plain_english_filters_only(self):
        """A project may opt into Rule 1 without Rule 2 — surviving phases
        then render their source text unchanged."""
        config = {"judge-tool": {"public_phases": ["Nice-to-Haves"]}}
        modules = [_module("Security Hardening (Do First)"),
                   _module("Nice-to-Haves", features=[("planned", "Raw item text")])]
        kept, dropped = _docs.apply_public_copy("judge-tool", modules, config)
        assert [m["name"] for m in kept] == ["Nice-to-Haves"]
        assert kept[0]["features"] == [("planned", "Raw item text")]
        assert not any("not translated" in d for d in dropped)

    def test_idempotent(self):
        config = {"aleph": {"plain_english": {
            "CPSIA / CPC": "Children's product safety",
            "CPC PDF generation (pdf-lib)": "Generate the certificate as a PDF",
        }}}
        modules = [_module("CPSIA / CPC",
                           features=[("planned", "CPC PDF generation (pdf-lib)")])]
        first, _ = _docs.apply_public_copy("aleph", modules, config)
        second, _ = _docs.apply_public_copy(
            "aleph", [dict(m) for m in modules], config)
        assert first == second


class TestJudgeToolCopyLayerIsFailClosed:
    """Only author-written plain_english values may survive the copy layer.

    Proven on SYNTHETIC input so no real source text or disclosure string is
    committed to this public repo. Real-source completeness is enforced at
    authoring time and at cron time (heartbeat drift), not here.
    """

    def test_only_authored_strings_survive(self):
        config = _docs.load_roadmap_copy()
        jt = config["judge-tool"]
        allow = jt["public_phases"]
        pe = jt["plain_english"]
        authored = set(pe.values())

        # A real feature map key (mapped, in an allowlisted phase) — survives.
        real_key = next(k for k in pe if k not in set(allow))

        modules = [
            # non-allowlisted phase → whole module dropped, canary must vanish
            _module("Security Hardening (Do First)",
                    features=[("planned", "CANARY-A-must-not-leak")]),
            # allowlisted phase → mapped item survives (renamed), unmapped canary dropped
            _module(allow[0],
                    features=[("planned", real_key),
                              ("planned", "CANARY-B-must-not-leak")]),
        ]

        kept, dropped = _docs.apply_public_copy("judge-tool", modules, config)

        # 1. Every string in the surviving structure is one we authored.
        for m in kept:
            assert m["name"] in authored, f"unauthored module name: {m['name']!r}"
            for _state, text in m["features"]:
                assert text in authored, f"unauthored feature reached output: {text!r}"
            for step in m["workflow"]:
                assert step in authored, f"unauthored workflow step: {step!r}"

        # 2. Canaries were dropped, never carried through.
        flat = " ".join(m["name"] + " " + " ".join(t for _s, t in m["features"])
                        for m in kept)
        assert "CANARY-A" not in flat
        assert "CANARY-B" not in flat
        assert any("CANARY-B" in d for d in dropped)  # reported, not silent
