---
status: pending
priority: p2
issue_id: 104
tags: ['code-review', 'security', 'oauth']
dependencies: []
---

# OpenSSL passphrase passed via argv exposes it in `/proc/<pid>/cmdline`

## Problem Statement
`bin/update-whoop.py:55-65` and `bin/update-trakt.py:71-81` invoke openssl with `-pass pass:{key}`. On a multi-user host, any user can read `/proc/<pid>/cmdline` and grab the key for the lifetime of the openssl process. On the GitHub Actions runner this is single-tenant + ephemeral, but local runs on a shared host (or a future build server) would leak `WHOOP_TOKEN_KEY` / `TRAKT_TOKEN_KEY`.

**Surfaced by:** security-sentinel during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Use `-pass env:WHOOP_TOKEN_KEY`
- Reads from environment instead of argv
- Trivial change, no script restructuring
- **Effort:** Trivial (~10 min)

### Option B: Mode-600 tempfile + `-pass file:/path/to/keyfile`
- More defense-in-depth (env vars also visible to children)
- **Effort:** Small

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] No openssl invocation has the passphrase in argv
- [ ] Encrypt + decrypt round-trip still works (`bin/whoop-encrypt.sh` parity check passes)

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
