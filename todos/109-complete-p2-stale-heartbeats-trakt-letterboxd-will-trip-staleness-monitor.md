---
status: complete
priority: p2
issue_id: 109
tags: ['code-review', 'monitoring', 'agent-native']
dependencies: []
---

# Stale heartbeats for `letterboxd` + `trakt` will trip the 48h staleness monitor

## Problem Statement
Trakt and Letterboxd were dropped 2026-04-28, but their `last_success_utc` timestamps in `.feeds-heartbeat.json` keep aging. Within 24h of disablement, `bin/check-feed-health.py` will open `Feed stale: letterboxd` and `Feed stale: trakt` GitHub issues — false alarms for deliberately retired feeds.

Same problem on the script side: `bin/check-feed-health.py:47, 49` `GUIDANCE` dict has stale keys `github` and `letterboxd` — `github` events were merged into `update-projects.py`'s `projects` heartbeat; `letterboxd` was dropped. Keys can never match a live heartbeat.

**Surfaced by:** architecture-strategist + agent-native-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Drop disabled-feed entries from heartbeat + GUIDANCE
- `git rm` the `letterboxd` and `trakt` keys from `.feeds-heartbeat.json`
- Drop `github` and `letterboxd` from `GUIDANCE`
- **Effort:** Trivial

### Option B: Add `DISABLED_FEEDS` skip-list in `check-feed-health.py`
- Future-proof for any feed re-enablement
- More code; less data churn
- **Effort:** Small

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] No staleness issue opens for trakt/letterboxd in next 48h+ run
- [ ] `GUIDANCE` dict matches active feed names

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
