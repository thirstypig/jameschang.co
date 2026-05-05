---
status: complete
priority: p3
issue_id: 136
tags: ['code-review', 'performance', 'security', 'cross-repo-admin']
dependencies: []
---

# Pages CDN cache window + Google Maps SDK pinning

## Problem Statement
Two unrelated small items worth one sweep:

1. **Pages CDN serves stale up to 10 minutes despite `cache: 'no-cache'`.** `bucketlist/bucketlist.js:77` and `now/now.js` use `cache: 'no-cache'` (force-revalidate) when fetching `/bucketlist.json`. But GitHub Pages responds with `Cache-Control: max-age=600`, so the browser obeys the response and the user can see stale data for ~10 minutes after a save lands. **`cache: 'reload'`** forces a network fetch every time. Or just document the behavior.

2. **Google Maps SDK pinned to `v=weekly` channel without SRI.** `HitListManager.tsx:33` loads `https://maps.googleapis.com/maps/api/js?key=...&v=weekly`. The `weekly` channel is a moving target — Google can ship breaking changes or, theoretically, a compromised CDN response could inject script in the same origin as the PAT. SRI hashes aren't published by Google for this script (it's served dynamically), so SRI isn't directly available. But pinning to a specific quarterly version (`v=3.62`) at least narrows the attack window.

**Surfaced by:** architecture-strategist (cache) and security-sentinel (SDK pinning) during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Tighten both (recommended)
- `bucketlist.js` and `now.js`: change `cache: 'no-cache'` → `cache: 'reload'`. Forces network fetch every page load. Trade-off: extra round-trip on every visit, but bucketlist.json is ~1KB so negligible.
- `HitListManager.tsx:33`: pin SDK version: `v=3.62` (or whatever the current quarterly is at fix time). Document the upgrade cadence as "review SDK pin twice yearly" in CLAUDE.md.

**Effort:** Small (~15 min)
**Risk:** Pinning Google Maps to an old version risks Places API behavior drift; check release notes before pinning.

### Option B — Document the cache window, leave SDK alone
Add a note to `docs/bucketlist-admin-spec.md` that "saves are visible within ~10 min due to Pages CDN max-age=600". Defer SDK pinning to admin-CSP audit (todo 129).

## Acceptance Criteria
- [ ] `bucketlist.js` and `now.js` use `cache: 'reload'` OR cache window is documented
- [ ] Google Maps SDK pinned to a numbered version OR explicitly tracked in todo 129
- [ ] Spec doc reflects the chosen behavior

## Resources
- `bucketlist/bucketlist.js:77`
- `now/now.js` (bucket list IIFE fetch)
- `HitListManager.tsx:33`
