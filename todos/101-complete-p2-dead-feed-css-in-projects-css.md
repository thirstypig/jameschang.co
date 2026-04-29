---
status: complete
priority: p2
issue_id: 101
tags: ['code-review', 'css', 'dead-code']
dependencies: []
---

# Delete ~226 lines of legacy feed CSS in `projects/projects.css`

## Problem Statement
`projects/projects.css:685-1080` contains ~47 unused selectors for legacy feed classes: `.spotify-*`, `.whoop-*`, `.trakt-*`, `.plex-*`, `.lb-*`, `.gh-*`, `.gr-*`, `.mlb-*`, `.fbst-*`, `.hitlist-*`, `.shipping-recent`, `.site-header nav a[aria-current]`, plus the `module-url` rule. CLAUDE.md states the 2026-04-27 cut-over emits `.nb-*` markup directly; per-feed classes are dead.

`grep -l` confirms zero references in any HTML, JS, or Python.

Keep only `.feed-empty` and `.feed-updated` (still used).

**Surfaced by:** performance-oracle + architecture-strategist + code-simplicity-reviewer (3-agent agreement) during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Delete the dead blocks
- Strip lines 685-1080 except `.feed-empty` and `.feed-updated`
- ~7.7 KB / 27.8% CSS reduction on every deep-dive page load
- **Effort:** Small (~30 min including grep verification + screenshot diff)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] All legacy feed-class rules removed
- [ ] `.feed-empty` and `.feed-updated` preserved
- [ ] Screenshot diff on `/projects/aleph/tech/` and `/now/` shows no regression
- [ ] Tests pass

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
