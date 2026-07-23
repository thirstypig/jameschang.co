#!/usr/bin/env python3
"""Sync project changelog + roadmap docs from source repos into the deep-dive
pages on jameschang.co.

Daily cron at 7:15 AM PT (14:15 UTC). Each entry in PROJECT_DOCS is a (slug,
doctype, adapter) tuple. An adapter is a callable `(token) → (parsed, error)`
that fetches + parses ONE project's source-of-truth, returning either a list
of canonical dicts or a None + error string. The script then renders the
canonical model to HTML and splices it between CHANGELOG/ROADMAP markers on
the destination page.

Adapter pattern lets us sync from heterogeneous sources without forcing every
project to author a single shared convention. Today's adapters:

  - parse_changelog       — heading-line markdown convention (## v X — date — tags)
  - parse_aleph_roadmap   — docs/plans/roadmap.md (### Module + **Workflow:** + percent table)
  - parse_jt_roadmap      — docs/PRODUCTION_ROADMAP.md (## PHASE N + task list, no percent)
  - parse_fl_roadmap      — client/src/pages/Roadmap.tsx (TypeScript data array extraction)

Canonical model — adapters MUST return one of these shapes:

  Changelog: [{version, date, tags: list[str], title: str, bullets: list[str]}, ...]
  Roadmap:   [{name, percent: int|None, description, workflow: list[str],
               features: list[(class, text)]}, ...]

Fail-safe: per-doc. Source missing / parse-empty → skip (no overwrite).
Markers missing in destination → error + heartbeat (if known). Other docs
sync normally. Whole script never crashes on a single source issue.

Heartbeat slugs:
  project-docs                      — aggregate, set on overall success
  project-docs:{slug}-{doctype}     — per-doc, set on per-doc failure / skip
"""

import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import _shared
from _shared import (
    content_changed,
    escape_html,
    record_heartbeat,
    REPO_ROOT,
    USER_AGENT,
)


# ---------------------------------------------------------------------------
# Heartbeat gating (bootstrap-aware)
# ---------------------------------------------------------------------------

def _known_feeds():
    """Return the set of feed slugs currently tracked in .feeds-heartbeat.json.

    Used to gate error-heartbeat writes: we only record an error for a feed
    that has previously succeeded at least once. This prevents the staleness
    monitor from opening false-positive issues during bootstrap — when the
    sync script ships but the source docs don't exist yet, the per-doc
    heartbeats stay absent (invisible to monitoring) until the first real
    success creates them.

    Reads via `_shared.HEARTBEAT_FILE` (not a local-imported copy) so tests
    can monkeypatch the path via `patch("_shared.HEARTBEAT_FILE", tmp_path)`
    without needing to also patch this module's namespace.
    """
    if not os.path.exists(_shared.HEARTBEAT_FILE):
        return set()
    try:
        with open(_shared.HEARTBEAT_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f).keys())
    except (json.JSONDecodeError, OSError):
        return set()


