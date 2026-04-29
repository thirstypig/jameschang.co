---
status: done
priority: p2
issue_id: 081
tags: ['code-review', 'css', 'pattern']
dependencies: []
---

# Reduce inline-style usage on deep-dive pages

## Problem Statement
Three deep-dive pages have a notable cluster of inline styles that could be classes:

- `/projects/aleph/roadmap/index.html`: 6 inline `style="color: var(--accent)"` / `style="color: var(--muted)"` / `style="opacity: 0.7"` on `<em>` tags marking priority. These are semantically `priority-high`, `priority-medium`, `priority-low` — should be three classes in `projects/projects.css`.
- `/projects/fantastic-leagues/tech/index.html`: line ~182 has `style="columns: 2; column-gap: 2rem; …"` (3 properties on a list block). Belongs as `.tech-column-block` or similar.
- `/projects/fantastic-leagues/dashboard/index.html`: line 157 hardcoded `<strong style="color:#D55E00">red</strong>` etc. — three Wong/colorblind-friendly priority colors using literal hex values, bypassing the design-token system.

Data-driven `style="width: Npx"` on `.t-bar` chart bars is defensible (the value is a number, not a category) but could use CSS custom properties: `style="--t-bar: 155px"` + a single `.t-bar { width: var(--t-bar); }` rule.

**Surfaced by:** pattern-recognition-specialist + simplicity reviewer during /ce:review on 2026-04-28.

## Proposed Solutions
### Option A: Add three `.priority-*` classes + one `.tech-column-block` class
- `.priority-high { color: var(--accent); font-style: italic; }`
- `.priority-medium { color: var(--muted); font-style: italic; }`
- `.priority-low { color: var(--muted); font-style: italic; opacity: 0.7; }`
- `.tech-column-block` for the 3-prop multi-column treatment
- For the dashboard hex colors, decide if they should remain literal (Wong palette is colorblind-deliberate) or move into CSS custom properties for theme parity.
- **Effort:** Small (~30 minutes)

### Option B: Leave as-is and add a test cap
Test that asserts max-N inline `style=` per page. Catches future leakage but doesn't fix existing.

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] Priority classes defined in projects.css and applied to roadmap pages
- [ ] Multi-column block extracted (FL tech)
- [ ] Dashboard priority colors decided (literal hex vs tokens)
- [ ] Optional: `.t-bar` migrated to CSS custom property pattern

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
