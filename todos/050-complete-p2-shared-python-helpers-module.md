---
status: pending
priority: p2
issue_id: 050
tags: [code-review, quality, architecture]
dependencies: []
---

# Extract shared Python helpers into bin/_shared.py

## Problem
Three sync scripts (update-whoop.py, update-spotify.py, update-public-feeds.py) each define their own `relative_time()`, `escape_html()` / `_escape()`, and `replace_marker()` — identical logic with slight naming drift. ~60 LOC of duplication. Adding a 4th feed means copy-paste-drift for a fourth time.

## Proposed Solutions
Create `bin/_shared.py` with `relative_time()`, `escape_html()`, `replace_marker()`, `REPO_ROOT`, `NOW_HTML`, `USER_AGENT`. Migrate all three scripts to import from it. Pure-helpers module — doesn't create shared failure mode since scripts are still independent processes.

## Acceptance Criteria
- [ ] Zero duplication of relative_time/escape_html/replace_marker across scripts; all three import from _shared.py.
