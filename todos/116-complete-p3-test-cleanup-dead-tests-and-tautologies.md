---
status: complete
priority: p3
issue_id: 116
tags: ['code-review', 'tests', 'simplicity']
dependencies: []
---

# Test cleanup: dark-mode parity references deleted file, exhaustive ordinal tests, tautological MLB test

## Problem Statement
Cluster of small test-quality findings:

1. **`tests/test_site_e2e.py:329-350` `TestDarkModeParity`** iterates over `["styles.css", "projects/projects.css"]`. `styles.css` was deleted in commit `ecacb5b`. The loop's `if not os.path.exists(path): continue` silently skips it. Drop `"styles.css"` from the list.

2. **`tests/test_feeds.py:50-93` `TestOrdinal`** has 12 tests for a 4-line `ordinal()` function. (1, 2, 3, 11, 21, 100, 111) already prove the algorithm; the rest are redundant rotations. Trim to ~5 tests.

3. **`tests/test_feed_builders.py:17-35` `TestMlbBlock.test_offseason_message`** body asserts `html is not None or html is None  # just ensure no crash` — tautology, no behavior tested. Either mock `datetime.now().date()` properly to test offseason rendering, or delete.

**Surfaced by:** code-simplicity-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Single test-cleanup commit
- Drop `styles.css` from parity loop
- Trim ordinal tests to ~5 representative cases
- Mock-and-assert the offseason path properly, or delete the tautological test
- **Effort:** Small (~30 min)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] No test references files that don't exist
- [ ] Test counts in CLAUDE.md / README.md updated to match
- [ ] All remaining tests assert real behavior

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
