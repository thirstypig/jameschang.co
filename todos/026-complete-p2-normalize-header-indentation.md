---
status: pending
priority: p2
issue_id: 026
tags: [code-review, cosmetic, quality]
dependencies: []
---

# Normalize header block indentation across 13 files (regex-injection artifact)

## Problem

Python regex injection added the `.site-header-inner` block without re-indenting its contents. Across all 13 files:

```html
    <div class="site-header-inner">          ← 4sp
    <a href="/" class="site-brand">…</a>      ← 4sp  (should be 6sp, child of div)
      <nav aria-label="Primary">              ← 6sp
      <a href="…">About</a>                   ← 6sp  (should be 8sp, child of nav)
      ...
      <button class="theme-toggle">…</button> ← 6sp  (should be 8sp)
    </nav>                                     ← 6sp  (should be 4sp)
    </div>                                     ← 4sp
```

Two-level indentation bug. Renders fine; future hand-edits will be confusing.

## Proposed Solutions

### Option A (Recommended): One-shot normalization via `prettier` or `tidy -i`
Prettier with HTML config, or manual Python pass that rewrites the block at correct indent levels. 5-minute chore.

### Option B: Manual edit pass across 13 files
Tedious but precise.

### Option C: Leave it
Works, but any future regex-based injections will compound the issue.

## Acceptance Criteria
- [ ] All 13 HTML headers indent consistently (div:4, brand:6, nav:6, nav links:8, close nav:6, close div:4)
- [ ] Diff shows only whitespace changes
- [ ] Pages still render identically

## Resources
- pattern-recognition review 2026-04-15, M1
- code-simplicity review 2026-04-15, mentions same issue
