---
status: pending
priority: p3
issue_id: 134
tags: ['code-review', 'simplicity', 'cross-repo-admin', 'thirstypig']
dependencies: []
---

# BucketListManager: minor cosmetic cleanups

## Problem Statement
Three small individually-trivial findings in `tina/BucketListManager.tsx` worth a single sweep:

1. **Slug regex literal `/[̀-ͯ]/g` (line 218)** — the combining-marks Unicode range works correctly (tsc compiles, runtime correct) but the literal characters are easy to mangle on copy/paste through editors. Prefer the explicit escape `/[̀-ͯ]/g`.

2. **`commit()`'s `message` parameter shadows the React state name (line 341).** Currently both compose without conflict, but a future refactor that destructures `message` from a hook will break confusingly. Rename to `commitMsg`.

3. **`loadPublicReadOnly` doesn't capture sha (lines 289-301).** If the user later pastes a token, the existing flow correctly calls `reload(trimmed)` to refresh sha — so this isn't a bug. But it's worth a one-line comment explaining why `commit` isn't reachable in read-only mode (the `if (!token)` guard on line 342) so a future contributor doesn't try to "fix" it by initializing sha to "".

**Surfaced by:** kieran-typescript-reviewer (#9, #10, #6) during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Single sweep
Apply all three in one PR. None individually justifies a commit.

**Effort:** Trivial (~10 min total)
**Risk:** None.

## Acceptance Criteria
- [ ] Regex uses `/[̀-ͯ]/g`
- [ ] `commit(items, commitMsg)` rename applied at the function and all call sites
- [ ] One-line comment near `loadPublicReadOnly` explaining the read-only contract

## Resources
- `/Users/jameschang/Projects/thirstypig/tina/BucketListManager.tsx:218,341,289-301`
