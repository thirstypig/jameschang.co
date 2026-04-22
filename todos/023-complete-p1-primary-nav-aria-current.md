---
status: done
priority: p1
issue_id: 023
tags: [code-review, accessibility, a11y]
dependencies: []
---

# Primary nav missing `aria-current="page"` on all 13 pages

## Problem

The `.site-header-inner` > `<nav>` primary nav block was injected via Python regex pass that didn't parameterize the current page. No nav item ever gets `aria-current="page"`, even when the page matches.

Affected pages:
- `/now/index.html` → "Now" link should have `aria-current="page"`
- `/work/index.html` and all 10 deep-dive pages → "Work" should have `aria-current="page"` (site-brand is NOT the current page, it's a home link — don't add aria-current to site-brand)
- Homepage → one of About/Experience/Work depending on scroll position is ambiguous; convention: no aria-current on homepage since it's a single-page scroll with multiple anchors

**Screen reader impact:** users cannot tell which primary section they're in. WCAG 2.2 violation (minor).

## Proposed Solutions

### Option A (Recommended): Add aria-current based on page URL
- Python pass across 13 files
- /now/ → `<a href="/now/" aria-current="page">Now</a>`
- /work/* → `<a href="/#work" aria-current="page">Work</a>` (note: fragment URL issues)
- Homepage → no aria-current (anchors are not pages)

### Option B: Skip; accept minor a11y regression
Fast but fails agent-native tests.

## Acceptance Criteria
- [ ] /now/ nav has `aria-current="page"` on "Now"
- [ ] All 10 /work/*/ pages have it on "Work"
- [ ] Homepage has none (anchors are in-page, not separate URLs)
- [ ] Screen reader announces "current page" when focused on the right item

## Resources
- pattern-recognition review 2026-04-15, H3
