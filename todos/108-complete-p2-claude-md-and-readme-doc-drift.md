---
status: complete
priority: p2
issue_id: 108
tags: ['code-review', 'documentation', 'agent-native']
dependencies: []
---

# CLAUDE.md and README.md drift from current repo state

## Problem Statement
Multiple doc-drift findings discovered cold by review agents — these block agent-native reproducibility:

1. **CLAUDE.md "Repo layout" tree** is incomplete: missing `update-plex.py`, `update-trakt.py`, `update-projects.py`, `trakt-auth.sh`, `trakt-encrypt.sh`, `check-feed-health.py`, `projects-config.json`, `/spotify/callback/`. Only `/whoop/callback/` is listed.
2. **CLAUDE.md** still mentions `styles.css` as "kept temporarily only as a reference" — file no longer exists in repo.
3. **CLAUDE.md "Project TLDRs"** claims `TLDR_FETCH_TOKEN` covers 4 private repos. `bin/projects-config.json` enumerates 7 projects across many more shipping repos. PAT scope guidance is stale.
4. **CLAUDE.md "Testing" table** says `tests/test_projects.py` has 19 tests; actual count is 23. Total 183 still matches but per-row attribution is wrong.
5. **README.md:44** says "176 tests"; actual is 183.
6. **`bin/update-spotify.py:4`** docstring says "4-hour cron"; workflow + CLAUDE.md agree on 30 min.
7. **`bin/update-public-feeds.py:9-11`** docstring still lists Letterboxd as active.
8. **`now/index.html:209`** prose still mentions Trakt/Letterboxd as live data sources (dropped 2026-04-28).

**Surfaced by:** architecture-strategist + agent-native-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Run `/doc` slash command after a code-state snapshot
- The `/doc` skill exists for exactly this. Run it after the P1+P2 code fixes, then resync docs.
- **Effort:** Small if all-at-once; defer until after code changes

### Option B: Fix each drift inline as separate small commits
- More history granularity but more thrashing
- **Effort:** Small per item

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] CLAUDE.md repo layout reflects actual `bin/` and root contents
- [ ] CLAUDE.md drops `styles.css` reference
- [ ] CLAUDE.md "Project TLDRs" lists all repos requiring Contents:Read
- [ ] CLAUDE.md test table per-row counts match `pytest --collect-only -q`
- [ ] README.md test count matches reality
- [ ] update-spotify.py + update-public-feeds.py docstrings current
- [ ] now/index.html prose reflects current feed list

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
