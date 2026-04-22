---
status: done
priority: p1
issue_id: 045
tags: [code-review, architecture, reliability]
dependencies: []
---

# WHOOP refresh token rewrite happens before API calls succeed (lockout risk)

## Problem
`bin/update-whoop.py` calls `encrypt_refresh_token(new_refresh)` immediately after the token exchange, before fetching recovery/sleep/cycle data. If the GitHub Action is cancelled or the subsequent fetches hang between the token exchange and the final commit, WHOOP's server has registered the new token but the repo never commits it — next run fails with `invalid_grant` because the stored token is the now-invalid previous one. Requires manual re-auth via `bin/whoop-auth.sh`.

## Proposed Solutions
Either (a) defer `encrypt_refresh_token()` until after the HTML write and the git commit succeed, or (b) write to `.whoop-token.enc.new` and atomically rename only after commit succeeds. Option (a) is simplest — keep the new refresh token in memory, do all work, write the encrypted file as the last step before git add.

## Acceptance Criteria
- [ ] No scenario where the rotated token is committed without the corresponding data update
- [ ] A cancelled workflow never leaves the token in an inconsistent state
