---
status: pending
priority: p3
issue_id: 059
tags: [code-review, quality]
dependencies: []
---

# MLB script hardcodes Pacific as UTC-7 (breaks during PST)

## Problem
`bin/update-public-feeds.py:258` uses `timezone(timedelta(hours=-7))` to localize game times. This is Pacific Daylight Time only — during PST (Nov-Mar) games display 1 hour off.

## Proposed Solutions
Use `zoneinfo.ZoneInfo("America/Los_Angeles")` (Python 3.9+, stdlib). Handles DST transitions automatically.

## Acceptance Criteria
- [ ] Game times correct year-round, including PST months.
