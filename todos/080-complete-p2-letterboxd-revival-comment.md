---
status: done
priority: p2
issue_id: 080
tags: ['code-review', 'agent-native', 'documentation']
dependencies: []
---

# Add re-enable hint comment for Letterboxd in update-public-feeds.py

## Problem Statement
`bin/update-public-feeds.py` had its `LETTERBOXD` entry removed from the `feeds[]` list on 2026-04-28 (cede613). The `letterboxd_block()` function itself (lines 129–170) was preserved for re-enable. But a future agent reviving Letterboxd won't know which marker name to re-add to `now/index.html` or which feed-list tuple shape to use.

Trakt has a similar pattern (workflow renamed `.yml` → `.yml.disabled`) but the trakt revival path *is* documented in CLAUDE.md.

**Surfaced by:** agent-native-reviewer during /ce:review on 2026-04-28.

**Files:**
- `bin/update-public-feeds.py` line 326 (the feeds[] list in main())
- Possibly `bin/update-trakt.py` and `.github/workflows/trakt-sync.yml.disabled` for symmetry

## Proposed Solutions
### Option A: One-line code comment near feeds[] (recommended)
Add a comment above the feeds[] list: `# Letterboxd disabled 2026-04-28 — to revive: add ("LETTERBOXD", letterboxd_block, '<fallback html>') here AND restore <!-- LETTERBOXD-START/END --> markers in now/index.html /07 section.`
- **Effort:** Tiny

### Option B: Delete letterboxd_block() entirely
Cleaner — the function can be reconstructed from git history if needed. But removes a hint about the data shape and CSP/CORS already-established for letterboxd.com.

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] Comment added to update-public-feeds.py near feeds[]
- [ ] (Optional) Mirror comment in trakt files

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
