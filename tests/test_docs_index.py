"""Unit tests for bin/build-docs-index.py — the docs-board manifest builder.

Covers the spec's required set: title extraction, the code-fence guard, section
grouping, exclusions, and the markdown/table renderer.
"""
import importlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))
idx = importlib.import_module("build-docs-index")

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


class TestTitleExtraction:
    def test_first_h1_wins(self):
        body = "\nsome intro\n\n# Real Title\n\n## sub\n"
        assert idx.extract_title(body, "x.md") == "Real Title"

    def test_code_fence_guard(self):
        # A '# comment' inside a fenced block must NOT become the title.
        body = "```bash\n# not the title\necho hi\n```\n\n# Actual Title\n"
        assert idx.extract_title(body, "x.md") == "Actual Title"

    def test_code_fence_only_falls_back_to_filename(self):
        body = "```bash\n# only a comment\n```\n"
        assert idx.extract_title(body, "projects/aleph/PRD-001-cpc-cert.md") == "Cpc Cert"

    def test_tidy_filename_strips_id_prefix(self):
        assert idx.tidy_filename("prds/PRD-007-widget-flow.md") == "Widget Flow"


class TestFrontmatter:
    def test_parses_fields_and_arrays(self):
        content = ("---\nid: PRD-001\ntype: prd\nproject: aleph\n"
                   "tags: [ai, compliance]\nlinks: []\n---\n\n# Title\nbody\n")
        fm, body = idx.parse_frontmatter(content)
        assert fm["id"] == "PRD-001"
        assert fm["type"] == "prd"
        assert fm["tags"] == ["ai", "compliance"]
        assert fm["links"] == []
        assert body.strip().startswith("# Title")

    def test_no_frontmatter_returns_empty(self):
        fm, body = idx.parse_frontmatter("# Just a heading\n")
        assert fm == {}

    def test_block_style_list_parses_to_real_list(self):
        content = ('---\nid: SOL-1\ntags:\n  - "projects-sync"\n  - cron\n'
                   '---\n\n# Title\nbody\n')
        fm, _ = idx.parse_frontmatter(content)
        assert fm["tags"] == ["projects-sync", "cron"]
        assert isinstance(fm["tags"], list)

    def test_quotes_stripped_from_scalar_and_list_items(self):
        content = ('---\ncategory: "logic-errors"\ntitle: \'Single Quoted\'\n'
                   'tags:\n  - "a"\n  - \'b\'\n  - c\n---\n\n# T\nbody\n')
        fm, _ = idx.parse_frontmatter(content)
        assert fm["category"] == "logic-errors"
        assert fm["title"] == "Single Quoted"
        assert fm["tags"] == ["a", "b", "c"]

    def test_inline_array_still_parses(self):
        content = "---\ntags: [ai, \"compliance\", 'x']\n---\n\n# T\nbody\n"
        fm, _ = idx.parse_frontmatter(content)
        assert fm["tags"] == ["ai", "compliance", "x"]

    def test_block_list_stops_at_the_next_key(self):
        # Real solutions frontmatter interleaves a block list with scalar keys:
        #   symptoms:
        #     - ...
        #   root_cause: ...
        # The list loop must halt at the next `key:` line, not swallow it — 8 of
        # the repo's solution docs would lose their category/tags otherwise.
        content = ("---\nsymptoms:\n  - first observed thing\n  - second thing\n"
                   "root_cause: the real cause\ncategory: tooling\n"
                   "tags:\n  - alpha\n  - beta\n---\n\n# T\nbody\n")
        fm, _ = idx.parse_frontmatter(content)
        assert fm["symptoms"] == ["first observed thing", "second thing"]
        assert fm["root_cause"] == "the real cause", "block list swallowed a scalar key"
        assert fm["category"] == "tooling"
        assert fm["tags"] == ["alpha", "beta"]


