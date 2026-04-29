---
status: pending
priority: p2
issue_id: 099
tags: ['code-review', 'agent-native', 'reliability']
dependencies: []
---

# Sync scripts crash with bare KeyError when env vars missing (no preflight)

## Problem Statement
`update-spotify.py:45-47`, `update-trakt.py:86-87,127`, `update-projects.py:245` access `os.environ["KEY"]` directly. When run cold without env vars exported, they raise `KeyError: 'SPOTIFY_CLIENT_ID'` and a 30-line traceback — opaque for a fresh agent or human.

`update-whoop.py:38-40` has the right pattern: check required vars, print missing list, `sys.exit(1)`.

**Surfaced by:** agent-native-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Replicate WHOOP's preflight in spotify/trakt/projects
- At top of `main()`: list required env vars, check `os.environ.get(...)` for each, print missing + exit 1
- **Effort:** Small (~20 min, three scripts)

### Option B: Add `bin/.env.example` documenting the matrix
- Combined with Option A, lets a cold reader find the answer in one place
- See companion todo for the env example file
- **Effort:** Trivial

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] Each script exits cleanly with a "Missing env vars: X, Y" message
- [ ] No bare `KeyError` traceback when run without env

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |

## Resources
- Reference pattern: bin/update-whoop.py:38-40
