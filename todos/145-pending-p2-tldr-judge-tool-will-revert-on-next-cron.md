---
status: pending
priority: p2
issue_id: "145"
tags: [code-review, content, cron, branding]
dependencies: []
---

## Problem Statement
The `<!-- TLDR-judge-tool-START/END -->` block in `now/index.html` was manually updated to use "Barbeque" instead of "KCBS-style BBQ". However, this block is rewritten on every daily run of `bin/update-projects.py` (7 AM PT, `projects-sync.yml`) from the Judge Tool repo's `CLAUDE.md` `<!-- now-tldr -->...<!-- /now-tldr -->` block. The manual fix will be silently reverted within 24 hours.

## Findings
- **File:** `now/index.html` lines 220–227 (inside `<!-- TLDR-judge-tool-START/END -->`)
- **Root cause:** Source of truth is the Judge Tool repo's `CLAUDE.md`, not this repo
- **Risk:** Next cron run at 7 AM PT will overwrite "Barbeque" with whatever spelling is in the Judge Tool CLAUDE.md
- **Caught by:** Pattern recognition agent + security sentinel during /ce:review on 2026-05-13

## Proposed Solution
Update the `<!-- now-tldr -->...<!-- /now-tldr -->` block in the **Judge Tool repo's** `CLAUDE.md` to:
- Replace "KCBS-style BBQ" → "Barbeque"
- Replace "KCBS-sanctioned competition" → "sanctioned competition"

This is a cross-repo change and cannot be done from this repo.

## Acceptance Criteria
- [ ] Judge Tool repo CLAUDE.md `<!-- now-tldr -->` block uses "Barbeque" spelling
- [ ] Next `projects-sync` cron run preserves "Barbeque" in `now/index.html`

## Work Log
- 2026-05-13: Identified during /ce:review. Cross-repo fix required (Judge Tool CLAUDE.md).
