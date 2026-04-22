---
status: done
priority: p2
issue_id: 068
tags: [code-review, documentation]
dependencies: []
---

# CLAUDE.md references nonexistent docs/plans/ + README.md out of date

## Problem Statement
Two documentation accuracy issues:

1. **CLAUDE.md phantom reference**: The agent-native conventions section says "Never delete files in `docs/plans/`, `docs/solutions/`, or `todos/` during review" — but `docs/plans/` does not exist. An agent following this instruction would encounter confusion.

2. **README.md significantly stale**: Describes a much older version of the site:
   - Says script.js is an "email-reveal click handler" (actually theme toggle + headshot rotator)
   - Says "Dark mode via prefers-color-scheme (no toggle)" (there IS a toggle)
   - Lists "Missing before launch" items long since resolved
   - Uses port 8000 vs CLAUDE.md's port 8787
   - Does not mention /now/, /work/, feed sync, or GitHub Actions

## Proposed Solutions

### Option A: Fix both (Recommended)
1. Remove `docs/plans/` from CLAUDE.md, or create the directory if it's planned
2. Update README.md to reflect the current site, or add a prominent note pointing to CLAUDE.md as the authoritative reference
- **Effort:** Small-Medium
- **Risk:** None

## Acceptance Criteria
- [ ] CLAUDE.md does not reference directories that don't exist
- [ ] README.md accurately describes the current project (or defers to CLAUDE.md)

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |
