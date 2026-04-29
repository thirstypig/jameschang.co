---
status: complete
priority: p2
issue_id: 106
tags: ['code-review', 'correctness', 'html']
dependencies: []
---

# `escape_html(text)[:90]` can split mid-entity producing malformed HTML

## Problem Statement
`bin/update-projects.py:213-214`:
```python
escape_html(ev["summary"])[:90]
```
Slicing escaped HTML by character count can split `&amp;` → `&am`, producing invalid markup. Cosmetic, not exploitable, but worth fixing for correctness.

**Surfaced by:** security-sentinel + kieran-python-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Truncate raw, then escape
- `escape_html(ev["summary"][:90])`
- **Effort:** Trivial

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] Truncation happens before escaping at all call sites in `update-projects.py`
- [ ] Regression test: input ending in `&` near boundary doesn't produce `&am`

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
