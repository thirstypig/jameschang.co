---
status: done
priority: p2
issue_id: 069
tags: [code-review, python, quality]
dependencies: []
---

# Python scripts: unused imports, missing heartbeat, mid-function import

## Problem Statement
Three minor code quality issues in the Python sync scripts:

1. **Unused imports** in `bin/update-public-feeds.py` (lines 14, 16): `import json` and `import sys` are never used.
2. **Missing `record_heartbeat`** in `bin/update-spotify.py` (line 224): The `content_changed()` early-return path does not call `record_heartbeat("spotify")`. If Spotify data is unchanged for 48+ hours, the staleness check could fire a false alarm.
3. **Mid-function import** in `bin/update-spotify.py` (line 203): `import re as _re` inside `main()` rather than at the top with other imports.

## Proposed Solutions

### Option A: Fix all three (Recommended)
1. Remove `import json` and `import sys` from update-public-feeds.py
2. Add `record_heartbeat("spotify")` before the `content_changed` early return
3. Move `import re` to the top-level imports in update-spotify.py
- **Effort:** Small (5 minutes)
- **Risk:** None

## Acceptance Criteria
- [ ] No unused imports in update-public-feeds.py
- [ ] Spotify early-return path calls record_heartbeat
- [ ] No mid-function imports in update-spotify.py

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |
