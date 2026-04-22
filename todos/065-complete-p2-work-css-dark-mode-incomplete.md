---
status: done
priority: p2
issue_id: 065
tags: [code-review, css, dark-mode]
dependencies: []
---

# Dark mode incomplete in work.css — missing [data-theme="dark"] selectors

## Problem Statement
The site supports dark mode via two mechanisms: `@media (prefers-color-scheme: dark)` for OS preference and `[data-theme="dark"]` for the manual toggle. Several components in `work/work.css` only have the `@media` query, missing the `[data-theme="dark"]` override. Users on a light-mode OS who manually toggle dark mode see light-colored elements on a dark background.

## Findings
Affected components:
- `.release-tag` variants (lines 163-168): `.security`, `.feature`, `.improvement`, `.fix` — dark overrides only via `@media`
- `.arch-block` (lines 353-355): Only `@media` dark override
- `.comp-table .yes` (line 299): Hardcoded `#3a7a4a`, no dark mode at all
- `.feature-list li.done::before` (line 245): Hardcoded `#3a7a4a`, no dark mode

Meanwhile, `.terminal`, `.prompt-excerpt pre`, `.whoop-*` colors correctly have both selectors. The pattern is inconsistent within the same file.

## Proposed Solutions

### Option A: Add matching [data-theme="dark"] blocks (Recommended)
For each `@media (prefers-color-scheme: dark)` block that overrides work.css components, add a parallel `[data-theme="dark"]` selector with identical values.
- **Effort:** Small
- **Risk:** None

### Option B: Also add success-green tokens
In addition to Option A, extract `#3a7a4a` into `--success-green` / `--success-green-dark` CSS custom properties.
- **Effort:** Small-Medium
- **Risk:** Low — requires auditing all uses of the color

## Acceptance Criteria
- [ ] `.release-tag.*` variants have `[data-theme="dark"]` overrides
- [ ] `.arch-block` has `[data-theme="dark"]` override
- [ ] `.comp-table .yes` has dark-mode color (via either mechanism)
- [ ] `.feature-list li.done::before` has dark-mode color
- [ ] Manual dark toggle produces correct colors on all work subpages

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |
