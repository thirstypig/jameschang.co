---
status: complete
priority: p3
issue_id: 141
tags: ['code-review', 'ci', 'github-actions']
dependencies: []
---

# Add setup-python to 4 workflows relying on ambient Python

## Problem Statement

Four workflows (`whoop-sync.yml`, `plex-sync.yml`, `spotify-sync.yml`, `public-feeds-sync.yml`) run Python scripts without an explicit `actions/setup-python` step — they rely on `ubuntu-latest`'s default Python installation. The other 4 workflows that use `setup-python` all pin `python-version: '3.12'` explicitly.

`ubuntu-latest` currently ships Python 3.12, but this is not guaranteed across runner image updates. An image bump could silently change the Python version and break the sync scripts.

Not introduced today — pre-existing inconsistency made more visible by today's version bump of the 4 workflows that already had `setup-python`.

**Surfaced by:** architecture-strategist during /ce:review 2026-05-11.

## Proposed Solutions

### Option A — Add setup-python to all 4 (recommended)

After the `actions/checkout@v6` step in each of the 4 workflows, add:

```yaml
- uses: actions/setup-python@v6
  with:
    python-version: '3.12'
```

**Effort:** Small (4 files, 3 lines each)
**Risk:** Minimal — adds an explicit step that matches current ambient behavior.

### Option B — Leave as-is and accept the ambient dependency

`ubuntu-latest` has been on Python 3.12 for over a year. Low probability of breakage in practice.

**Effort:** None
**Risk:** Low but non-zero.

## Recommended Action

Option A. Brings all 8 workflows to parity, removes ambient dependency.

## Acceptance Criteria

- [ ] All 8 active workflows use `actions/setup-python@v6` with `python-version: '3.12'`
- [ ] Workflows still pass on GitHub Actions

## Work Log

- 2026-05-11: Identified during /ce:review — architecture-strategist finding.
