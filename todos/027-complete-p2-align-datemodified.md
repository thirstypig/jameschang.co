---
status: done
priority: p2
issue_id: 027
tags: [code-review, schema, consistency]
dependencies: [020]
---

# JSON-LD `dateModified` disagrees with visible "Last updated" on /work/ deep-dives

## Problem

Each /work/ deep-dive page has:
- Visible `<p class="page-updated">Last updated <time datetime="2026-04-15">` (refreshed by sync script)
- JSON-LD `dateModified: "2026-04-14"` (set once at creation, never updated)

By one day apart. Agents comparing site freshness across sources see the inconsistency.

## Proposed Solutions

### Option A: Drop the visible "Last updated" markers (aligns with todo #020 cutting sync pipeline)
If the sync pipeline goes, the markers go, and JSON-LD `dateModified` becomes the single source of truth.

### Option B (Recommended if keeping some timestamp): Compute `dateModified` from git log at deploy time
Add a tiny build step (pre-push hook or Action) that rewrites all `dateModified` fields based on `git log -1 --format=%ad --date=short FILE`. Consistent, automatic, no regex brittleness.

### Option C: Leave it
One-day drift; no one will notice except machines.

## Dependencies

Resolution depends on todo #020 outcome:
- If #020 cuts sync → this becomes Option A (drop visible markers, keep JSON-LD)
- If #020 keeps sync → either fix sync-work.py to also patch JSON-LD, or adopt Option B

## Acceptance Criteria
- [ ] Single source of truth for "when was this page updated"
- [ ] Visible timestamp and schema timestamp match (if both exist)

## Resources
- pattern-recognition review 2026-04-15, M4
