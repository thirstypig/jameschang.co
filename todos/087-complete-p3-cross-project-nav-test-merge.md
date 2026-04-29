---
status: done
priority: p3
issue_id: 087
tags: ['code-review', 'testing', 'simplicity']
dependencies: []
---

# Merge the two cross-project-nav iteration tests into one for cleaner output

## Problem Statement
`TestCrossProjectNav::test_every_deep_dive_has_cross_project_nav` and `TestCrossProjectNav::test_cross_project_nav_links_to_canonical_entry_points` walk the same 12 pages with separate fetch loops. Merging into one test with two assert blocks saves ~12 LOC and produces a single failure message instead of two.

**Surfaced by:** code-simplicity-reviewer during /ce:review on 2026-04-28. Low priority — the duplication is minor.

## Proposed Solutions
### Option A: Merge into one test
Single loop that does both presence + href assertions per page.
- **Effort:** Tiny

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] Two tests merged; failure messages still informative

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
