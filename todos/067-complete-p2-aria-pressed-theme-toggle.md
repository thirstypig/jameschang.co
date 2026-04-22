---
status: done
priority: p2
issue_id: 067
tags: [code-review, accessibility]
dependencies: []
---

# Missing aria-pressed="false" on theme toggle in 14 of 16 HTML files

## Problem Statement
Only `index.html` and `privacy/index.html` include `aria-pressed="false"` on the theme toggle button. The remaining 14 pages omit it. While `script.js` sets `aria-pressed` dynamically via `syncPressed()`, there is an accessibility gap during page load before JS executes — screen reader users see an ambiguous toggle state.

## Findings
Pages WITH aria-pressed: `index.html:143`, `privacy/index.html:21`
Pages WITHOUT: All 12 work subpages, `now/index.html`, and callback pages (14 total)

## Proposed Solutions

### Option A: Add aria-pressed="false" to all 14 files (Recommended)
Simple attribute addition to the theme toggle button in each file.
- **Effort:** Small (14 identical edits)
- **Risk:** None

## Acceptance Criteria
- [ ] All HTML files with a theme toggle button include `aria-pressed="false"`
- [ ] `script.js` `syncPressed()` still correctly updates the value at runtime

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |
