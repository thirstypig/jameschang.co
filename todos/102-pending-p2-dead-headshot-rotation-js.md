---
status: pending
priority: p2
issue_id: 102
tags: ['code-review', 'javascript', 'dead-code']
dependencies: []
---

# Delete ~40 lines of dead headshot-rotation code in `script.js`

## Problem Statement
`script.js:36-76` runs a rotation loop bound to `.headshot-rotate`. That class does not exist in any HTML. The active homepage uses a static `<picture>` (`index.html:220-224`) — the rotation was retired with the notebook redesign cut-over (2026-04-27).

Selector returns null, loop exits cleanly via existing null guard, but the code is dead weight.

**Surfaced by:** performance-oracle during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Delete the rotation block
- Keep theme toggle + `beforeprint` listener (both live)
- **Effort:** Trivial

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] `.headshot-rotate` selector and rotation loop removed
- [ ] Theme toggle + beforeprint listener preserved
- [ ] No console errors on homepage

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
