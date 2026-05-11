---
status: complete
priority: p2
issue_id: 138
tags: ['code-review', 'architecture', 'now-page', 'process']
dependencies: []
---

# Document marker bootstrap requirement in CLAUDE.md

## Problem Statement

The May 7–11 outage followed a predictable pattern: a commit introduced new cron behavior requiring new markers in `now/index.html`, but the markers were not seeded in that same commit. The cron correctly bailed (fail-safe worked), but no automated check caught the omission. The same failure mode applies to every future feed addition.

CLAUDE.md's "Adding a new data feed" checklist (step 1) says to add `FEED-START` / `FEED-END` markers — but it doesn't make explicit that the seeding must happen **in the same commit** as the script logic, and it doesn't mention section-level markers (ACTIVE-PROJECTS etc.) vs per-card markers (TLDR-{slug}).

**Surfaced by:** architecture-strategist during /ce:review 2026-05-11.

## Findings

- `CLAUDE.md` "Adding a new data feed" step 1: mentions adding markers to `now/index.html` but doesn't warn about the bootstrap timing requirement
- The auto-classify feature commit (`9fda3ca`) added script logic for `ACTIVE-PROJECTS` / `BACKBURNER-PROJECTS` without seeding the markers — the exact failure mode the checklist should prevent
- The existing test guard (todo 137) catches missing markers at CI time, but the checklist is a first-line defense

## Proposed Solutions

### Option A — Add explicit bootstrap note to CLAUDE.md checklist (recommended)

In the "Adding a new data feed" section, step 1, add:

> **Bootstrap requirement:** any new marker names introduced by the script must be seeded in `now/index.html` in the **same commit** that adds the script logic — never after. The cron's fail-safe (`replace_marker()` returning False) will silently preserve stale content indefinitely if markers are absent.

**Effort:** Small (one paragraph in CLAUDE.md)
**Risk:** None — documentation only.

### Option B — Also add a pre-commit hook check

Extend `.git/hooks/pre-commit` to grep `now/index.html` for any marker names referenced in `bin/update-*.py`. More automation, more fragile to maintain.

**Effort:** Medium
**Risk:** Low but adds hook complexity. Option A is sufficient given todo 137 adds CI coverage.

## Recommended Action

Option A. With CI now guarding markers (todo 137), the checklist note is a documentation improvement, not a safety critical fix.

## Acceptance Criteria

- [ ] CLAUDE.md "Adding a new data feed" step 1 contains explicit bootstrap timing warning
- [ ] Warning mentions both per-feed and section-level marker types

## Work Log

- 2026-05-11: Identified during /ce:review — architecture-strategist finding.
