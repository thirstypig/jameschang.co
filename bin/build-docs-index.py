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
import collections
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
    ("site-engineering", "Site engineering",
     "how this site is built — guides & solved problems"),
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
    "guide": "site-engineering", "solution": "site-engineering",
    "glossary": "foundations", "intake-rules": "foundations",
    "note": "notes",
}
# Exceptions by path substring → section key (empty today; the hook exists).
PATH_OVERRIDES = {}

_FENCE = re.compile(r"```.*?```", re.DOTALL)
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_FM_LINE = re.compile(r"^(\w+):\s*(.*)$")

# A secret VALUE looks like `name = <16+ opaque chars>`. A bare mention of an
# env-var NAME is public-safe — those names are already public in this repo
# (see the /admin/ binding rule in CLAUDE.md).
#
# The keyword list is BARE STEMS ONLY (secret, token, key, password,
# passphrase, credential) — not compounds like client_secret/secret_key/
# api_key. Every compound tried across three prior review rounds is subsumed
# by one of these stems, so enumerating compounds was pure redundancy — and
# redundant enumeration is exactly what let three different bare keywords
# (token, then key, then secret) slip through undetected across those three
# rounds. Matching on stems instead of the compounds built from them closes
# the whole class at once: any identifier containing one of these stems
# anywhere (PLEX_TOKEN, WHOOP_TOKEN_KEY, APP_SECRET, SIGNING_KEY,
# DB_PASSWORD, API_CREDENTIAL, client_secret, api_key, ...) is caught. PEM
# headers are always a value regardless of the assigned name.
_SECRET_KEYWORD = (
    r"[a-z0-9_]*(?:secret|token|key|password|passphrase|credential)[a-z0-9_]*"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(" + _SECRET_KEYWORD + r")[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_\-./+]{16,})",
    re.IGNORECASE,
)
# Some secrets are whole URLs (e.g. a Google Calendar "secret address in iCal
# format") rather than opaque tokens — the secrecy is the full path, not one
# assigned value.
_SECRET_URL = re.compile(
    r"[a-z0-9_]*(?:ical_url|webhook_url|_uri)[a-z0-9_]*"
    r"[\"']?\s*[:=]\s*[\"']?(https?://\S{20,})",
    re.IGNORECASE,
)
# GitHub PAT prefixes are self-identifying as secret-shaped regardless of the
# variable name they're assigned to.
_GITHUB_PAT = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,})")
_PEM_HEADER = re.compile(r"-----BEGIN [A-Z ]*(PRIVATE KEY|CERTIFICATE)-----")
# A matched assignment value that's plainly a filename/path (e.g.
# `TOKEN_ENC = ".whoop-token.enc"`) is documentation, not a leak — these
# extensions never appear inside a real secret value.
_FILENAME_LIKE_VALUE = re.compile(
    r"\.(?:enc|json|md|py|js|ics|txt|ya?ml|sh)$", re.IGNORECASE
)
# A value made of lowercase-alpha words joined by - or _, with at least one
# separator and NO digits, is a slug/identifier (section keys, project slugs,
# doc filenames), not a secret. Real secrets carry digits or mixed case. BUT
# a diceware-style passphrase (e.g. WHOOP_TOKEN_KEY=correct-horse-battery-
# staple, an AES passphrase in this repo) is exactly this shape too, so this
# exemption must never apply just because the value looks slug-like — it
# must also require the matched KEYWORD to be a bare stem ("key", "secret",
# ...) with no prefix/suffix, i.e. a structural JSON/YAML field name like
# `"key": "site-engineering"`. A compound name like APP_SECRET or
# WHOOP_TOKEN_KEY is a real secret identifier and must never be exempt, no
# matter how slug-like its value looks.
_SLUG_LIKE_VALUE = re.compile(r"^[a-z]+(?:[-_][a-z]+)+$")
_BARE_STEM_KEYWORD = re.compile(
    r"^(?:secret|token|key|password|passphrase|credential)$", re.IGNORECASE
)


def find_secret_values(text):
    """Return a list of substrings that look like leaked secret VALUES.

    Empty list means the text is publishable. Used by the guard test against
    the committed index.json.
    """
    hits = [
        m.group(0)
        for m in _SECRET_ASSIGNMENT.finditer(text)
        if not _FILENAME_LIKE_VALUE.search(m.group(2))
        and not (
            _BARE_STEM_KEYWORD.match(m.group(1))
            and _SLUG_LIKE_VALUE.match(m.group(2))
        )
    ]
    hits += [m.group(0) for m in _SECRET_URL.finditer(text)]
    hits += [m.group(0) for m in _GITHUB_PAT.finditer(text)]
    hits += [m.group(0) for m in _PEM_HEADER.finditer(text)]
    return hits


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

