---
title: "Per-project adapters beat a single convention when source-of-truth lives in N different shapes"
category: integration-issues
tags: [sync-pipeline, adapter-pattern, content-mirror, cross-repo, bootstrap-monitoring, brace-counting, github-contents-api]
symptom: "designing a single markdown convention for content sync produces dual-maintenance friction when each source repo already maintains canonical content in its own native shape (plain markdown, custom markdown, in-app TypeScript)"
root_cause: "treating heterogeneous source repos as a homogeneous fleet — a 'one convention to rule them all' design forces authors to dual-maintain their canonical content (in-app data, custom markdown) alongside a synced markdown twin. Cost: every edit lives in two places forever, and they drift"
module: project-doc-sync-pipeline
date_solved: 2026-05-29
severity: medium
---

# Per-project adapters for heterogeneous source-of-truth

## The problem

The /projects/ deep-dive pages on jameschang.co had stale changelog and roadmap content — last hand-updated 2026-04-15, ~6 weeks behind the live data inside each product. The ask: build a daily sync that fetches changelog + roadmap from each source repo, similar to how `/now` syncs project TLDRs from each repo's CLAUDE.md.

The instinct was the obvious one: design a single shared markdown convention (`docs/changelog.md` + `docs/roadmap.md` with a heading-line grammar), have authors write to that convention in each source repo, then a single parser + renderer fans out to the destination pages. Clean, symmetrical, scales.

That design got built — and then the second-look investigation revealed the assumption underneath it was false:

- **Aleph** maintains roadmap content at `docs/plans/roadmap.md`, but uses `###` for modules (not `##`), bold-text section markers (`**Workflow:**` / `**Features:**`) instead of `### Workflow` / `### Features`, and stores progress percentages in a `## Project Health` table at the top of the file. Close to the convention, but not it.
- **Judge Tool** maintains roadmap content at `docs/PRODUCTION_ROADMAP.md`, organized as `## PHASE N: Name` sections with task-list bodies. No per-phase percent. Some phases have prose-and-tables inside H3 subsections that aren't task-list-shaped.
- **The Fantastic Leagues** has no roadmap markdown file. The roadmap is a hardcoded TypeScript data structure (`productRoadmap: RoadmapPhase[]`) inside `client/src/pages/Roadmap.tsx`, rendered live in-app at `app.thefantasticleagues.com/roadmap`.
- **All 3 changelogs** live in-app (admin-only pages or React components), with NO markdown source.

If we forced the single-convention design, James would have to dual-maintain a `docs/roadmap.md` alongside whatever the canonical source already is. Every product edit would need a parallel edit in the synced file, forever. They would drift — that's not "if", it's "when".

## The shape of the right answer

Drop the "one convention" idea. Each project gets its own adapter that knows how to read its native source format. The adapter is a small callable `(token) → (parsed, error_or_none)` that owns the fetch + parse for ONE source. The renderer and the destination markers stay shared — adapters all return the same canonical internal model.

```python
# bin/update-project-docs.py

def make_adapter(repo, path, parser):
    """Adapter closure: fetch path from repo, parse, return canonical dicts."""
    def adapter(token):
        text = fetch_file(repo, path, token)
        if text is None:
            return None, f"source missing: {repo}/{path}"
        parsed = parser(text)
        if not parsed:
            return None, "empty or unparseable"
        return parsed, None
    return adapter


PROJECT_DOCS = [
    ("aleph",             "changelog", make_adapter("thirstypig/alephco.io-app",
                                                    "docs/changelog.md", parse_changelog)),
    ("aleph",             "roadmap",   make_adapter("thirstypig/alephco.io-app",
                                                    "docs/plans/roadmap.md", parse_aleph_roadmap)),
    ("fantastic-leagues", "roadmap",   make_adapter("thirstypig/TheFantasticLeagues",
                                                    "client/src/pages/Roadmap.tsx", parse_fl_roadmap)),
    ("judge-tool",        "roadmap",   make_adapter("thirstypig/thejudgetool",
                                                    "docs/PRODUCTION_ROADMAP.md", parse_jt_roadmap)),
    # ... etc
]
```

The canonical internal model is the contract between adapters and renderer:

