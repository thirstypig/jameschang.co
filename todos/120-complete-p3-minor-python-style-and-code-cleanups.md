---
status: complete
priority: p3
issue_id: 120
tags: ['code-review', 'cleanup', 'simplicity']
dependencies: []
---

# Minor Python style + dead-comment cleanups

## Problem Statement
Catch-all for small, individually-trivial findings worth a single sweep:

1. **`bin/update-projects.py:175`** — `15` is a magic number for the enrichment cap. Hoist to module constant `MAX_COMMIT_ENRICHMENTS` next to `EVENTS_PER_PROJECT`.

2. **`bin/update-public-feeds.py`** — repeated XML element-extract pattern: `el.text.strip() if el is not None and el.text else default`. Consider a tiny helper `_text(el, default="")` to dedupe at lines 73, 138, 157, 200, 216, 246.

3. **`bin/update-projects.py:101-102`** — `_render_markdown_inline` runs `_MD_BOLD_RE` then `_MD_CODE_RE` against already-escaped text. If a bold span contains backticks (e.g., `` **`foo`** ``), the code regex matches inside the `<strong>` substitution and produces nested tags. Probably fine in practice; tighten the docstring's "order matters" claim or add a regression test.

4. **`script.js:2`** — `// Email is now a plain mailto:; no reveal logic needed.` — WHAT-not-WHY comment about removed code. Drop.

5. **`bin/update-projects.py:285-294`** — when all projects fail (`failures` populated, no `updates`) but `content_changed` is false, the success-path `record_heartbeat("projects")` runs and the error-path `record_heartbeat("projects", error=...)` is unreachable. Check `failures and not updates` before the `content_changed` short-circuit.

**Surfaced by:** kieran-python-reviewer + architecture-strategist + code-simplicity-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Single sweep commit
- All five micro-cleanups in one pass
- **Effort:** Small (~30 min)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] No magic numbers in `update-projects.py`
- [ ] XML extract pattern centralized (or accepted as fine-as-is)
- [ ] All-failures path records error heartbeat correctly
- [ ] Stale `script.js` comment removed
- [ ] Tests pass

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
