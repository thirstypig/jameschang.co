---
status: pending
priority: p1
issue_id: 094
tags: ['code-review', 'agent-native', 'tooling']
dependencies: []
---

# `check-feed-health.py` has no dry-run; running it locally creates real GitHub issues

## Problem Statement
`bin/check-feed-health.py` calls `gh issue create / close / comment` unconditionally. There's no `--dry-run`, no `DRY_RUN=1` env, no warning in CLAUDE.md. An agent (or human) running it locally to verify behavior will open or close real issues against the live repo — destructive by default, with no preview path.

**Surfaced by:** agent-native-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: `DRY_RUN=1` env var guard
- Wrap each `gh issue create/close/comment` call with `if os.environ.get("DRY_RUN"): print(...); return`
- Document in script docstring + CLAUDE.md "Local preview" section
- **Effort:** Small (~20 min)

### Option B: Argparse `--dry-run` flag
- More discoverable but adds a dep on argparse import; env var is consistent with other scripts that read env at module load
- **Effort:** Small

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] `DRY_RUN=1 python3 bin/check-feed-health.py` performs no `gh` writes
- [ ] Stdout shows what would have been created/closed/commented
- [ ] Documented in CLAUDE.md and the script's docstring

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
