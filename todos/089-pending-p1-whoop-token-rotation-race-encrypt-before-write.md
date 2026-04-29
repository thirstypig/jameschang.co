---
status: pending
priority: p1
issue_id: 089
tags: ['code-review', 'security', 'oauth', 'whoop']
dependencies: []
---

# WHOOP token rotation race: encrypt-after-write can permanently break sync

## Problem Statement
`bin/update-whoop.py:272` calls `encrypt_refresh_token(new_refresh)` *after* `write_now_html()` and `record_heartbeat()`. WHOOP rotates refresh tokens on every use — once `get_access_token()` returns at line 95, the old token is dead. If the runner is killed, encryption fails, or any prior step `sys.exit(1)`s, the new token is never persisted to `.whoop-token.enc` → next run can't refresh → permanent lockout requiring manual `bin/whoop-auth.sh` re-run.

`bin/update-trakt.py:208-210` does this correctly: encrypt immediately after refresh, before any side-effect work. Copy that ordering.

**Surfaced by:** security-sentinel + kieran-python-reviewer (cross-agent agreement) during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Hoist encrypt to right after token refresh
- Move the `encrypt_refresh_token(new_refresh)` call to immediately after `get_access_token()` returns the rotated token, before `write_now_html()` and any other I/O
- Mirror `update-trakt.py:208-210`'s ordering
- **Effort:** Small (~10 minutes)

## Recommended Action
_(Filled during triage)_

## Technical Details
- `bin/update-whoop.py:95-102` — token refresh returns new_refresh
- `bin/update-whoop.py:272` — current encrypt call (too late)
- `bin/update-trakt.py:208-210` — reference pattern
- Solution doc: `docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md`

## Acceptance Criteria
- [ ] `encrypt_refresh_token(new_refresh)` runs before `write_now_html()`
- [ ] If encryption fails, script exits before HTML/heartbeat writes
- [ ] Existing `tests/test_whoop.py` still passes

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |

## Resources
- Solution doc: docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md
- Reference: bin/update-trakt.py:208-210