def record_error_if_known(feed_slug, error):
    """Record an error heartbeat ONLY if `feed_slug` is already tracked.

    See `_known_feeds()` for the rationale. Successful heartbeats are always
    recorded — they're how a feed becomes known in the first place.
    """
    if feed_slug in _known_feeds():
        record_heartbeat(feed_slug, error=error)


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_file(repo, path, token):
    """Fetch a raw file from GitHub's default branch. Returns string or None."""
    url = f"https://raw.githubusercontent.com/{repo}/HEAD/{path}"
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError) as e:
        print(f"  fetch failed for {repo}/{path}: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Inline markdown helpers (subset: **bold**, `code`)
# ---------------------------------------------------------------------------

_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_MD_CODE_RE = re.compile(r"`([^`]+)`")


def render_inline(text):
    """Escape HTML then render **bold** and `code` to <strong>/<code>.

    Mirrors update-projects.py's _render_markdown_inline so author-written
    angle brackets render as text, not as real tags."""
    out = escape_html(text)
    out = _MD_BOLD_RE.sub(r"<strong>\1</strong>", out)
    out = _MD_CODE_RE.sub(r"<code>\1</code>", out)
    return out


_BULLET_LINE_RE = re.compile(r"^[-*]\s+(.*)$")
_ORDERED_LINE_RE = re.compile(r"^\d+\.\s+(.*)$")
_TASK_LINE_RE = re.compile(r"^[-*]\s+\[(?P<state>[ x~])\]\s+(?P<text>.*)$")
_STATE_TO_CLASS = {"x": "done", " ": "planned", "~": "deferred"}


def _extract_bullets(body):
    """Extract `- foo` / `* foo` bullets. Continuation lines (indented 2+)
    are joined into the preceding bullet."""
    bullets = []
    for raw_line in body.split("\n"):
        line = raw_line.rstrip()
        if line.startswith("  ") and bullets:
            bullets[-1] += " " + line.strip()
            continue
        m = _BULLET_LINE_RE.match(line.lstrip())
        if m:
            bullets.append(m.group(1).strip())
    return bullets


def _extract_ordered_items(body):
    """Extract `1. foo`, `2. bar` ordered list items. Returns [str]."""
    items = []
    for line in body.split("\n"):
        m = _ORDERED_LINE_RE.match(line.strip())
        if m:
            items.append(m.group(1).strip())
    return items


def _extract_feature_items(body):
    """Extract `- [x] foo`, `- [ ] bar`, `- [~] baz`. Returns [(class, text)].
    Non-task-list bullets (plain `-` lines) are skipped — that's how the JT
    parser tolerates phases with mixed prose/task content."""
    items = []
    for line in body.split("\n"):
        m = _TASK_LINE_RE.match(line.strip())
        if m:
            state = m.group("state")
            css_class = _STATE_TO_CLASS.get(state, "planned")
            items.append((css_class, m.group("text").strip()))
    return items


_CSS_CLASS_SAFE_RE = re.compile(r"[^a-z0-9\-]+")


def _sanitize_class(s):
    """Lowercase + strip everything not [a-z0-9-]. Used for unknown tag classes."""
    return _CSS_CLASS_SAFE_RE.sub("", s.lower())


# ---------------------------------------------------------------------------
# Changelog parser (default heading-line convention)
# ---------------------------------------------------------------------------

# `## v0.12.0 — 2026-04-14 — security, improvement`
_CHANGELOG_H2_RE = re.compile(
    r"^##\s+(?P<version>\S+)\s+[—\-]+\s+"
    r"(?P<date>\d{4}-\d{2}-\d{2}[^\n—]*?)"
    r"(?:\s+[—\-]+\s+(?P<tags>[^\n]+))?\s*$",
    re.MULTILINE,
)
_CHANGELOG_TITLE_RE = re.compile(r"^###\s+(?P<title>[^\n]+)\s*$", re.MULTILINE)
_KNOWN_TAGS = {
    "feature", "improvement", "security", "fix", "breaking", "docs", "refactor",
}


def parse_changelog(markdown):
    """Parse changelog markdown into a list of release dicts.

    Each release: {version, date, tags: list[str], title: str, bullets: list[str]}.
    Returns [] if no releases found.
    """
    if not markdown:
        return []
    matches = list(_CHANGELOG_H2_RE.finditer(markdown))
    if not matches:
        return []
    releases = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        version = m.group("version").strip()
        date = m.group("date").strip()
        tags_raw = (m.group("tags") or "").strip()
        tags = [t.strip().lower() for t in tags_raw.split(",") if t.strip()]
        title_match = _CHANGELOG_TITLE_RE.search(body)
        if title_match:
            title = title_match.group("title").strip()
            body_after = body[title_match.end():].strip()
        else:
            title = ""
            body_after = body
        bullets = _extract_bullets(body_after)
        releases.append({
            "version": version,
            "date": date,
            "tags": tags,
            "title": title,
            "bullets": bullets,
        })
    return releases


def render_changelog(releases):
    """Render release dicts to <article class="release"> HTML blocks."""
    if not releases:
        return ""
    parts = []
    for rel in releases:
        version = escape_html(rel["version"])
        date = escape_html(rel["date"])
        title = render_inline(rel["title"])
        head_parts = [
            f'          <span class="release-version">{version}</span>',
            f'          <span class="release-date">{date}</span>',
        ]
        for tag in rel["tags"]:
            tag_class = tag if tag in _KNOWN_TAGS else _sanitize_class(tag)
            head_parts.append(
                f'          <span class="release-tag {tag_class}">{escape_html(tag)}</span>'
            )
        bullets_html = "\n".join(
            f"            <li>{render_inline(b)}</li>" for b in rel["bullets"]
        )
        body_html = (
            f'        <div class="release-body">\n'
            f'          <ul>\n'
            f'{bullets_html}\n'
            f'          </ul>\n'
            f'        </div>'
        )
        parts.append(
            f'      <article class="release">\n'
            f'        <div class="release-head">\n'
            + "\n".join(head_parts) + "\n"
            f'        </div>\n'
            f'        <h3 class="release-title">{title}</h3>\n'
            f'{body_html}\n'
            f'      </article>'
        )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Roadmap parsers — one per project + a default convention parser
# ---------------------------------------------------------------------------

# Convention parser: `## Module Name — NN%` H2 with optional ### Workflow / ### Features.
_ROADMAP_H2_RE = re.compile(
    r"^##\s+(?P<name>.+?)\s+[—\-]+\s+(?P<percent>\d{1,3})%\s*$",
    re.MULTILINE,
)
_ROADMAP_H3_RE = re.compile(r"^###\s+(?P<heading>[^\n]+?)\s*$", re.MULTILINE)


def parse_roadmap(markdown):
    """Default heading-line-convention roadmap parser.

    Each `## Module — NN%` becomes a module dict. Inside each: prose
    description, optional `### Workflow` (numbered list), optional
    `### Features` (task list).
    """
    if not markdown:
        return []
    matches = list(_ROADMAP_H2_RE.finditer(markdown))
    if not matches:
        return []
    modules = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[start:end].strip()
        modules.append(_parse_module_body(
            name=m.group("name").strip(),
            percent=int(m.group("percent")),
            body=body,
        ))
    return modules


def _parse_module_body(name, percent, body):
    """Shared shape: description (prose before any ### subsection),
    `### Workflow` ordered list, `### Features` task list."""
    description_lines = []
    workflow_items = []
    feature_items = []
    h3_matches = list(_ROADMAP_H3_RE.finditer(body))
    if h3_matches:
        description_lines = body[:h3_matches[0].start()].strip().split("\n")
        for j, h3 in enumerate(h3_matches):
            sec_start = h3.end()
            sec_end = h3_matches[j + 1].start() if j + 1 < len(h3_matches) else len(body)
            sec_body = body[sec_start:sec_end].strip()
            heading = h3.group("heading").lower()
            if heading.startswith("work"):
                workflow_items = _extract_ordered_items(sec_body)
            elif heading.startswith("feature"):
                feature_items = _extract_feature_items(sec_body)
    else:
        description_lines = body.split("\n")
    description = " ".join(l.strip() for l in description_lines if l.strip())
    return {
        "name": name,
        "percent": percent,
        "description": description,
        "workflow": workflow_items,
        "features": feature_items,
    }


# --- Aleph roadmap parser -------------------------------------------------
#
# Source: docs/plans/roadmap.md in thirstypig/alephco.io-app.
# Shape:
#   ## Project Health         ← markdown table mapping module → percent
#   ## Compliance Module Roadmaps
#     ### CPSIA / CPC         ← H3 (not H2) module heading
#     (prose description paragraph)
#     **Workflow:**           ← bold-text section marker (not H3)
#     1. **Step Name** — description
#     **Features:**
#     - [x] feature

# `| CPSIA / CPC | 100% |` — table row mapping module to percent.
# Tolerates leading `~` (Aleph uses ~70% for Platform's approximate progress).
_ALEPH_HEALTH_ROW_RE = re.compile(
    r"^\|\s*(?P<name>[^|]+?)\s*\|\s*~?(?P<percent>\d{1,3})%\s*\|", re.MULTILINE
)
_ALEPH_MODULE_RE = re.compile(r"^###\s+(?P<name>[^\n]+?)\s*$", re.MULTILINE)
_ALEPH_WORKFLOW_RE = re.compile(r"\*\*Workflow:\*\*", re.IGNORECASE)
_ALEPH_FEATURES_RE = re.compile(r"\*\*Features:\*\*", re.IGNORECASE)


def parse_aleph_roadmap(markdown):
    """Parse Aleph's `docs/plans/roadmap.md`.

    Module discovery is anchored to the "## Compliance Module Roadmaps" H2 so
    H3s elsewhere in the document (e.g. inside ## Project Health or a future
    ## Platform section) don't get misread as modules. Percent comes from the
    Project Health table at the top — modules without a row in the table get
    `percent=None` (renderer omits the badge).
    """
    if not markdown:
        return []
    percent_by_name = {
        m.group("name").strip(): int(m.group("percent"))
        for m in _ALEPH_HEALTH_ROW_RE.finditer(markdown)
    }
    # Bound module discovery to the body between "## Compliance Module Roadmaps"
    # and the next H2. Without the upper bound, downstream H2 sections (e.g.
    # "## Expansion Verticals" with ### regulatory categories) leak into the
    # module list and render as zero-percent modules — verified against the
    # live Aleph roadmap.md on 2026-05-28.
    start_anchor = "## Compliance Module Roadmaps"
    start_idx = markdown.find(start_anchor)
    if start_idx < 0:
        body_pool = markdown
    else:
        scan_start = start_idx + len(start_anchor)
        next_h2 = re.search(r"^##\s+", markdown[scan_start:], re.MULTILINE)
        body_pool = (
            markdown[scan_start:scan_start + next_h2.start()] if next_h2
            else markdown[scan_start:]
        )
    matches = list(_ALEPH_MODULE_RE.finditer(body_pool))
    if not matches:
        return []
    modules = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body_pool)
        body = body_pool[start:end].strip()
        name = m.group("name").strip()
        wf_match = _ALEPH_WORKFLOW_RE.search(body)
        feat_match = _ALEPH_FEATURES_RE.search(body)
        if wf_match:
            desc_block = body[:wf_match.start()]
        elif feat_match:
            desc_block = body[:feat_match.start()]
        else:
            desc_block = body
        description = " ".join(
            l.strip() for l in desc_block.split("\n") if l.strip()
        )
        workflow = []
        if wf_match:
            wf_end = feat_match.start() if feat_match else len(body)
            workflow = _extract_ordered_items(body[wf_match.end():wf_end])
        features = []
        if feat_match:
            features = _extract_feature_items(body[feat_match.end():])
        modules.append({
            "name": name,
            "percent": percent_by_name.get(name),
            "description": description,
            "workflow": workflow,
            "features": features,
        })
    return modules