class TestSectionGrouping:
    def test_types_map_to_expected_sections(self):
        cases = {
            "prd": "product", "roadmap": "product",
            "adr": "engineering", "api-docs": "engineering",
            "costs": "operations", "changelog": "operations",
            "risk": "security", "privacy": "security",
            "glossary": "foundations", "intake-rules": "foundations",
            "note": "notes",
        }
        for t, sec in cases.items():
            assert idx.section_for(t, "x.md") == sec, t

    def test_unknown_type_falls_to_notes(self):
        assert idx.section_for("mystery", "x.md") == "notes"

    def test_path_override_wins(self, monkeypatch):
        monkeypatch.setattr(idx, "PATH_OVERRIDES", {"special/": "product"})
        assert idx.section_for("note", "special/thing.md") == "product"


class TestMarkdownRender:
    def test_table_renders(self):
        md = "| a | b |\n|---|---|\n| 1 | 2 |\n"
        html = idx.md_to_html(md)
        assert "<table>" in html and "<th>a</th>" in html and "<td>1</td>" in html

    def test_heading_and_list_and_inline(self):
        md = "# H\n\n- one **bold**\n- two `code`\n"
        html = idx.md_to_html(md)
        assert "<h1>H</h1>" in html
        assert "<li>one <strong>bold</strong></li>" in html
        assert "<code>code</code>" in html

    def test_code_fence_is_escaped_not_interpreted(self):
        md = "```\n<script>alert(1)</script>\n```\n"
        html = idx.md_to_html(md)
        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_html_comments_stripped(self):
        assert "secret" not in idx.md_to_html("<!-- secret note -->\n\ntext\n")

    def test_link_renders(self):
        html = idx.md_to_html("see [docs](/admin/docs/)\n")
        assert '<a href="/admin/docs/" rel="noopener">docs</a>' in html


class TestExclusionsAndRealIndex:
    def test_templates_and_underscore_files_excluded(self):
        paths = [p for r in idx.ROOTS for p in idx.iter_root_files(r)]
        assert not any("_templates/" in p for p in paths)
        assert not any(os.path.basename(p).startswith("_") for p in paths)

    def test_real_index_builds_and_is_shaped(self):
        index = idx.build_index()
        assert index["docs"], "expected at least one doc"
        assert index["sections"], "expected at least one section"
        for d in index["docs"]:
            assert d["type"] and d["title"] and d["html"]
            assert d["section"] in {s["key"] for s in index["sections"]}

    def test_committed_index_is_public_safe(self):
        # The single most load-bearing invariant: the committed, PUBLIC index.json
        # must carry no secret VALUE. index.json is always committed, so its absence
        # means the gate has nothing to guard — fail loud rather than silently no-op.
        path = os.path.join(REPO_ROOT, "admin", "docs", "index.json")
        assert os.path.exists(path), (
            "admin/docs/index.json is missing — the public-safe guard has nothing "
            "to check; regenerate with `python3 bin/refresh-docs.py`")
        blob = open(path, encoding="utf-8").read()
        leaks = idx.find_secret_values(blob)
        assert not leaks, f"index.json contains secret value(s): {leaks[:3]}"

    def test_committed_index_matches_a_fresh_rebuild(self):
        # The committed index.json embeds the rendered HTML of every source doc.
        # If someone edits a hub doc (a PRD, a solution, a guide) and forgets to
        # run `refresh-docs.py`, the committed board silently goes stale — the
        # exact non-reproducibility class that shipped once this session.
        # `generated` is a volatile timestamp; everything else must match a
        # rebuild from the same tracked sources.
        path = os.path.join(REPO_ROOT, "admin", "docs", "index.json")
        assert os.path.exists(path), "admin/docs/index.json is missing"
        committed = json.load(open(path, encoding="utf-8"))
        fresh = idx.build_index()
        assert fresh["docs"] == committed["docs"], (
            "admin/docs/index.json is stale — a source doc changed without a "
            "rebuild. Run `python3 bin/refresh-docs.py` and commit the result.")
        assert fresh["sections"] == committed["sections"]

    def test_guard_allows_bare_env_var_mentions(self):
        # Naming an env var in prose is public-safe — the names are already
        # public in this repo. Only VALUES are forbidden.
        prose = ("Required GitHub Secrets: `WHOOP_CLIENT_SECRET`, "
                 "`SPOTIFY_REFRESH_TOKEN`. Store the password in 1Password.")
        assert idx.find_secret_values(prose) == []

    def test_guard_allows_bare_token_and_url_var_mentions(self):
        prose = ("Required secrets: `PLEX_TOKEN`, `GCAL_ICAL_URL`. "
                  "See the setup guide for details.")
        assert idx.find_secret_values(prose) == []

    def test_paths_are_repo_relative(self):
        index = idx.build_index()
        hub = [d for d in index["docs"] if "/projects/aleph/" in d["path"]]
        assert hub, "expected at least one Aleph doc"
        for d in hub:
            assert d["path"].startswith("admin/docs/"), d["path"]
        for d in index["docs"]:
            assert not d["path"].startswith("/"), "must be relative, not absolute"
            assert os.path.exists(os.path.join(REPO_ROOT, d["path"])), d["path"]


