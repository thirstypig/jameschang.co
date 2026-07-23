#!/usr/bin/env python3
"""Build the docs-board manifest: admin/docs/index.json.

Walks admin/docs/, and for each authored doc parses its frontmatter, extracts a
title (first H1, guarded against code-fence false positives), renders the markdown
body to HTML, and assigns it a board SECTION by type. The viewer
(admin/docs-viewer.js) reads this manifest — it never touches filenames or walks the
tree (impossible on a static host).

Run standalone, or via `python3 bin/refresh-docs.py` (which calls this last).
Python 3 stdlib only.
"""
import html as _html
import json
import os
import re
from datetime import datetime, timezone

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
HUB = os.path.join(REPO_ROOT, "admin", "docs")
INDEX = os.path.join(HUB, "index.json")

# Board sections, in display order (most-referenced first, foundations near bottom).
SECTIONS = [
    ("product", "Product", "what & why — specs, roadmap, intake"),
    ("engineering", "Engineering", "how it's built — decisions, APIs, tests"),
    ("operations", "Operations", "under the hood — stats, costs, changelog, runbook"),
    ("security", "Security & risk", "risks, privacy, open questions"),
    ("foundations", "Foundations", "glossary, rules, conventions"),
    ("notes", "Notes", "scratchpad & inbox"),
]
TYPE_SECTION = {
    "prd": "product", "roadmap": "product", "todos": "product", "launch-spec": "product",
    "adr": "engineering", "tech-spec": "engineering", "api-docs": "engineering",
    "decision-log": "engineering", "testing": "engineering", "component-lib": "engineering",
    "stats": "operations", "costs": "operations", "status": "operations",
    "changelog": "operations", "runbook": "operations", "experiment": "operations",
    "risk": "security", "privacy": "security",
    "glossary": "foundations", "intake-rules": "foundations",
    "note": "notes",
}
# Exceptions by path substring → section key (empty today; the hook exists).
PATH_OVERRIDES = {}

_FENCE = re.compile(r"```.*?```", re.DOTALL)
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_FM_LINE = re.compile(r"^(\w+):\s*(.*)$")


def section_for(doc_type, rel_path):
    for needle, key in PATH_OVERRIDES.items():
        if needle in rel_path:
            return key
    return TYPE_SECTION.get(doc_type, "notes")


