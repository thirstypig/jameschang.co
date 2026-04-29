---
status: pending
priority: p2
issue_id: 107
tags: ['code-review', 'security', 'oauth', 'trakt']
dependencies: []
---

# `trakt-auth.sh` prints token to stdout and assembles JSON via shell interpolation

## Problem Statement
Two issues in `bin/trakt-auth.sh`:

1. **Line 71:** prints the refresh token to stdout in plain. Other auth scripts (`whoop-auth.sh:82-90`, `spotify-auth.sh:75-80`) write secrets to a `umask 077` tempfile, avoiding terminal scrollback / recorded sessions / screen-share leakage.

2. **Lines 43-51:** JSON body is assembled via shell variable interpolation. `AUTH_CODE`, `TRAKT_CLIENT_ID`, `TRAKT_CLIENT_SECRET` get inlined into a JSON string. A `"` in any of them produces invalid JSON. Trakt PINs are alphanumeric in practice, so safe today, but fragile.

(Trakt is currently disabled per CLAUDE.md but the auth path is preserved for re-enable — fix anyway since the script will run again.)

**Surfaced by:** security-sentinel during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Mirror WHOOP/Spotify tempfile pattern + use jq for JSON
- Tempfile: `umask 077; tmp=$(mktemp); echo "$REFRESH_TOKEN" > "$tmp"; echo "Saved to: $tmp"`
- JSON: `jq -n --arg code "$AUTH_CODE" --arg cid "$TRAKT_CLIENT_ID" '{code:$code, client_id:$cid, ...}'` (or `python3 -c 'import json; print(json.dumps(...))'` if jq isn't a dep)
- **Effort:** Small (~30 min)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] No secret printed to stdout
- [ ] JSON body is constructed safely (jq or python)
- [ ] Re-running `trakt-auth.sh` still produces a valid encrypted token file

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
