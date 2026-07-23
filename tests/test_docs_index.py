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
        paths = list(idx.iter_doc_files())
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
        blob = open(path, encoding="utf-8").read().lower()
        for bad in ["client_secret", "private_key", "api_key", "password", "-----begin"]:
            assert bad not in blob, f"index.json contains sensitive marker: {bad!r}"