```
Roadmap:   list[{name, percent: int|None, description, workflow: list[str],
                  features: list[(class, text)]}]
Changelog: list[{version, date, tags: list[str], title: str, bullets: list[str]}]
```

Per-project complexity is bounded to the parser. Adding a new project means one new parser function and one new line in `PROJECT_DOCS`. The renderer, marker-splice logic, fail-safe error handling, and heartbeat tracking stay shared — change them once, every project benefits.

## When this pattern applies

Use adapter-per-source whenever the upstream source-of-truth answers "yes" to any of these:

- The source already exists in a project-specific shape AND authors actively maintain it there.
- The shape is unlikely to converge to a shared convention any time soon (different teams, different stacks, different audiences).
- Forcing convergence would require dual-maintenance (parallel files saying the same thing).
- The number of sources is small enough that per-source parsers don't compound into maintenance hell (rule of thumb: under ~10; this site has 3-4 today, ceiling around 8 before the JSON-export alternative starts to win).

Use a shared convention instead when:

- The source repos are greenfield or willing to author against a contract.
- The number of sources will grow large (10+).
- The content shape is genuinely uniform across sources (e.g., all repos use Conventional Commits — convention is natural).

The break-even is at the point where per-source adapter maintenance starts exceeding the dual-maintenance cost of a convention. For 3 sources in a portfolio site, adapters win cleanly.

## Three technical sub-patterns the build surfaced

### 1. Bootstrap-aware heartbeat gating

The sync wires per-doc heartbeats into the existing staleness monitor (`bin/check-feed-health.py`), which opens a GitHub issue if a feed has no `last_success_utc` within 48 hours. Naive implementation: record an error heartbeat whenever a fetch fails. The bug: on day 1 the source files don't exist yet, so the first cron run records error heartbeats for every feed. With no prior success, `feed_age_hours()` returns `infinity` → staleness monitor opens 4 false-positive GitHub issues immediately.

The fix is a one-line rule:

```python
def record_error_if_known(feed_slug, error):
    """Record an error heartbeat ONLY if `feed_slug` already exists in the
    heartbeat file. New feeds (never succeeded) stay invisible to monitoring
    until their first success creates them."""
    if feed_slug in _known_feeds():
        record_heartbeat(feed_slug, error=error)
```

Successful runs always record (via `record_heartbeat` directly). Errors only record once the feed has graduated to "known" by succeeding at least once. The day-1 noise disappears.

This is the analog of "don't alert on a service that's never started" in operational monitoring — same shape, different domain.

### 2. Brace counting with string-state tracking for TypeScript extraction

Parsing FL's `productRoadmap: RoadmapPhase[]` TypeScript data structure without a TypeScript parser sounds brittle. It is, but only along one axis: the SHAPE of the data structure (field names, nesting). The actual character-level scanning is robust if you track string state.

```python
def _slice_balanced(src, start_idx, open_ch, close_ch):
    """Given src[start_idx] == open_ch, return the substring between it and
    the matching close_ch. Tracks single, double, and backtick string literals
    plus backslash escapes so braces inside quoted text don't count."""
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
```

That ~20 lines handles every realistic case: nested object braces, brackets inside strings, escaped quotes, backtick template literals. The brittleness lives in `_extract_string_field(block, "label")` — if upstream renames `label` to `name`, the parser silently returns nothing. That's the right brittleness budget: the parser fails the soft way (returns empty → fail-safe skips → existing page preserved), not the hard way (crash → silent freeze).

One subtlety the FL parser surfaced: `const productRoadmap: RoadmapPhase[] = [` contains a `[]` from the TypeScript type annotation BEFORE the real array `[`. The regex needs to skip empty-bracket pairs:

```python
while i < len(src):
    if src[i] == "[":
        # Type annotation `[]` (empty brackets) — skip past and keep looking.
        if i + 1 < len(src) and src[i + 1] == "]":
            i += 2
            continue
        return _slice_balanced(src, i, open_ch="[", close_ch="]")
    if src[i] == ";":
        return None
    i += 1
```

### 3. Anchored AND bounded section parsing

