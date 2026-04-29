---
status: complete
priority: p1
issue_id: 093
tags: ['code-review', 'correctness', 'projects-sync']
dependencies: []
---

# Lexicographic ISO-8601 sort breaks if any timestamp uses `+00:00` instead of `Z`

## Problem Statement
`bin/update-projects.py:198`:
```python
merged.sort(key=lambda e: e["time"], reverse=True)
```
Sorts ISO-8601 strings lexicographically. Works today because GitHub's events API emits `Z` suffix uniformly, but breaks silently if any timestamp ever passes through `datetime.isoformat()` (which emits `+00:00`). The mismatch sorts `+00:00` strings before `Z` strings of the same instant, scrambling shipping order.

**Surfaced by:** kieran-python-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Parse to `datetime` for the sort key
- `key=lambda e: datetime.fromisoformat(e["time"].replace("Z", "+00:00"))`
- Robust against timezone-suffix drift
- **Effort:** Small (~5 min)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] Sort is timezone-suffix-agnostic
- [ ] `tests/test_projects.py` covers a mixed-suffix case

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
