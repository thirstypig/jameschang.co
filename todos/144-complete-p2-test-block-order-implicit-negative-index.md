---
status: complete
priority: p2
issue_id: "144"
tags: [code-review, tests, quality]
---

## Problem Statement
`test_deep_dive_block_order` in `tests/test_site_e2e.py` relied on Python's negative-index arithmetic to implicitly catch missing required elements (`project-nav`, `work-hero`). If either was absent, `body.find()` returns `-1`, and the chained comparison `i_pnav < i_hero` would evaluate to `False` — catching the problem, but producing a cryptic failure message like `work-hero=-1` with no clear explanation.

## Findings
- **File:** `tests/test_site_e2e.py` — `test_deep_dive_block_order`
- **Issue:** No explicit guard for `-1` returns; correctness was accidental
- **Impact:** Test would still catch missing elements but give confusing output; next reader would question whether the logic was intentional
- **Caught by:** code-simplicity-reviewer agent during /ce:review on 2026-05-13

## Resolution
Added explicit guard at top of loop body:
```python
if i_pnav == -1 or i_hero == -1:
    failures.append(f"{f}: missing required element — project-nav={i_pnav}, work-hero={i_hero}")
    continue
```
Removed the redundant `0 <` prefix from the comparison branches since the guard ensures non-negative values.

## Work Log
- 2026-05-13: Found by code-simplicity-reviewer. Fixed immediately. 224 tests passing.
