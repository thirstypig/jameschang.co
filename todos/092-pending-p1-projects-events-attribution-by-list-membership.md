---
status: pending
priority: p1
issue_id: 092
tags: ['code-review', 'correctness', 'projects-sync']
dependencies: []
---

# `update-projects.py:181` attributes events by list-identity equality (silent miscredit risk)

## Problem Statement
At `bin/update-projects.py:181`:
```python
repo_name = [r for r, lst in by_repo.items() if entry in lst][0]
```
This is O(N²) and depends on `entry in lst` doing identity-ish dict equality. It works today because the same dict object is in `lst`, but a future refactor that copies entries (e.g., for filtering or sorting) silently picks the wrong repo and misattributes shipping events to the wrong project on /now.

Additionally, `events_list[:EVENTS_PER_PROJECT]` is sliced unsorted at `:170-171` — the "first N" enriched may differ from the "first N" returned by `events_for_project()` which sorts by time.

**Surfaced by:** kieran-python-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Stamp repo name on the entry at construction time
- When building `by_repo`, set `entry["_repo"] = repo` so attribution is a direct field lookup
- Eliminates the comprehension entirely
- **Effort:** Small (~15 min)

### Option B: Iterate `(repo, entries)` pairs and slice within the loop
- Refactor the enrichment loop to operate per-repo, slicing `entries[:EVENTS_PER_PROJECT]` directly
- **Effort:** Small

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] No comprehension-as-lookup in `update-projects.py`
- [ ] Events are sorted by time before slicing for enrichment
- [ ] `tests/test_projects.py` still passes; consider adding a regression test for entry copying

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
