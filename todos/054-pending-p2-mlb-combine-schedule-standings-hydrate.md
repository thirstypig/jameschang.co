---
status: pending
priority: p2
issue_id: 054
tags: [code-review, performance]
dependencies: []
---

# MLB script makes two API calls where hydrate param allows one

## Problem
`bin/update-public-feeds.py:211,226` — one call to `/standings` and another to `/schedule`. The schedule endpoint supports `hydrate=team,linescore,standings` — a single request returns all of: team abbreviation, game results with scores, and the team's standings context. Cuts MLB fetch latency ~50%.

## Proposed Solutions
Collapse to a single `/schedule` call with `hydrate=team,linescore,standings`. Parse standings from the hydrated response alongside games.

## Acceptance Criteria
- [ ] MLB block makes 1 API call per sync instead of 2; output unchanged.
