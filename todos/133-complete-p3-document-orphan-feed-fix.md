---
status: pending
priority: p3
issue_id: 133
tags: ['code-review', 'documentation', 'compound-engineering']
dependencies: []
---

# Document the orphan feed-stale fix + marker-boundary lesson

## Problem Statement
This session shipped two related fixes that share an underlying lesson but neither is captured in `docs/solutions/`:

1. **Orphan feed-stale issue cleanup** (`bin/check-feed-health.py` change in commit `248afd2`) — the script iterated `data.items()` from the heartbeat file, so a slug missing from the heartbeat was never visited and any open issue for that retired slug sat OPEN forever. Fix: second loop closes orphans.

2. **WHOOP eyebrow date freeze** (commit `454c4f4`) — a hardcoded date string OUTSIDE the `<!-- WHOOP-START -->`/`<!-- WHOOP-END -->` markers had been frozen since April 27 because `replace_marker()` only touches content between markers.

Both share the lesson: **anything outside a marker block is structurally invisible to the corresponding sync mechanism.** That's correct by design but easy to forget when adding static content near a feed block. Easy to repeat if not documented.

The existing `docs/solutions/integration-issues/relative-time-html-defeats-content-changed-cache.md` covers a related class (relative-time text defeating `content_changed()`) but doesn't generalize the marker-boundary lesson.

**Surfaced by:** learnings-researcher during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — One solution doc + a CLAUDE.md note (recommended)
Create `docs/solutions/integration-issues/marker-boundary-content-staleness.md` that:
- Explains the marker-replacement contract used by all sync scripts
- Catalogs the two incidents (WHOOP eyebrow + github feed-stale orphan)
- Generalizes: "any text dependent on a sync mechanism must live INSIDE the marker block, or be reachable by an explicit code path that owns it"
- Cross-links the relative-time solution doc

Add a one-line note to `CLAUDE.md`'s "Data feeds on /now" section:
> **Marker boundaries.** `replace_marker()` only writes between `<!-- {FEED}-START -->` and `<!-- {FEED}-END -->`. Date strings or status indicators OUTSIDE markers are never updated by the sync — they freeze on their last hand-edit. See `docs/solutions/integration-issues/marker-boundary-content-staleness.md`.

**Effort:** Small (~30 min)
**Risk:** None — documentation only.

### Option B — Skip
Both fixes are committed; the next time someone runs `git blame` they'll see the commits. But a doc compounds; commits don't.

## Acceptance Criteria
- [ ] New solution doc exists with both incidents catalogued
- [ ] `CLAUDE.md` has the one-line cross-reference
- [ ] Existing relative-time solution doc cross-links to the new one

## Resources
- Commits `454c4f4` (WHOOP eyebrow) and `248afd2` (orphan cleanup)
- `docs/solutions/integration-issues/relative-time-html-defeats-content-changed-cache.md`
- `bin/check-feed-health.py:135-187`
- `bin/_shared.py` (where `replace_marker()` lives)
