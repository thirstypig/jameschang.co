---
status: pending
priority: p2
issue_id: 051
tags: [code-review, security]
dependencies: []
---

# HTTPError response bodies printed verbatim to GitHub Actions logs can leak tokens

## Problem
`bin/update-whoop.py:88-90`, `bin/update-spotify.py:52,73`, `bin/update-public-feeds.py` all `print(e.read().decode(...))` on token-exchange errors. Public GitHub Actions logs show these. OAuth providers sometimes echo the submitted `refresh_token` in `error_description` or `error_uri`. GitHub's secret masker only masks values registered as secrets — access tokens returned in response bodies are NOT registered.

## Proposed Solutions
Wrap token-exchange error printing with a sanitizer that strips `access_token`, `refresh_token`, `code`, `client_secret` values from any JSON response before logging. Or simpler: log only `e.code` + a generic message ("Token refresh failed with HTTP {code}") without the body.

## Acceptance Criteria
- [ ] No raw OAuth response bodies in CI logs; error logging sanitized or omitted.
