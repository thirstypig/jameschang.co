---
status: done
priority: p2
issue_id: 084
tags: ['code-review', 'testing']
dependencies: []
---

# Assert deep-dive block ordering: project-nav → snapshot-banner → work-hero

## Problem Statement
On the 10 non-dashboard deep-dive pages, the structural order is `project-nav` (line ~85) → `snapshot-banner` (~93–95) → `work-hero` (~99–102). This is consistent today but no test asserts the order. A future page edit could re-order without breaking any current test.

**Surfaced by:** pattern-recognition-specialist during /ce:review on 2026-04-28.

## Proposed Solutions
### Option A: Assert document-order of three selectors per deep-dive
For each deep-dive page (excluding the 2 dashboard pages which intentionally lack snapshot-banner), assert `indexOf("class=\"project-nav\"")` < `indexOf("class=\"snapshot-banner\"")` < `indexOf("class=\"work-hero\"")`.
- **Effort:** Small

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] Test added; correctly exempts dashboard pages

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