def parse_frontmatter(content):
    """Return (frontmatter_dict, body). Empty dict if no frontmatter block."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content
    block = content[3:end]
    body = content[end + 4:]
    fm = {}
    for line in block.splitlines():
        m = _FM_LINE.match(line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            val = [x.strip() for x in val[1:-1].split(",") if x.strip()]
        fm[key] = val
    return fm, body


def tidy_filename(rel_path):
    base = os.path.splitext(os.path.basename(rel_path))[0]
    base = re.sub(r"^(PRD|ADR|DOC|RISK|EXP)-\d+-", "", base)
    return base.replace("-", " ").replace("_", " ").strip().title()


def extract_title(body, rel_path):
    """First '# H1' as title — but strip fenced code first, so a '# comment' inside
    a bash block never wins. Fall back to a tidy filename."""
    stripped = _FENCE.sub("", body)
    m = _H1.search(stripped)
    if m:
        return m.group(1).strip()
    return tidy_filename(rel_path)


# ── markdown → HTML (focused: the constructs these docs actually use) ──────

def _esc(s):
    return _html.escape(s, quote=False)


def _inline(text):
    """Inline formatting on already-escaped text. Code spans are protected first."""
    spans = []

    def stash(m):
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)

    def _link(m):
        label, href = m.group(1), m.group(2).strip()
        # Block dangerous URL schemes even in our own docs (defense in depth).
        if re.match(r"^\s*(javascript|data|vbscript):", href, re.IGNORECASE):
            href = "#"
        return (f'<a href="{_html.escape(href, quote=True)}" '
                f'rel="noopener">{label}</a>')

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link, text)

    def unstash(m):
        return "<code>" + spans[int(m.group(1))] + "</code>"

    return re.sub(r"\x00(\d+)\x00", unstash, text)


def _is_table_sep(line):
    return re.match(r"^\s*\|[\s:|-]+\|\s*$", line) is not None


def _cells(row):
    row = row.strip().strip("|")
    return [c.strip() for c in row.split("|")]


def md_to_html(md):
    md = re.sub(r"<!--.*?-->", "", md, flags=re.DOTALL)  # drop HTML comments
    lines = md.split("\n")
    out = []
    i, n = 0, len(lines)
    para = []

    def flush_para():
        if para:
            out.append("<p>" + _inline(_esc(" ".join(para)).strip()) + "</p>")
            para.clear()

    while i < n:
        line = lines[i]
        s = line.strip()

        if s.startswith("```"):
            flush_para()
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + _esc("\n".join(buf)) + "</code></pre>")
            continue

        if not s:
            flush_para()
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.+?)\s*$", s)
        if m:
            flush_para()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{_inline(_esc(m.group(2)))}</h{lvl}>")
            i += 1
            continue

        if s in ("---", "***", "___"):
            flush_para()
            out.append("<hr>")
            i += 1
            continue

        if s.startswith("|") and i + 1 < n and _is_table_sep(lines[i + 1]):
            flush_para()
            header = _cells(lines[i])
            i += 2
            body_rows = []
            while i < n and lines[i].strip().startswith("|"):
                body_rows.append(_cells(lines[i]))
                i += 1
            thead = "".join(f"<th>{_inline(_esc(c))}</th>" for c in header)
            trs = []
            for r in body_rows:
                tds = "".join(f"<td>{_inline(_esc(c))}</td>" for c in r)
                trs.append(f"<tr>{tds}</tr>")
            out.append(f"<table><thead><tr>{thead}</tr></thead>"
                       f"<tbody>{''.join(trs)}</tbody></table>")
            continue

        if re.match(r"^[-*]\s+", s):
            flush_para()
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]).rstrip())
                i += 1
            lis = "".join(f"<li>{_inline(_esc(it))}</li>" for it in items)
            out.append(f"<ul>{lis}</ul>")
            continue

        if s.startswith(">"):
            flush_para()
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>" + _inline(_esc(" ".join(quote))) + "</blockquote>")
            continue

        para.append(s)
        i += 1

    flush_para()
    return "\n".join(out)


# ── walk + build ──────────────────────────────────────────────────────────

def iter_doc_files():
    for root, dirs, files in os.walk(HUB):
        dirs[:] = [d for d in dirs if d != "_templates"]
        for fn in sorted(files):
            if not fn.endswith(".md") or fn.startswith("_"):
                continue
            yield os.path.join(root, fn)


def build_index():
    docs = []
    for path in iter_doc_files():
        rel = os.path.relpath(path, HUB)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        fm, body = parse_frontmatter(content)
        if not fm.get("type"):
            continue  # not an indexable authored doc
        docs.append({
            "id": fm.get("id", ""),
            "type": fm.get("type", ""),
            "status": fm.get("status", ""),
            "project": fm.get("project", ""),
            "tags": fm.get("tags", []) if isinstance(fm.get("tags"), list) else [],
            "title": extract_title(body, rel),
            "path": rel,
            "section": section_for(fm.get("type", ""), rel),
            "html": md_to_html(body),
        })
    docs.sort(key=lambda d: (d["project"], d["title"].lower()))
    present = {d["section"] for d in docs}
    sections = [{"key": k, "label": lbl, "blurb": bl2}
                for (k, lbl, bl2) in SECTIONS if k in present]
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sections": sections,
        "docs": docs,
    }


def main():
    index = build_index()
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Docs index built: {len(index['docs'])} docs, "
          f"{len(index['sections'])} sections → "
          f"{os.path.relpath(INDEX, REPO_ROOT)}")


if __name__ == "__main__":
    main()
