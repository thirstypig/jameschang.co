---
status: pending
priority: p1
issue_id: 090
tags: ['code-review', 'performance', 'sync-pipeline']
dependencies: []
---

# Sync scripts produce timestamp-only commits, defeating `content_changed()`

## Problem Statement
`relative_time_html()` (added 2026-04-23) emits `<time data-rel>` elements whose text changes every minute ("16h ago" → "17h ago"). The cron sync scripts hash the rendered HTML for the no-op short-circuit, so even when no upstream content changed, the hash differs every run → `content_changed()` always returns true → `git add now/index.html && commit && push` fires.

Result: Spotify pushes 48 timestamp-only commits/day. Likely affects `update-public-feeds.py`, `update-plex.py`, `update-whoop.py` too. Wasted CI minutes and noisy `git log` that obscures real edits.

The client-side upgrader at `now/now.js:102` reformats `data-rel` text every 60s anyway — server-rendered text is just initial seed.

**Surfaced by:** performance-oracle during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Hash on upstream payload identifiers
- Build the content-hash from upstream API response (track IDs + episode ID for Spotify; recovery score + sleep ID for WHOOP; etc.) instead of rendered HTML
- `replace_marker()` only runs if the upstream changed
- The `<time data-rel>` elements stay correct because client JS reformats every 60s
- **Effort:** Medium (~1-2h, four scripts to audit)

### Option B: Strip `<time data-rel>` and `feed-updated` text from the hash input only
- Less invasive: keep current hash but normalize away time-volatile substrings before hashing
- Brittle (regex over rendered HTML)
- **Effort:** Small but fragile

## Recommended Action
_(Filled during triage)_

## Technical Details
- `bin/update-spotify.py:225` — primary offender (every 30 min)
- `bin/update-public-feeds.py`, `bin/update-plex.py`, `bin/update-whoop.py` — audit for same anti-pattern
- `bin/_shared.py::content_changed` — current hash function
- `bin/_shared.py::relative_time_html` — emits time-volatile markup

## Acceptance Criteria
- [ ] Spotify cron commits only when upstream tracks/episode change
- [ ] Same fix applied to public-feeds, plex, whoop sync scripts
- [ ] `<time data-rel>` text still reformats client-side (verify in browser)
- [ ] No regression in heartbeat recording (success path still records)

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |

## Resources
- now/now.js:102 — client-side reformatter (canonical upgrader)
