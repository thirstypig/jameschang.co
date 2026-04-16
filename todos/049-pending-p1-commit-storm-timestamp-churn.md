---
status: pending
priority: p1
issue_id: 049
tags: [code-review, performance]
dependencies: []
---

# ~11 Pages rebuilds per day from timestamp-only HTML rewrites

## Problem
Three workflows (daily WHOOP, 4-hourly Spotify, 6-hourly public-feeds) each include `Auto-updated <today>` text in their generated HTML. Even when the underlying data is unchanged (MLB record same, no new listens, same recovery), the date line forces a file diff, a commit, a push, and a GitHub Pages rebuild. Estimated 11+ rebuilds/day, most with zero semantic change.

## Proposed Solutions
Two options: (a) Normalize out the `Auto-updated …` date line before diffing; only commit if non-date content changed. (b) Consolidate the three workflows into a single `sync.yml` running at a single cron with three jobs sharing one checkout/setup-python/commit cycle.

## Acceptance Criteria
- [ ] Commits per day drop to reflect actual data changes (target: <5/day)
- [ ] No "chore: update X" commits with identical underlying data
