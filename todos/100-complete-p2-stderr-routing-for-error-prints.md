---
status: complete
priority: p2
issue_id: 100
tags: ['code-review', 'observability', 'sync-pipeline']
dependencies: []
---

# Sync scripts print errors to stdout instead of stderr

## Problem Statement
All `bin/update-*.py` scripts use `print(...)` for warnings and errors, sending them to stdout. GitHub Actions logs both streams, but stderr would let Actions UI separate "errors" from "normal output" visually, and would let any future shell pipeline filter accordingly.

Affects: `update-whoop.py:39,42,50,64,119,258`, `update-spotify.py`, `update-trakt.py`, `update-plex.py`, `update-public-feeds.py`, `update-projects.py`.

**Surfaced by:** kieran-python-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Audit and route error/warning prints to stderr
- `print(..., file=sys.stderr)` for warning/error paths
- Keep success/info prints on stdout
- **Effort:** Small (~30 min across 6 files)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] All warning/error `print()` calls in `bin/update-*.py` route to `sys.stderr`
- [ ] Success messages remain on stdout

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