# --- Class-level regression guard -------------------------------------------
#
# Three prior review rounds each added ONE missing bare keyword (token, then
# key, then secret) to _SECRET_KEYWORD — a compound-enumeration approach that
# guarantees a fourth miss eventually. `find_secret_values()` was generalized
# to match bare STEMS (secret/token/key/password/passphrase/credential)
# instead of compounds built from them.
#
# This table is the guard against round 4: it doesn't test one keyword at a
# time, it tests the CLASS — every representative secret-name *shape* that
# must be caught, and every representative safe shape that must pass. To add
# coverage for a new secret-name pattern, add one line to MUST_CATCH (or
# MUST_PASS for a new safe shape) — no new test function needed.
MUST_CATCH = [
    ("bare *_SECRET, unquoted", "APP_SECRET=abcdefghijklmnopqrstuvwxyz"),
    ("bare *_SECRET, double-quoted", 'JWT_SECRET="abcdefghijklmnopqrstuvwxyz"'),
    ("bare *_SECRET, colon-style", "SESSION_SECRET: abcdefghijklmnopqrstuvwxyz"),
    ("bare *_TOKEN", "PLEX_TOKEN=abcdef0123456789ghijk"),
    ("*_TOKEN with a github_pat-shaped value",
     "TLDR_FETCH_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz012345"),
    ("compound *_TOKEN_KEY", "WHOOP_TOKEN_KEY=s3cr3tpassphrase0000"),
    ("bare *_KEY", "SIGNING_KEY=1234567890abcdef1234"),
    ("bare *_KEY, double-quoted", 'ENCRYPTION_KEY="1234567890abcdef1234"'),
    ("bare *_KEY, colon-style", "MASTER_KEY: 1234567890abcdef1234"),
    ("compound *_CLIENT_SECRET", 'WHOOP_CLIENT_SECRET="a1b2c3d4e5f6g7h8i9j0k1l2"'),
    ("bare *_PASSWORD", "DB_PASSWORD=Sup3rSecretPassw0rd!!"),
    ("bare *_CREDENTIAL", "API_CREDENTIAL=abcdefghijklmnop1234"),
    ("bare *_PASSPHRASE", "APP_PASSPHRASE=abcdef0123456789ghijklmn"),
    ("github_pat_ literal (name-independent)",
     "leaked: github_pat_abcdefghijklmnopqrstuvwxyz0123456789ABCD"),
    ("PEM header (name-independent)", "-----BEGIN RSA PRIVATE KEY-----"),
    ("*_URL secret (full-URL secrecy, not opaque token)",
     "GCAL_ICAL_URL=https://calendar.google.com/ical/abc0123456789/basic.ics"),
    ("*_WEBHOOK_URL secret", "SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/abcdefghijklmnopqrst"),
    ("bare *_URI secret", "DATABASE_URI=https://user:pass@db.example.com/abcdefghijklmnopqrst"),
    ("diceware passphrase, compound *_SECRET (must not slip through the bare-stem slug exemption)",
     "APP_SECRET=correct-horse-battery-staple"),
    ("diceware passphrase, compound *_SECRET, different words",
     "SESSION_SECRET=forest-green-clay-accent"),
    ("diceware passphrase, compound *_TOKEN_KEY (this repo's real WHOOP_TOKEN_KEY shape)",
     "WHOOP_TOKEN_KEY=correct-horse-battery-staple"),
]

