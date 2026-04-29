---
status: complete
priority: p2
issue_id: 103
tags: ['code-review', 'security', 'plex']
dependencies: []
---

# Plex token sent in URL query string instead of header

## Problem Statement
`bin/update-plex.py:41` sends the Plex token as `?X-Plex-Token={PLEX_TOKEN}`. Tokens in URLs land in any logged URL (redirect chain, debug print, third-party error wrapper) and could leak via Action logs. Plex supports the same token via `X-Plex-Token` request header.

**Surfaced by:** security-sentinel during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Move token to request header
- Change `?X-Plex-Token={PLEX_TOKEN}` → `headers={"X-Plex-Token": PLEX_TOKEN}`
- **Effort:** Trivial (~5 min)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] No Plex token appears in any URL constructed by the script
- [ ] Plex sync still pulls session history correctly (test against real instance)

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
