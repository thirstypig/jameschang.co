---
status: complete
priority: p3
issue_id: 114
tags: ['code-review', 'simplicity', 'dead-code']
dependencies: []
---

# `record_heartbeat` writes `last_run_utc` but no caller reads it

## Problem Statement
`bin/_shared.py:40-60::record_heartbeat` writes `last_run_utc` on every call. `bin/check-feed-health.py` only reads `last_success_utc` and `last_error`. The `last_run_utc` field is write-only. The defensive `existing` lookup that preserves it is also unnecessary.

`tests/test_shared.py:295-297` asserts the write — which becomes a low-value test once the field is dropped.

**Surfaced by:** code-simplicity-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Drop `last_run_utc` from `record_heartbeat`
- Simpler write path
- Drop the matching `tests/test_shared.py` assertion
- **Effort:** Trivial

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] `last_run_utc` no longer written
- [ ] `.feeds-heartbeat.json` regenerated cleanly (or the field harmlessly remains as legacy data)
- [ ] Tests pass

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
