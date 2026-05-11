---
status: complete
priority: p3
issue_id: 142
tags: ['code-review', 'ci', 'github-actions']
dependencies: []
---

# Upgrade actions in trakt-sync.yml.disabled

## Problem Statement

`.github/workflows/trakt-sync.yml.disabled` was not included in today's GitHub Actions version bump and still references `actions/checkout@v4`. If the workflow is re-enabled in the future (by renaming back to `.yml`), it will immediately generate Node.js 20 deprecation warnings and eventually fail when Node.js 20 is removed from runners (September 2026).

Trakt was disabled 2026-04-28 — the workflow is preserved for potential re-enable. The disabled extension means GitHub Actions doesn't execute it, but the file is still part of the repo and should stay current.

**Surfaced by:** security-sentinel during /ce:review 2026-05-11.

## Proposed Solutions

### Option A — Update the disabled workflow in place (recommended)

Apply the same bump: `actions/checkout@v4` → `@v6`. If the workflow also has `actions/setup-python`, bump that too.

**Effort:** Trivial
**Risk:** None — file is not executed while disabled.

### Option B — Delete the workflow

If Trakt is permanently dropped, delete the file rather than maintaining it. The auth scripts and tokens are already preserved separately.

**Effort:** Trivial
**Risk:** Loses the re-enable path. Decision for the repo owner.

## Recommended Action

Option A unless there's a decision to permanently drop Trakt.

## Acceptance Criteria

- [ ] `.github/workflows/trakt-sync.yml.disabled` uses `actions/checkout@v6` (and `setup-python@v6` if present)

## Work Log

- 2026-05-11: Identified during /ce:review — security-sentinel finding.