The Aleph adapter parses modules from inside the `## Compliance Module Roadmaps` H2 section. The naive implementation anchors on that H2 and parses ALL subsequent H3s as modules. The bug: the markdown file has further H2 sections after Compliance (`## Platform Features`, `## Expansion Verticals`, `## Implementation Phases`, `## Infrastructure Status`), and "Expansion Verticals" has 6 H3s for future regulatory categories. Those got parsed as zero-percent modules and showed up on the rendered page.

The fix is to anchor AND bound:

```python
start_anchor = "## Compliance Module Roadmaps"
start_idx = markdown.find(start_anchor)
if start_idx < 0:
    body_pool = markdown
else:
    scan_start = start_idx + len(start_anchor)
    # Bound at the next H2 — without this, downstream H2 sections leak in.
    next_h2 = re.search(r"^##\s+", markdown[scan_start:], re.MULTILINE)
    body_pool = (
        markdown[scan_start:scan_start + next_h2.start()] if next_h2
        else markdown[scan_start:]
    )
matches = list(_ALEPH_MODULE_RE.finditer(body_pool))
```

Whenever you scope a parser to a section of a multi-section document, you need BOTH an anchor (where to start) AND a bound (where to stop). Missing either one means content leaks. Pin the bound with a test against a fixture that explicitly contains downstream sections — otherwise a future addition of a new `##` section to the source silently regresses the parser.

## Prevention

For the next time this comes up — building a sync between heterogeneous source repos and a portfolio / dashboard site:

1. **Inventory the sources BEFORE designing the convention.** Open each source repo. Look at what canonical content already exists, where it lives, and what shape it's in. The cost of looking is 10 minutes. The cost of designing the wrong convention is days of refactor + a thrown-out spec.
2. **Default to adapters when N is small (under ~8).** Convention-based designs win at large N (zero per-source code, one shared parser). At small N, the per-source maintenance is cheaper than the dual-maintenance cost of forcing a shared shape onto authors who already have their canonical version somewhere else.
3. **Keep the canonical internal model stable.** Adapters can change parsers freely; the renderer and downstream code only care about the canonical dict shape. Pin the contract with tests on the adapter output (not just the rendered HTML).
4. **Fail-safe on every adapter return path.** Source missing → skip. Parse empty → skip. Markers missing in destination → error + heartbeat (if known). NEVER overwrite a destination page with empty content — that's how a transient upstream outage turns into a permanently-blank deep-dive page.
5. **For brittle parsers (Tsx extraction, custom markdown), invest in unit-test fixtures pinned to real edge cases.** The FL parser had explicit fixture tests for nested braces in descriptions and the TypeScript `[]` type annotation specifically because both broke during development.
6. **Bound the heartbeat surface to "known feeds."** Any monitoring system that pages on missing `last_success_utc` will produce false positives during bootstrap unless the writer gates errors to feeds that have succeeded once. Make this rule explicit and tested, not an afterthought.

## Related

- [marker-boundary-content-staleness](marker-boundary-content-staleness.md) — content outside the contract surface freezes silently. Adapter destinations must use markers; surrounding chrome stays hand-edited; both invariants need explicit tests.
- [cross-repo-admin-via-github-contents-api](cross-repo-admin-via-github-contents-api.md) — the same `TLDR_FETCH_TOKEN` PAT pattern is reused here. Fine-grained PATs with `Contents:Read` scope on each source repo.
- [relative-time-html-defeats-content-changed-cache](relative-time-html-defeats-content-changed-cache.md) — `content_changed()` strips time-volatile substrings to avoid spurious commits. Project doc sync inherits this — the renderer outputs no `Auto-updated` timestamps inside markers, so no special-case handling needed.

## Implementation reference

- Adapter architecture + parsers: `bin/update-project-docs.py` (commit `32085ba`, 2026-05-29)
- Tests: `tests/test_project_docs.py` (63 tests, including the brace-counter edge cases and the Aleph bounded-section invariant)
- Workflow: `.github/workflows/project-docs-sync.yml` (13:15 UTC daily, offset 15 min from `projects-sync.yml` at 13:00 UTC to avoid concurrency races)
- Documented in CLAUDE.md → "Project doc sync (changelog + roadmap)"