# --- Judge Tool roadmap parser --------------------------------------------
#
# Source: docs/PRODUCTION_ROADMAP.md in thirstypig/thejudgetool.
# Shape:
#   ## PHASE N: Phase Name (parenthetical hints)
#   - [x] task done
#   - [ ] task planned
#   - [~] task deferred
#
# Some phases have ### subsections with prose + tables. _extract_feature_items
# only matches `- [x]/[ ]/[~]` lines, so non-task bullets are naturally skipped.

_JT_PHASE_RE = re.compile(
    r"^##\s+PHASE\s+\d+:\s+(?P<name>[^\n]+?)\s*$", re.MULTILINE
)


def parse_jt_roadmap(markdown):
    """Parse Judge Tool's `docs/PRODUCTION_ROADMAP.md`.

    Each `## PHASE N: Name` → one module. No percent (the JT roadmap doesn't
    have per-phase progress; renderer omits the badge). No workflow, no
    description. Features are all task-list items in the phase body, including
    those inside `### ` subsections.
    """
    if not markdown:
        return []
    matches = list(_JT_PHASE_RE.finditer(markdown))
    if not matches:
        return []
    modules = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[start:end]
        name = m.group("name").strip()
        modules.append({
            "name": name,
            "percent": None,
            "description": "",
            "workflow": [],
            "features": _extract_feature_items(body),
        })
    return modules


