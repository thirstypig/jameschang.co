---
status: done
priority: p3
issue_id: 085
tags: ['code-review', 'security', 'documentation']
dependencies: []
---

# Add code comments warning that re-enabling Trakt/Letterboxd requires updating privacy disclosure

## Problem Statement
Trakt + Letterboxd disclosures were removed from `privacy/index.html` on 2026-04-28 because the integrations no longer surface data on /now. But the workflow file (`.github/workflows/trakt-sync.yml.disabled`) and the function (`letterboxd_block` in `update-public-feeds.py`) are preserved for re-enable. A future re-enable that doesn't restore the disclosure would be a privacy gap (silent re-introduction of a third-party data source).

**Surfaced by:** security-sentinel during /ce:review on 2026-04-28.

## Proposed Solutions
### Option A: Comment at each revival point
Add a top-of-file comment to `bin/update-trakt.py` and a comment near `letterboxd_block` in `update-public-feeds.py`: "Re-enabling requires restoring privacy/index.html disclosure — see commit cede613 + 2026-04-28 doc sweep."
- **Effort:** Tiny

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] Comments added at each revival point

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
