---
status: done
priority: p3
issue_id: 088
tags: ['code-review', 'css']
dependencies: []
---

# Migrate data-driven `.t-bar` widths to CSS custom properties

## Problem Statement
The sprint-burndown / changelog-stats charts on FL/analytics, FL/tech, judge-tool/changelog use `<span class="t-bar" style="width: 155px">` patterns repeatedly. Each is a data-driven width — defensible inline — but cleaner as `style="--t-bar: 155px"` with a single `.t-bar { width: var(--t-bar); }` rule. Lets the design system control the chart bar's *other* properties (height, color, transition) without each `.t-bar` instance inheriting inline-overridable styles.

**Surfaced by:** pattern-recognition-specialist during /ce:review on 2026-04-28.

## Proposed Solutions
### Option A: Refactor to custom property
- Replace `style="width: Npx"` → `style="--t-bar: Npx"` across all charts
- Add `.t-bar { width: var(--t-bar); }` to projects.css
- **Effort:** Small (~30 minutes; mostly find/replace)

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] All `.t-bar` instances use custom property pattern
- [ ] CSS rule reads `width: var(--t-bar)`

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
