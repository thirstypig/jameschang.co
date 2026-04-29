---
status: complete
priority: p3
issue_id: 119
tags: ['code-review', 'agent-native', 'documentation']
dependencies: []
---

# Add `bin/.env.example` + tighten resume.pdf regen instructions

## Problem Statement
Two related agent-reproducibility items:

1. **No `bin/.env.example`** documenting the env-var matrix per script. A cold agent has to grep `os.environ` across 6 files to learn what each script needs (whoop: 3 vars + enc file; spotify: 3 vars; plex: 2 vars; projects: 1 var; public-feeds: 0 vars).

2. **`resume.pdf` regen snippet leaves an orphan `python3 -m http.server` process.** CLAUDE.md and README both show `python3 -m http.server 8787 &` with no `kill %1` / trap. Agents looping regen accumulate processes on port 8787.

**Surfaced by:** agent-native-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Create env example + fix regen snippet
- Add `bin/.env.example` listing every env var with one-line comment per var
- Reference from CLAUDE.md "Local preview" section
- Wrap regen snippet: start server in background, capture pid, kill at end (or use `trap`)
- **Effort:** Small (~30 min)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] `bin/.env.example` exists and is referenced from CLAUDE.md
- [ ] Resume regen snippet cleans up its background process
- [ ] A cold agent can run `cp bin/.env.example .env` (or equivalent) and the scripts succeed

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