Root = collections.namedtuple("Root", "path adapter recurse")


def iter_root_files(root):
    """Yield absolute paths of indexable .md files under one root.

    A root may be a single file or a directory. A missing root logs and yields
    nothing — a rename must never break the build for every other doc.
    """
    abs_root = os.path.join(REPO_ROOT, root.path)
    if os.path.isfile(abs_root):
        yield abs_root
        return
    if not os.path.isdir(abs_root):
        print(f"  ! root missing, skipped: {root.path}")
        return
    if not root.recurse:
        for fn in sorted(os.listdir(abs_root)):
            full = os.path.join(abs_root, fn)
            if fn.endswith(".md") and not fn.startswith("_") and os.path.isfile(full):
                yield full
        return
    for dirpath, dirnames, files in os.walk(abs_root):
        dirnames[:] = sorted(d for d in dirnames if d != "_templates")
        for fn in sorted(files):
            if not fn.endswith(".md") or fn.startswith("_"):
                continue
            yield os.path.join(dirpath, fn)


def _doc(rel, body, *, doc_id, doc_type, status, project, title, tags, stage=""):
    """Assemble one index entry. `rel` is repo-relative."""
    return {
        "id": doc_id,
        "type": doc_type,
        "status": status,
        "stage": stage,
        "project": project,
        "tags": tags,
        "title": title,
        "path": rel,
        "section": section_for(doc_type, rel),
        "html": md_to_html(body),
    }


def adapt_hub(fm, body, rel):
    """admin/docs/** — already hub schema. No `type` means not an authored doc."""
    if not fm.get("type"):
        return None
    tags = fm.get("tags", [])
    return _doc(
        rel, body,
        doc_id=fm.get("id", ""),
        doc_type=fm.get("type", ""),
        status=fm.get("status", ""),
        stage=fm.get("stage", ""),
        project=fm.get("project", ""),
        title=extract_title(body, rel),
        tags=tags if isinstance(tags, list) else [],
    )


SITE_ENG_PROJECT = "jameschang-co-eng"


def _slug_id(prefix, rel):
    """Slug-based ID for adapter-synthesized docs (never hand-assigned)."""
    base = os.path.splitext(os.path.basename(rel))[0]
    return f"{prefix}-{base}"


def adapt_guide(fm, body, rel):
    """docs/guides/** + docs/test-plan.md — no frontmatter at all."""
    return _doc(
        rel, body,
        doc_id=_slug_id("GUIDE", rel),
        doc_type="guide",
        status="active",
        project=SITE_ENG_PROJECT,
        title="Guide — " + extract_title(body, rel),
        tags=[],
    )


def adapt_solution(fm, body, rel):
    """docs/solutions/** — its own frontmatter vocabulary, translated here.

    Source schema: title, slug, category, tags, severity, component, symptom,
    root_cause, date_solved. That schema is load-bearing for /ce:compound and
    the learnings-researcher agent, so it is read, never rewritten.
    """
    title = (fm.get("title") or "").strip().strip('"').strip()
    if not title:
        title = extract_title(body, rel)
    tags = fm.get("tags", [])
    tags = list(tags) if isinstance(tags, list) else []
    category = fm.get("category", "")
    if category and category not in tags:
        tags = [category] + tags
    return _doc(
        rel, body,
        doc_id=_slug_id("SOL", fm.get("slug") or rel),
        doc_type="solution",
        status="done",
        project=SITE_ENG_PROJECT,
        title="Solution — " + title,
        tags=tags,
    )


# Hardcoded allowlist. NEVER glob docs/** — docs/superpowers/ holds gitignored
# local design specs and index.json is committed and public.
ROOTS = [
    Root("admin/docs", adapt_hub, True),
    Root("docs/guides", adapt_guide, False),
    Root("docs/solutions", adapt_solution, True),
    Root("docs/test-plan.md", adapt_guide, False),
]


def build_index():
    docs = []
    for root in ROOTS:
        count = 0
        for path in iter_root_files(root):
            rel = os.path.relpath(path, REPO_ROOT)
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                fm, body = parse_frontmatter(content)
                doc = root.adapter(fm, body, rel)
            except Exception as exc:  # one bad file must not kill the build
                print(f"  ! skipped {rel}: {exc.__class__.__name__}")
                continue
            if doc is None:
                continue
            docs.append(doc)
            count += 1
        print(f"  {root.path}: {count} doc(s)")
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