MUST_PASS = [
    ("prose naming vars in backticks, no assignment",
     "Required secrets: `PLEX_TOKEN`, `GCAL_ICAL_URL`, `WHOOP_CLIENT_SECRET`. "
     "See the setup guide for details."),
    ("filename constant, not a secret value",
     'TOKEN_ENC = ".whoop-token.enc"'),
    ("public OAuth endpoint URL, not a secret",
     'TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"'),
    ("docs-index section key, a slug not a secret",
     '"key": "site-engineering"'),
    ("docs-index project slug, a slug not a secret",
     '"project": "jameschang-co-eng"'),
]


class TestSecretKeywordClass:
    """Table-driven guard against a 4th round of one-keyword-at-a-time patches."""

    def test_must_catch_every_representative_secret_shape(self):
        misses = [label for label, text in MUST_CATCH if not idx.find_secret_values(text)]
        assert not misses, f"find_secret_values() missed: {misses}"

    def test_must_pass_every_representative_safe_shape(self):
        false_positives = [
            (label, idx.find_secret_values(text)) for label, text in MUST_PASS
            if idx.find_secret_values(text)
        ]
        assert not false_positives, f"find_secret_values() false-positived: {false_positives}"


class TestRootsAndAdapters:
    def test_hub_adapter_skips_docs_without_type(self):
        assert idx.adapt_hub({}, "# No frontmatter\n", "admin/docs/x.md") is None
        assert idx.adapt_hub({"id": "X"}, "# T\n", "admin/docs/x.md") is None

    def test_hub_adapter_maps_fields(self):
        fm = {"id": "PRD-9", "type": "prd", "status": "active",
              "project": "aleph", "stage": "shipped", "tags": ["ai"]}
        doc = idx.adapt_hub(fm, "# Widget\nbody\n", "admin/docs/p/PRD-9.md")
        assert doc["id"] == "PRD-9"
        assert doc["type"] == "prd"
        assert doc["section"] == "product"
        assert doc["title"] == "Widget"
        assert doc["tags"] == ["ai"]
        assert doc["path"] == "admin/docs/p/PRD-9.md"

    def test_missing_root_is_skipped_not_fatal(self):
        ghost = idx.Root("docs/does-not-exist", idx.adapt_hub, False)
        assert list(idx.iter_root_files(ghost)) == []

    def test_single_file_root_yields_that_file(self):
        r = idx.Root("docs/test-plan.md", idx.adapt_hub, False)
        got = list(idx.iter_root_files(r))
        assert len(got) == 1 and got[0].endswith("docs/test-plan.md")

    def test_unparseable_file_is_skipped_not_fatal(self, tmp_path, monkeypatch):
        # A file that explodes on read must not take down the whole build.
        def boom(*a, **k):
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "synthetic")
        real_open = open
        calls = {"n": 0}

        def flaky(path, *a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                boom()
            return real_open(path, *a, **k)

        monkeypatch.setattr("builtins.open", flaky)
        index = idx.build_index()          # must not raise
        assert index["docs"], "one bad file must not empty the index"

    def test_no_local_only_dirs_are_indexed(self):
        # docs/superpowers holds gitignored design specs; index.json is public.
        index = idx.build_index()
        forbidden = ("docs/superpowers/", "docs/archive/", "docs/screenshots/")
        for d in index["docs"]:
            assert not d["path"].startswith(forbidden), d["path"]

    def test_roots_cannot_reach_local_only_dirs(self):
        # The data check above can't fail while ROOTS points only at safe subtrees —
        # so guard the real invariant at its source: no Root may be the bare `docs`
        # dir or any ancestor of a local-only dir, which is how a future edit would
        # start sweeping gitignored specs into the committed, public index.
        local_only = ("docs/superpowers", "docs/archive", "docs/screenshots")
        for root in idx.ROOTS:
            p = root.path.rstrip("/")
            assert p != "docs", (
                f"Root({root.path!r}) would recurse the whole docs/ tree and could "
                "index gitignored local specs into the public index.json")
            for local in local_only:
                assert not (local == p or local.startswith(p + "/")), (
                    f"Root({root.path!r}) is an ancestor of {local}/ — it must never "
                    "be indexed into the public index.json")

    def test_index_is_idempotent(self):
        a = idx.build_index()
        b = idx.build_index()
        a.pop("generated"), b.pop("generated")
        assert a == b, "two consecutive builds must agree"

    def test_guide_adapter_synthesizes_everything(self):
        body = "# Adding a new data feed\n\nSteps follow.\n"
        doc = idx.adapt_guide({}, body, "docs/guides/adding-new-feed.md")
        assert doc["type"] == "guide"
        assert doc["status"] == "active"
        assert doc["project"] == "jameschang-co-eng"
        assert doc["section"] == "site-engineering"
        assert doc["title"] == "Guide — Adding a new data feed"
        assert doc["id"] == "GUIDE-adding-new-feed"
        assert doc["tags"] == []

    def test_guide_title_ignores_h1_in_code_fence(self):
        body = "```bash\n# not the title\n```\n\n# Real Guide\n"
        doc = idx.adapt_guide({}, body, "docs/guides/x.md")
        assert doc["title"] == "Guide — Real Guide"

    def test_every_guide_on_disk_and_the_test_plan_are_indexed(self):
        """Count from disk, not a magic number — matches the sibling
        test_all_solutions_on_disk_are_indexed. The old version asserted a
        hardcoded 8 under the name "all_seven_guides", which had already
        drifted once (name said 7, assertion said 8) and would have needed a
        hand-edit for every new guide."""
        import glob
        on_disk = {os.path.relpath(p, idx.REPO_ROOT)
                   for p in glob.glob(os.path.join(idx.REPO_ROOT, "docs/guides/*.md"))}
        on_disk.add("docs/test-plan.md")
        index = idx.build_index()
        guides = [d for d in index["docs"] if d["type"] == "guide"]
        assert {d["path"] for d in guides} == on_disk, (
            f"indexed={sorted(d['path'] for d in guides)} disk={sorted(on_disk)}")
        paths = {d["path"] for d in guides}
        assert "docs/test-plan.md" in paths
        assert "docs/guides/cron-scripts-architecture.md" in paths

    def test_solution_adapter_maps_its_own_vocabulary(self):
        fm = {
            # Realistic post-parse input: parse_frontmatter() already strips
            # quotes, so the adapter receives an unquoted title.
            "title": "Generating an ATS-friendly resume PDF",
            "slug": "resume-pdf-pipeline",
            "category": "tooling",
            "tags": ["print-stylesheet", "ats"],
            "date_solved": "2026-04-29",
        }
        doc = idx.adapt_solution(fm, "# Heading\nbody\n",
                                 "docs/solutions/tooling/resume-pdf.md")
        assert doc["type"] == "solution"
        assert doc["status"] == "done"
        assert doc["project"] == "jameschang-co-eng"
        assert doc["section"] == "site-engineering"
        assert doc["title"] == "Solution — Generating an ATS-friendly resume PDF"
        assert doc["id"] == "SOL-resume-pdf-pipeline"
        assert doc["tags"] == ["tooling", "print-stylesheet", "ats"]

    def test_solution_falls_back_to_h1_when_title_missing(self):
        doc = idx.adapt_solution({}, "# Fallback Title\n",
                                 "docs/solutions/x/y.md")
        assert doc["title"] == "Solution — Fallback Title"

    def test_all_solutions_on_disk_are_indexed(self):
        # Count-from-disk, not a magic number: every docs/solutions/**/*.md must
        # be indexed. Self-updates as the KB grows, still catches a silent drop.
        import glob
        on_disk = {os.path.relpath(p, REPO_ROOT)
                   for p in glob.glob(
                       os.path.join(REPO_ROOT, "docs", "solutions", "**", "*.md"),
                       recursive=True)
                   if not os.path.basename(p).startswith("_")}
        index = idx.build_index()
        indexed = {d["path"] for d in index["docs"] if d["type"] == "solution"}
        assert indexed == on_disk, {
            "missing_from_index": sorted(on_disk - indexed),
            "indexed_but_not_on_disk": sorted(indexed - on_disk),
        }
        assert all(p.startswith("docs/solutions/") for p in indexed)

    def test_no_indexed_tag_contains_a_quote_character(self):
        index = idx.build_index()
        offenders = [(d["path"], t) for d in index["docs"] for t in d["tags"]
                     if '"' in t]
        assert not offenders, offenders

    def test_all_solutions_have_at_least_two_tags(self):
        # Every docs/solutions/**/*.md carries `category` plus a real `tags`
        # list (verified against the source frontmatter, not assumed) — so
        # the merged tag list on each indexed solution should be >= 2.
        index = idx.build_index()
        sols = [d for d in index["docs"] if d["type"] == "solution"]
        assert sols, "expected solution docs to be indexed"
        thin = [(d["path"], d["tags"]) for d in sols if len(d["tags"]) < 2]
        assert not thin, thin


class TestStageAndCockpit:
    def test_stage_is_captured(self):
        index = idx.build_index()
        staged = [d for d in index["docs"] if d.get("stage")]
        assert staged, "expected at least one stage-tagged PRD"
        assert {"mvp", "shipped", "planned"} & {d["stage"] for d in staged}

    def test_pm_review_cockpit_indexed(self):
        index = idx.build_index()
        pm = [d for d in index["docs"] if d["id"] == "DOC-PM-REVIEW"]
        assert pm, "the generated PM-review cockpit should be indexed"
        assert "portfolio cockpit" in pm[0]["html"].lower()


class TestProjectSlugCoherence:
    """The docs hub keys every doc to a project by slug, but nothing in the
    build pipeline validates that slug against `bin/projects-config.json` —
    `adapt_hub` passes `project` through verbatim.

    So a project rename that updates the config but misses the hub leaves
    docs filed under a slug that no longer exists. They don't error; they
    render under a phantom project on the /admin board and quietly detach
    from the real one. Renaming `spar` -> `tip` (2026-08-04) touched four
    separate places by hand — config, portfolio.json, the hub folder, and the
    hub frontmatter — and only these assertions would have caught a miss.
    """

    ALLOWED_NON_PROJECT = {"portfolio", idx.SITE_ENG_PROJECT}

    def _config_slugs(self):
        path = os.path.join(REPO_ROOT, "bin", "projects-config.json")
        return {p["slug"] for p in json.load(open(path, encoding="utf-8"))["projects"]}

    def test_indexed_docs_reference_a_real_project_slug(self):
        valid = self._config_slugs() | self.ALLOWED_NON_PROJECT
        orphans = [
            (d["path"], d["project"])
            for d in idx.build_index()["docs"]
            if d.get("project") and d["project"] not in valid
        ]
        assert not orphans, (
            "docs filed under a project slug absent from bin/projects-config.json "
            f"(rename drift): {orphans}"
        )

    def test_project_folders_are_real_project_slugs(self):
        """`admin/docs/projects/<slug>/` folder names are the hub's on-disk
        grouping. A stale folder survives a rename silently — the frontmatter
        can be correct while the directory still carries the old name."""
        base = os.path.join(REPO_ROOT, "admin", "docs", "projects")
        folders = {
            e for e in os.listdir(base)
            if os.path.isdir(os.path.join(base, e)) and not e.startswith("_")
        }
        stale = sorted(folders - self._config_slugs())
        assert not stale, (
            f"admin/docs/projects/ folders with no matching config slug: {stale}"
        )
