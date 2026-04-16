---
status: pending
priority: p1
issue_id: 047
tags: [code-review, quality, logic-error]
dependencies: []
---

# MLB `games_back` string comparison misses valid "+0.0", "E" wildcard-leader, integer "0"

## Problem
`bin/update-public-feeds.py:266` has `if games_back and games_back != "-" and games_back != "0.0"` but the MLB API returns `games_back` as various strings: `"2.5"`, `"-"`, `"0.0"`, `"+0.0"`, `"E"` (elimination/wildcard leader in other contexts), sometimes just `"0"`. The current guard incorrectly treats `"+0.0"` and `"0"` as real games-back values and appends them to the display as `(+0.0 GB)` or `(0 GB)`.

## Proposed Solutions
Use `if games_back and games_back not in ("-", "0.0", "+0.0", "0", "E", "+0", "-0"):`. Or safer: try to convert to float and skip if zero/invalid.

## Acceptance Criteria
- [ ] Dodgers display never shows "+0.0 GB" or "(0 GB)"
- [ ] Leaders show no GB value
- [ ] Non-leaders show the real number