# --- Fantastic Leagues roadmap parser (TypeScript) ------------------------
#
# Source: client/src/pages/Roadmap.tsx in thirstypig/TheFantasticLeagues.
# Brittle by design — adapter to a TS data structure we don't own. If the file
# layout drifts (different identifier, different schema), the parser returns
# []. sync_one's fail-safe then skips rendering, preserving the existing page.
#
# Expected source schema:
#   const productRoadmap: RoadmapPhase[] = [
#     { id: "...", label: "...", timeframe: "...",
#       items: [
#         { title: "...", description: "...",
#           status: "done" | "planned" | "in-progress" },
#         ...
#       ] },
#     ...
#   ];

# FL uses three status values in source; we collapse "in-progress" into
# "planned" for now (the .module CSS only styles done/planned/deferred). If
# a fourth class gets added to projects.css, update this map.
_FL_STATUS_TO_CLASS = {
    "done": "done",
    "planned": "planned",
    "in-progress": "planned",  # lossy mapping — flag for re-visit
    "deferred": "deferred",
}


def parse_fl_roadmap(tsx_source):
    """Extract productRoadmap from a Roadmap.tsx file. Returns module dicts.

    Approach: locate the `const productRoadmap … = [ … ];` array via regex,
    then iterate top-level `{...}` blocks using a brace counter that tracks
    string state. Per phase, extract `label`, `timeframe`, and the `items`
    sub-array. Per item, extract `title` and `status`.
    """
    if not tsx_source:
        return []
    array_body = _slice_named_array(tsx_source, "productRoadmap")
    if array_body is None:
        return []
    modules = []
    for phase_block in _iter_top_level_objects(array_body):
        label = _ts_extract_string(phase_block, "label")
        if not label:
            continue
        timeframe = _ts_extract_string(phase_block, "timeframe") or ""
        items_body = _slice_named_array(phase_block, "items")
        features = []
        if items_body is not None:
            for item_block in _iter_top_level_objects(items_body):
                title = _ts_extract_string(item_block, "title")
                if not title:
                    continue
                status = _ts_extract_string(item_block, "status") or "planned"
                css_class = _FL_STATUS_TO_CLASS.get(status, "planned")
                features.append((css_class, title))
        modules.append({
            "name": label,
            "percent": None,
            "description": timeframe,
            "workflow": [],
            "features": features,
        })
    return modules


