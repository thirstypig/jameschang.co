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
        path = os.path.join(REPO_ROOT, "admin", "docs", "index.json")
        if not os.path.exists(path):
            return
        blob = open(path, encoding="utf-8").read()
        leaks = idx.find_secret_values(blob)
        assert not leaks, f"index.json contains secret value(s): {leaks[:3]}"

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
]

MUST_PASS = [
    ("prose naming vars in backticks, no assignment",
     "Required secrets: `PLEX_TOKEN`, `GCAL_ICAL_URL`, `WHOOP_CLIENT_SECRET`. "
     "See the setup guide for details."),
    ("filename constant, not a secret value",
     'TOKEN_ENC = ".whoop-token.enc"'),
    ("public OAuth endpoint URL, not a secret",
     'TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"'),
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

    def test_index_is_idempotent(self):
        a = idx.build_index()
        b = idx.build_index()
        a.pop("generated"), b.pop("generated")
        assert a == b, "two consecutive builds must agree"


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
