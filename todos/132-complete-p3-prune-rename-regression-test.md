---
status: pending
priority: p3
issue_id: 132
tags: ['code-review', 'testing', 'simplicity']
dependencies: []
---

# Drop test_now_js_renames_hitlist_to_eat_at — one-shot regression, not load-bearing

## Problem Statement
`tests/test_site_e2e.py::TestBucketList::test_now_js_renames_hitlist_to_eat_at` (lines 965-974) asserts that `now/now.js` contains `"places i want to eat at"` and does NOT contain `"places i want to try"`. It was added to lock in the rename when the bucket list took over the broader "want to try" framing.

This kind of "regression test for a one-shot text rename" is maintenance noise: it never catches a real bug, but it breaks any future innocent edit of the section title. Anyone touching the title text will wonder why a test failed.

The other 8 tests in `TestBucketList` are load-bearing (schema, uniqueness, render targets, no-top-nav-link, page-loads). This one isn't.

**Surfaced by:** code-simplicity-reviewer (#4) during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Delete the test (recommended)
Just remove it. No replacement needed.

**Effort:** Trivial (~2 min)
**Risk:** None.

### Option B — Keep it
Argument: defensive against an accidental revert. Counterargument: titles will keep evolving; this test will keep needing updates. Not worth the friction.

## Acceptance Criteria
- [ ] Test removed
- [ ] Test count drops from 9 to 8 in `TestBucketList`
- [ ] Total suite count goes 183 → 182 (or stays 183 if other todos add tests first)

## Resources
- `tests/test_site_e2e.py:965-974`
