---
status: complete
priority: p3
issue_id: 115
tags: ['code-review', 'simplicity', 'yagni']
dependencies: []
---

# `bin/projects-config.json` `"file"` field is YAGNI — every project hardcodes `"CLAUDE.md"`

## Problem Statement
`bin/projects-config.json` declares a per-project `"file"` field but every one of the 7 projects sets it to `"CLAUDE.md"`. The schema admits per-project file paths; nothing uses the variability.

**Surfaced by:** code-simplicity-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Hardcode `CLAUDE.md` and drop the field
- `bin/update-projects.py:261` hardcodes the path
- Drop `"file"` from each project block in JSON
- Drop `assert "file" in project` in `tests/test_projects.py:84`
- **Effort:** Trivial (~10 min)

### Option B: Keep for forward-compatibility
- If James anticipates per-project TLDR file paths (e.g., a repo where TLDR lives in README.md), keep the field
- **Effort:** Zero, but adds maintenance surface

## Recommended Action
_(Filled during triage — preference call)_

## Acceptance Criteria
- [ ] Decision recorded
- [ ] If A: schema clean, tests pass, sync still emits TLDRs

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
