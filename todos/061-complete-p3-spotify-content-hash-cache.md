---
status: pending
priority: p3
issue_id: 061
tags: [code-review, performance]
dependencies: []
---

# Spotify recently-played rewrites HTML every 4h even when tracks unchanged

## Problem
`bin/update-spotify.py` always fetches `recently-played?limit=5` and writes the resulting block into now/index.html, including an "Auto-updated" date line. Most 4-hour windows show the same 5 tracks (users don't rotate tracks that fast). The commit churn pollutes git history with no semantic change.

## Proposed Solutions
Add a `last_tracks_hash` field to `.spotify-state.json`. Compute SHA-1 of the rendered track list (not the date line). If unchanged, skip the HTML write — just update the podcast state if needed. Reduces ~50% of Spotify commits.

## Acceptance Criteria
- [ ] Commits for unchanged track lists eliminated; state file tracks the hash.
