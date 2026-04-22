---
status: done
priority: p1
issue_id: 044
tags: [code-review, security]
dependencies: []
---

# Refresh tokens printed to stdout during auth script setup

## Problem
`bin/whoop-auth.sh` and `bin/spotify-auth.sh` print the full token JSON response (containing access_token + refresh_token) to stdout, then again print `WHOOP_REFRESH_TOKEN = <token>` / `SPOTIFY_REFRESH_TOKEN = <token>` in cleartext. Tokens persist in shell scrollback, Terminal session logs, and any screen recording/share during setup. Spotify refresh tokens don't rotate — a single leak compromises the integration until the app is rotated in the Spotify developer dashboard.

## Proposed Solutions
(a) Don't print the raw JSON response — parse and print only success/failure. (b) Write the refresh token to a tempfile with mode 600 via `mktemp` + `printf %s`, tell user to cat it, then `shred`/`rm`. Alternatively, gate the token echo behind a `--show` flag.

## Acceptance Criteria
- [ ] No token values echoed to stdout unless user explicitly passes `--show`
- [ ] Tempfile pattern documented in the script
