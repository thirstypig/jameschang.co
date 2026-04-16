---
status: pending
priority: p2
issue_id: 057
tags: [code-review, documentation]
dependencies: []
---

# CLAUDE.md missing Spotify + public-feeds docs, has stale enumerated todo list

## Problem
`CLAUDE.md` was written when only WHOOP sync existed. Issues: (a) line 20 lists only `update-whoop.py` under `/bin/`, missing update-spotify.py and update-public-feeds.py. (b) line 21 says "GitHub Actions (daily WHOOP sync)" — now inaccurate, three workflows exist. (c) lines 91-97 enumerate todos 029-034 which will go stale. (d) No documented "add a new feed" recipe — future agent adding Strava would reverse-engineer conventions.

## Proposed Solutions
Update CLAUDE.md to (a) list all three scripts and the state files, (b) describe the three workflows with cadence, (c) add a "Data feeds on /now" section with the marker convention + add-a-new-feed 5-step recipe, (d) remove the enumerated todo list (the `todos/` dir is already the source of truth).

## Acceptance Criteria
- [ ] CLAUDE.md accurately documents all current sync scripts + workflows; add-a-new-feed recipe present; no inline enumerated todos.
