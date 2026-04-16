---
status: pending
priority: p3
issue_id: 062
tags: [code-review, observability]
dependencies: []
---

# No staleness monitor — silent sync failures go unnoticed

## Problem
If the WHOOP/Spotify/public-feeds sync silently stops working (API change, auth failure, workflow disabled), the /now page shows increasingly stale data but nothing alerts. `git diff --cached --quiet` legitimately suppresses empty commits, which is indistinguishable from "script crashed before reaching the diff."

## Proposed Solutions
(1) Have each sync script write a `.feeds-heartbeat.json` with `{last_success_utc, last_error}` per feed — committed unconditionally. (2) Add a weekly GitHub Action that reads the heartbeat file and opens an issue if any feed is >48h stale. Or cheaper: use `echo "::warning::WHOOP stale"` in the workflow to surface in the Actions UI.

## Acceptance Criteria
- [ ] Each sync records a timestamped heartbeat; staleness >48h is visible somewhere without manual checking.
