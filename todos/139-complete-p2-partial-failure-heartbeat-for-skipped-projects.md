---
status: complete
priority: p2
issue_id: 139
tags: ['code-review', 'architecture', 'projects-sync', 'observability']
dependencies: []
---

# Record partial-failure heartbeat when individual projects skip

## Problem Statement

`bin/update-projects.py` only records an error heartbeat when **all** projects fail (line 380). When one or more projects are silently skipped (e.g. 404 from the GitHub API due to bad PAT scope), the heartbeat is recorded as success and `check-feed-health.py` never opens a GitHub issue. The project disappears from `/now` indefinitely with no alert.

ktv-singer has been silently skipping on every daily run since the marker fix — the heartbeat reads healthy because the other 8 projects succeeded.

**Surfaced by:** architecture-strategist during /ce:review 2026-05-11.

## Findings

- `bin/update-projects.py` line 379–382: only errors heartbeat on all-fail
- `bin/update-projects.py` line 433: `record_heartbeat("projects")` — no-args call records clean success even if `failures` list is non-empty
- `bin/check-feed-health.py`: reads `last_error` from `.feeds-heartbeat.json`; if absent, feed is considered healthy
- `.feeds-heartbeat.json` currently shows `projects` as healthy despite ktv-singer skipping on every run

## Proposed Solutions

### Option A — Annotate heartbeat with failure list (recommended)

After line 433, change to:

```python
if failures:
    record_heartbeat("projects", error=f"skipped {len(failures)} project(s): {', '.join(failures)}")
else:
    record_heartbeat("projects")
```

This records `last_error` alongside `last_success_utc` so the failure is visible in `.feeds-heartbeat.json` without triggering the staleness monitor (which only fires on missing `last_success_utc`). The staleness check won't open a GitHub issue for this, but the error is surfaced in the heartbeat file for manual review.

**Effort:** Small (3 lines)
**Risk:** None — heartbeat format supports arbitrary `error` strings; existing staleness check only uses `last_success_utc`.

### Option B — Open a separate GitHub issue per skipped project

More signal, significantly more complexity. Not proportionate for a one-person site.

### Option C — Print a WARNING line to stdout and accept the silence

Already happens (`print("    skipped (no TLDR content)")`). The workflow log captures it, but nobody reads the log unless something is broken. Not sufficient.

## Recommended Action

Option A. Three lines, zero risk, makes skipped projects visible in the committed heartbeat file.

## Acceptance Criteria

- [ ] `record_heartbeat("projects", error=...)` called when `failures` is non-empty
- [ ] `.feeds-heartbeat.json` shows the failure list after a run with skipped projects
- [ ] `record_heartbeat("projects")` (no error) called when all projects succeed
- [ ] Existing heartbeat tests in `tests/test_shared.py` still pass

## Work Log

- 2026-05-11: Identified during /ce:review — architecture-strategist finding. ktv-singer is the live example.
