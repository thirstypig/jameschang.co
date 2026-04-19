---
status: done
priority: p3
issue_id: 073
tags: [code-review, documentation, agent-native]
dependencies: []
---

# CLAUDE.md documentation gaps: work page template, screenshot workflow, feed instructions

## Problem Statement
Several gaps in CLAUDE.md that would cause an agent to get stuck or guess:

1. **No work page scaffolding guide**: Adding a new project deep-dive requires updating 5+ files (project-nav in siblings, /work/index.html, homepage #work grid, sitemap.xml, llms.txt). Only point 1 is mentioned.

2. **Screenshot workflow undocumented**: "Screenshot the change if it's CSS/layout" references a `/tmp/jc-shots/` pattern but never defines the Chrome command, viewport sizes, or theme handling.

3. **"Adding a new data feed" incomplete**: Missing CSS naming convention (.{feed}-module pattern), feeds-list tuple pattern in update-public-feeds.py, CSP implications for new external domains, staleness threshold consideration for non-daily feeds.

4. **Print stylesheet order map not listed**: Current order values (hero:0, about:1, experience:2, etc.) require reading CSS to discover.

5. **Feed sync script invocation assumption**: Scripts use `from _shared import ...` which only works when invoked as `python3 bin/script.py` (not as a module import).

## Proposed Solutions

### Option A: Incrementally expand CLAUDE.md
Add sections for each gap as they become relevant.
- **Effort:** Medium (spread over time)
- **Risk:** None

## Acceptance Criteria
- [ ] "Adding a new project deep-dive" checklist in CLAUDE.md
- [ ] Screenshot workflow documented or scripted
- [ ] Feed instructions expanded with CSS convention, CSP note, and staleness threshold
- [ ] Print order map documented

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |
