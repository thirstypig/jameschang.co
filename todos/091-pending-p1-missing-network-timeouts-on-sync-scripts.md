---
status: pending
priority: p1
issue_id: 091
tags: ['code-review', 'reliability', 'sync-pipeline']
dependencies: []
---

# `urlopen()` and `subprocess.run()` calls without timeouts can hang Action runners

## Problem Statement
Multiple sync scripts call `urlopen(req)` without a `timeout=` argument. If the upstream stalls, the GitHub Action runner parks for up to its 6-hour ceiling, burning CI minutes and blocking the `concurrency: now-html-writer` group for other syncs.

`bin/_shared.fetch_json` already passes `timeout=15` — same default should apply everywhere.

**Surfaced by:** kieran-python-reviewer during /ce:review 2026-04-29.

## Findings
- `bin/update-whoop.py:95, 116` — `urlopen(req)` no timeout
- `bin/update-spotify.py:61, 80` — `urlopen(req)` no timeout (`get_access_token`, `api_get`)
- `bin/update-trakt.py:109, 131` — same
- `bin/check-feed-health.py:62, 71` — `subprocess.run` without `timeout=`

## Proposed Solutions
### Option A: Pass `timeout=15` to every `urlopen` and `timeout=30` to every `subprocess.run`
- Match `bin/_shared.fetch_json`'s default
- One-line change per call site
- **Effort:** Small (~15 min)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] All `urlopen()` calls in `bin/update-*.py` have `timeout=15`
- [ ] All `subprocess.run()` calls in `bin/check-feed-health.py` have `timeout=30`
- [ ] Existing tests still pass

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |

## Resources
- bin/_shared.py:184 — fetch_json reference