def _slice_named_array(src, name):
    """Find `name: [...]` or `name = [...]` and return the substring between
    the matching `[` and `]`. Returns None if not found or unbalanced.

    Handles TypeScript type annotations like `name: RoadmapPhase[] = [...]`
    by skipping over the empty `[]` in the type position. Detection rule:
    an empty bracket pair (`[` immediately followed by `]`) is a type
    annotation; anything else is a real array start."""
    pat = re.compile(rf"\b{re.escape(name)}\b")
    m = pat.search(src)
    if not m:
        return None
    i = m.end()
    while i < len(src):
        ch = src[i]
        if ch == "[":
            # Type annotation `[]` — skip and keep looking.
            if i + 1 < len(src) and src[i + 1] == "]":
                i += 2
                continue
            return _slice_balanced(src, i, open_ch="[", close_ch="]")
        if ch == ";":
            # Hit a statement terminator with no array assigned.
            return None
        i += 1
    return None


def _slice_balanced(src, start_idx, open_ch, close_ch):
    """Given `src[start_idx] == open_ch`, return the substring between
    `open_ch` and the matching `close_ch`. None if unbalanced. Tracks
    JS string literals (single, double, backtick) so quoted brackets
    don't throw off the count."""
    if src[start_idx] != open_ch:
        return None
    depth = 0
    in_str = None
    i = start_idx
    while i < len(src):
        ch = src[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in "\"'`":
            in_str = ch
            i += 1
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return src[start_idx + 1:i]
        i += 1
    return None


def _iter_top_level_objects(body):
    """Yield `{...}` substrings at depth 0 within `body`. Tracks JS strings
    so braces inside quoted text don't count."""
    depth = 0
    start = None
    in_str = None
    i = 0
    while i < len(body):
        ch = body[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in "\"'`":
            in_str = ch
            i += 1
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                yield body[start:i + 1]
                start = None
        i += 1


def _ts_extract_string(block, field):
    """Extract `field: "value"` from a TS object literal. Handles escaped
    quotes inside the value. Returns the unescaped string or None."""
    pattern = rf'\b{re.escape(field)}\s*:\s*"((?:\\.|[^"\\])*)"'
    m = re.search(pattern, block)
    if not m:
        return None
    # Unescape common sequences: \" → ", \\ → \, \n → newline
    raw = m.group(1)
    return (raw.replace(r"\"", '"')
               .replace(r"\\", "\\")
               .replace(r"\n", " ")
               .strip())


# ---------------------------------------------------------------------------
# Reader-facing copy layer
# ---------------------------------------------------------------------------
#
# Roadmap sources are written for engineers; these pages are read by everyone
# else. Two rules, both fail-closed, translate one into the other WITHOUT
# modifying the source repos:
#
#   Rule 1  public_phases  — which phases may be published at all
#   Rule 2  plain_english  — how each surviving line reads
#
# An item must clear both. Anything dropped is returned to the caller, which
# reports it via record_heartbeat(partial_success=True) so upstream drift shows
# up in .feeds-heartbeat.json instead of leaking raw engineering text onto the
# site. See docs/superpowers/specs/2026-07-21-non-technical-roadmap-copy-design.md

ROADMAP_COPY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "roadmap-copy.json")


def load_roadmap_copy():
    """Load bin/roadmap-copy.json. Missing or malformed file → {} (passthrough)."""
    try:
        with open(ROADMAP_COPY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def apply_public_copy(slug, modules, config=None):
    """Filter and translate parsed roadmap modules for a non-technical audience.

    Returns (modules, dropped) where `dropped` is a list of short strings
    describing what was removed. A project absent from the config passes
    through unchanged with no drops.
    """
    if config is None:
        config = load_roadmap_copy()
    rules = config.get(slug)
    if not rules:
        return modules, []

    dropped = []
    public_phases = rules.get("public_phases")

    kept = []
    for mod in modules:
        if public_phases is not None and mod["name"] not in public_phases:
            dropped.append(f"phase not allowlisted: {mod['name']}")
            continue

        copy_map = rules.get("plain_english")
        if copy_map is None:
            kept.append(mod)
            continue

        # Rule 1 matched the SOURCE name; Rule 2 now renames what survived.
        # Ordering matters — renaming must never affect filtering.
        if mod["name"] not in copy_map:
            dropped.append(f"module not translated: {mod['name']}")
            continue

        new_mod = dict(mod)
        new_mod["name"] = copy_map[mod["name"]]

        description = mod.get("description", "")
        if description and description not in copy_map:
            dropped.append(f"description not translated: {mod['name']}")
            new_mod["description"] = ""
        elif description:
            new_mod["description"] = copy_map[description]

        new_workflow = []
        for step in mod.get("workflow", []):
            if step in copy_map:
                new_workflow.append(copy_map[step])
            else:
                dropped.append(f"workflow step not translated: {step[:60]}")
        new_mod["workflow"] = new_workflow

        new_features = []
        for state, text in mod.get("features", []):
            if text in copy_map:
                new_features.append((state, copy_map[text]))
            else:
                dropped.append(f"feature not translated: {text[:60]}")
        new_mod["features"] = new_features

        kept.append(new_mod)
    return kept, dropped


# ---------------------------------------------------------------------------
# Renderer (shared across all roadmap adapters)
# ---------------------------------------------------------------------------

def render_roadmap(modules):
    """Render module dicts to <div class="module"> HTML blocks.

    Modules with `percent=None` get no `.module-progress` badge. Modules with
    empty `description` / `workflow` / `features` omit those subsections
    rather than emitting empty wrappers.
    """
    if not modules:
        return ""
    parts = []
    for mod in modules:
        name = render_inline(mod["name"])
        percent = mod.get("percent")
        description = render_inline(mod["description"])
        head_lines = [
            '      <div class="module">',
            '        <div class="module-head">',
            f'          <h3 class="module-name">{name}</h3>',
        ]
        if percent is not None:
            head_lines.append(
                f'          <span class="module-progress">Progress: {percent}%</span>'
            )
        head_lines.append('        </div>')
        module_parts = list(head_lines)
        if description:
            module_parts.append(f'        <p class="module-desc">{description}</p>')
        if mod["workflow"]:
            steps = "\n".join(
                f"            <li>{render_inline(s)}</li>" for s in mod["workflow"]
            )
            module_parts.append(
                '        <div class="module-workflow">\n'
                '          <strong>Workflow</strong>\n'
                '          <ol>\n'
                f'{steps}\n'
                '          </ol>\n'
                '        </div>'
            )
        if mod["features"]:
            items = "\n".join(
                f'          <li class="{cls}">{render_inline(text)}</li>'
                for cls, text in mod["features"]
            )
            module_parts.append(
                '        <ul class="feature-list">\n'
                f'{items}\n'
                '        </ul>'
            )
        module_parts.append('      </div>')
        parts.append("\n".join(module_parts))
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Adapter factory + PROJECT_DOCS
# ---------------------------------------------------------------------------

def make_adapter(repo, path, parser):
    """Return adapter(token) → (parsed, error_or_none).

    Closes over `repo`, `path`, and `parser`. `parser` is a single-arg
    function taking the fetched file text and returning either a list of
    canonical dicts or [] on empty/unparseable input.
    """
    def adapter(token):
        text = fetch_file(repo, path, token)
        if text is None:
            return None, f"source missing: {repo}/{path}"
        parsed = parser(text)
        if not parsed:
            return None, "empty or unparseable"
        return parsed, None
    return adapter


# Each tuple: (slug, doctype, adapter). Adapter is responsible for fetching
# AND parsing its source — sync_one only invokes it via `adapter(token)`.
PROJECT_DOCS = [
    ("aleph",             "changelog",
        make_adapter("thirstypig/alephco.io-app", "docs/changelog.md", parse_changelog)),
    ("aleph",             "roadmap",
        make_adapter("thirstypig/alephco.io-app", "docs/plans/roadmap.md", parse_aleph_roadmap)),
    ("fantastic-leagues", "changelog",
        make_adapter("thirstypig/TheFantasticLeagues", "docs/changelog.md", parse_changelog)),
    ("fantastic-leagues", "roadmap",
        make_adapter("thirstypig/TheFantasticLeagues",
                     "client/src/pages/Roadmap.tsx", parse_fl_roadmap)),
    ("judge-tool",        "changelog",
        make_adapter("thirstypig/thejudgetool", "docs/changelog.md", parse_changelog)),
    ("judge-tool",        "roadmap",
        make_adapter("thirstypig/thejudgetool",
                     "docs/PRODUCTION_ROADMAP.md", parse_jt_roadmap)),
]


def dest_path(slug, doctype):
    return os.path.join(REPO_ROOT, "projects", slug, doctype, "index.html")


# ---------------------------------------------------------------------------
# Splice + main loop
# ---------------------------------------------------------------------------

def replace_marker_in(content, marker, html, source_label):
    """Variant of _shared.replace_marker that names the source file in warnings
    and uses the destination's 6-space indent for the closing marker."""
    pattern = rf"(<!-- {marker}-START -->).*?(<!-- {marker}-END -->)"
    matches = re.findall(pattern, content, flags=re.DOTALL)
    if len(matches) == 0:
        print(f"  WARNING: {marker}-START / -END markers not found in {source_label}")
        return content, False
    if len(matches) > 1:
        print(f"  WARNING: {marker} markers found {len(matches)} times in {source_label}")
        return content, False
    replacement = f"<!-- {marker}-START -->\n{html}\n      <!-- {marker}-END -->"
    new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    return new_content, True


def _record_sync_heartbeat(feed_slug, dropped):
    """Clean success, or success-with-drops recorded as a non-fatal note.

    partial_success=True refreshes last_success_utc (so the 48h staleness
    monitor stays quiet — the page did render) while surfacing what was
    dropped in last_error, which lands in .feeds-heartbeat.json on every
    cron commit.
    """
    if not dropped:
        record_heartbeat(feed_slug)
        return
    sample = "; ".join(dropped[:3])
    record_heartbeat(feed_slug,
                     error=f"{len(dropped)} item(s) dropped: {sample}",
                     partial_success=True)


def sync_one(slug, doctype, adapter, token):
    """Sync one (slug, doctype) via its adapter. Returns 'ok'/'skipped'/'error'."""
    feed_slug = f"project-docs:{slug}-{doctype}"
    dest = dest_path(slug, doctype)
    print(f"  {slug}/{doctype}")

    parsed, error = adapter(token)
    if error:
        record_error_if_known(feed_slug, error)
        # `skipped` for missing source; `error` for parse failures with content.
        # In practice both paths flow through here — caller doesn't distinguish.
        print(f"    skipped ({error})")
        return "skipped"

    dropped = []
    if doctype == "changelog":
        rendered = render_changelog(parsed)
    elif doctype == "roadmap":
        parsed, dropped = apply_public_copy(slug, parsed)
        rendered = render_roadmap(parsed)
    else:
        record_error_if_known(feed_slug, f"unknown doctype: {doctype}")
        print(f"    error (unknown doctype: {doctype})")
        return "error"

    if not os.path.exists(dest):
        record_error_if_known(feed_slug, f"destination missing: {dest}")
        print(f"    error (destination page missing)")
        return "error"

    with open(dest, "r", encoding="utf-8") as f:
        old_content = f.read()
    marker = doctype.upper()
    new_content, replaced = replace_marker_in(old_content, marker, rendered, dest)
    if not replaced:
        record_error_if_known(feed_slug, f"{marker} markers missing in {dest}")
        return "error"

    if not content_changed(old_content, new_content):
        _record_sync_heartbeat(feed_slug, dropped)
        print(f"    no changes ({len(parsed)} entries)")
        return "ok"

    with open(dest, "w", encoding="utf-8") as f:
        f.write(new_content)
    _record_sync_heartbeat(feed_slug, dropped)
    print(f"    updated ({len(parsed)} entries)")
    return "ok"


def main():
    token = os.environ.get("TLDR_FETCH_TOKEN", "").strip() or None
    if not token:
        print("WARNING: TLDR_FETCH_TOKEN not set — private repos will 404.")
    statuses = {"ok": [], "skipped": [], "error": []}
    for slug, doctype, adapter in PROJECT_DOCS:
        try:
            status = sync_one(slug, doctype, adapter, token)
        except Exception as e:
            print(f"  unexpected error syncing {slug}/{doctype}: {e}", file=sys.stderr)
            record_error_if_known(f"project-docs:{slug}-{doctype}", str(e))
            status = "error"
        statuses[status].append(f"{slug}/{doctype}")

    # Aggregate heartbeat: only records errors for an already-known feed.
    # Successful aggregate runs always record (so the 'project-docs' slug
    # becomes visible to monitoring after first success).
    if statuses["error"]:
        record_error_if_known(
            "project-docs",
            f"errors: {', '.join(statuses['error'])}",
        )
    elif statuses["skipped"] and not statuses["ok"]:
        record_error_if_known(
            "project-docs",
            f"all docs skipped: {', '.join(statuses['skipped'])}",
        )
    else:
        record_heartbeat("project-docs")

    print(
        f"Done. ok={len(statuses['ok'])} "
        f"skipped={len(statuses['skipped'])} "
        f"errors={len(statuses['error'])}."
    )


if __name__ == "__main__":
    main()
