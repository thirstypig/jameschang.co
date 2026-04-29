---
status: done
priority: p1
issue_id: 078
tags: ['code-review', 'agent-native', 'documentation']
dependencies: []
---

# CLAUDE.md "Adding a new project deep-dive" checklist missing cross-project nav step

## Problem Statement
The 2026-04-28 cross-project nav addition (commit 5f06bd8) wired all 12 existing deep-dive sub-pages with a `.cross-project-nav` block and an e2e test (`TestCrossProjectNav` in `tests/test_site_e2e.py`) that asserts presence + canonical entry-point hrefs + aria-current matching the slug.

But the "Adding a new project deep-dive" checklist in CLAUDE.md (lines 81–87) was written before cross-project nav existed. A 4th project added today would land without:
1. The new project being included in the cross-project nav of the 12 existing pages
2. The new project's own pages getting a cross-project nav block including the *new* slug

Either gap fails the e2e test, but with no documented hint of the fix.

**Surfaced by:** agent-native-reviewer during /ce:review on 2026-04-28.

**Files:**
- `CLAUDE.md` lines 81–87 (the checklist)
- `tests/test_site_e2e.py::TestCrossProjectNav` (the enforcer)

## Proposed Solutions
### Option A: Add steps 7+8 to the checklist (recommended)
Append to CLAUDE.md "Adding a new project deep-dive" checklist:
- Step 7: Add the new project to the `.cross-project-nav` block in **all existing deep-dive sub-pages**. Update the chip's href to the new project's canonical entry-point sub-page. The e2e test (`TestCrossProjectNav`) enforces presence + canonical hrefs + aria-current.
- Step 8: Update `tests/test_site_e2e.py::TestCrossProjectNav.EXPECTED_LINKS` to include the new slug. Update the assertion that there are 12 deep-dive pages (will become 12 + however many sub-pages the new project ships with).
- **Effort:** Tiny (5 minutes)
- **Risk:** None — pure documentation

### Option B: Generate the cross-project nav at build time
Defeats the static-only ethos. Skip.

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] CLAUDE.md "Adding a new project deep-dive" checklist includes the cross-project nav step
- [ ] CLAUDE.md mentions updating `EXPECTED_LINKS` in the e2e test

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
