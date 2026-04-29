---
status: discarded
priority: p2
issue_id: 110
tags: ['code-review', 'documentation', 'now-feeds', 'false-positive']
dependencies: []
---

# Goodreads has only one marker block but docs claim two (currently-reading + read)

**Discarded 2026-04-29 — false positive.** Both markers exist in `now/index.html`:
`<!-- GOODREADS-READING-START -->` at line 420 (currently reading) and
`<!-- GOODREADS-START -->` at line 427 (recently read). Both are wired up
in `bin/update-public-feeds.py:335-336` and rendering correctly. Docs match
reality. The agent-native reviewer missed the second marker pair on its scan.

## Problem Statement (original — invalid)
`now/index.html` has only `GOODREADS-READING-START/END` (line 420/426). No second `GOODREADS-READ` marker pair. CLAUDE.md, README.md, and `bin/update-public-feeds.py:335` registration all claim two shelves (currently-reading + read).

**Surfaced by:** agent-native-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Add the second marker block + builder hook
- `<!-- GOODREADS-READ-START -->...<!-- GOODREADS-READ-END -->` in `now/index.html`
- Wire up the matching shelf fetch in `update-public-feeds.py`
- Update `tests/test_site_e2e.py::EXPECTED_MARKERS`
- **Effort:** Small (~30 min)

### Option B: Drop the "+ read" claim from docs
- If James only wants currently-reading, simpler to align docs to reality
- Update CLAUDE.md, README.md, and the script's feed registration
- **Effort:** Trivial

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] Code and docs agree on Goodreads shelf coverage
- [ ] `EXPECTED_MARKERS` matches reality

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
