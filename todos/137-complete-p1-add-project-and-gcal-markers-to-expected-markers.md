---
status: complete
priority: p1
issue_id: 137
tags: ['code-review', 'testing', 'now-page', 'projects-sync']
dependencies: []
---

# Add project section + GCAL markers to EXPECTED_MARKERS

## Problem Statement

`tests/test_site_e2e.py::TestFeedMarkers.test_all_markers_present` checks that sync-script injection targets exist in `now/index.html` — but it only guards 8 of the 14 active marker pairs. Six markers are missing from `EXPECTED_MARKERS`:

- `ACTIVE-PROJECTS`, `BACKBURNER-PROJECTS`, `ACTIVE-EYEBROW`, `BACKBURNER-EYEBROW` (projects sync)
- `GCAL`, `GCAL-EYEBROW` (Google Calendar sync)

The 4 project markers going missing caused a **silent 4-day outage** (May 7–11, 2026). CI ran green on every push during that period because the test didn't check for them. The fix is a one-line addition; no new test logic is needed.

**Surfaced by:** simplicity-reviewer + architecture-strategist during /ce:review 2026-05-11.

## Findings

- `tests/test_site_e2e.py` line 34: `EXPECTED_MARKERS = ["WHOOP", "SPOTIFY", "MLB", "GOODREADS-READING", "GOODREADS", "FBST", "PLEX", "PAGE-UPDATED"]`
- `TestFeedMarkers.test_all_markers_present` (line 299) iterates this list and asserts each `NAME-START` + `NAME-END` pair exists in `now/index.html`
- `update-projects.py` bails silently if `ACTIVE-PROJECTS` or `BACKBURNER-PROJECTS` are missing; same for `update-gcal.py` with `GCAL` and `GCAL-EYEBROW`
- Both GCAL marker pairs were simply never added when the feed was introduced

## Proposed Solutions

### Option A — Add all 6 missing markers (recommended)

```python
EXPECTED_MARKERS = [
    "WHOOP", "SPOTIFY", "MLB", "GOODREADS-READING", "GOODREADS", "FBST", "PLEX",
    "PAGE-UPDATED",
    "ACTIVE-PROJECTS", "BACKBURNER-PROJECTS", "ACTIVE-EYEBROW", "BACKBURNER-EYEBROW",
    "GCAL", "GCAL-EYEBROW",
]
```

**Effort:** Trivial (one line)
**Risk:** None — the markers all exist in `now/index.html` today; tests will pass immediately.

### Option B — Add project markers only, defer GCAL

Add just the 4 project markers now, add GCAL separately.

**Effort:** Same trivial effort, just split across two commits for no benefit. Not recommended.

## Recommended Action

Option A. One line, zero risk, closes the gap that caused a real outage.

## Acceptance Criteria

- [ ] `EXPECTED_MARKERS` contains all 14 markers (8 existing + 6 new)
- [ ] `python3 -m pytest tests/test_site_e2e.py -v -k test_all_markers_present` passes
- [ ] Full test suite passes (221 tests)

## Work Log

- 2026-05-11: Identified during /ce:review — simplicity-reviewer + architecture-strategist both flagged independently.
