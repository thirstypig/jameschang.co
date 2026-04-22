---
status: done
priority: p2
issue_id: 070
tags: [code-review, performance]
dependencies: []
---

# Inconsistent cache-busting query strings on CSS references

## Problem Statement
Two dashboard pages (`work/aleph/dashboard/index.html` and `work/fantastic-leagues/dashboard/index.html`) use versioned CSS links (`/styles.css?v=20260417`, `/work/work.css?v=20260417`) while all other pages use bare paths. This creates inconsistency: those 2 pages always fetch fresh CSS while the other 14 rely on GitHub Pages' 600-second cache.

## Proposed Solutions

### Option A: Remove version strings from the 2 pages (Recommended)
Match all other pages. GitHub Pages' 600-second cache is short enough that manual cache-busting is unnecessary.
- **Effort:** Small
- **Risk:** None

### Option B: Add version strings to all pages
Consistent cache-busting everywhere, but requires updating all 16 files on every CSS change.
- **Effort:** Medium (16 files to maintain)
- **Risk:** Easy to forget updating version strings

## Acceptance Criteria
- [ ] All HTML files use the same CSS reference pattern (with or without version strings)

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |
