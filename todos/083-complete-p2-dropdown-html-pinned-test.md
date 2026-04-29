---
status: done
priority: p2
issue_id: 083
tags: ['code-review', 'testing']
dependencies: []
---

# Add e2e test pinning the projects dropdown menu HTML across all 16 pages

## Problem Statement
The `[projects ▾]` dropdown menu inner-HTML is identical across all 16 pages today (verified). No test pins it. A single-file edit could drift the menu items (e.g., reordering, dropping a project) without any test failing.

**Surfaced by:** pattern-recognition-specialist during /ce:review on 2026-04-28.

## Proposed Solutions
### Option A: Hash + parity assertion
Hash the `<div class="nb-dropdown" role="menu">…</div>` block on each page; assert all 16 hashes match.
- **Effort:** Small

Naturally this complements `TestCrossProjectNav` (which checks deep-dive cross-project nav, a different surface).

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] Test asserts dropdown menu HTML parity across all 16 pages

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
