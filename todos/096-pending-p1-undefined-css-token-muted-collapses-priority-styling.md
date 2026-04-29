---
status: pending
priority: p1
issue_id: 096
tags: ['code-review', 'css', 'visual-regression']
dependencies: []
---

# `.priority-medium` and `.priority-low` reference undefined `var(--muted)`

## Problem Statement
`projects/projects.css:718-719` uses `var(--muted)`, but the token is not defined in `notebook.css` (only `--dim` exists; the cut-over to notebook tokens renamed it). The CSS property silently inherits, collapsing the visual hierarchy of priority indicators.

Used live on `/projects/aleph/roadmap/` (3 elements rendered with class `priority-medium` / `priority-low`).

**Surfaced by:** pattern-recognition-specialist during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Swap to `var(--dim)`
- One-line change in `projects/projects.css:718-719`
- Aligns with the rest of the notebook design system
- **Effort:** Trivial

### Option B: Define `--muted` as alias to `--dim` in notebook.css
- Fixes any other consumers that might exist; risks token sprawl
- **Effort:** Small

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] `var(--muted)` no longer appears as an undefined reference (or is defined)
- [ ] `/projects/aleph/roadmap/` priority chips render with intended dim color in both light and dark mode
- [ ] Screenshot diff vs current render

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
