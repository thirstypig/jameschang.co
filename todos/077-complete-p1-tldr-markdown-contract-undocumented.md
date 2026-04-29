---
status: done
priority: p1
issue_id: 077
tags: ['code-review', 'agent-native', 'documentation']
dependencies: []
---

# Document the supported markdown subset for project TLDR sync

## Problem Statement
`bin/update-projects.py::_render_markdown_inline` (added 2026-04-28) supports only `**bold**` and `` `code` `` — not italics, links, lists, or any other markdown syntax. Authors of the *other* repos' CLAUDE.md `<!-- now-tldr -->` blocks (Aleph, Fantastic Leagues, Thirsty Pig, etc.) have no way to know this. Anything else they write — `_italic_`, `[links](…)`, lists — silently renders as literal text on the live /now page.

**Surfaced by:** agent-native-reviewer during /ce:review on 2026-04-28.

**Files:**
- `bin/update-projects.py` lines 88–103 (`_render_markdown_inline`)
- `CLAUDE.md` line 100 (the per-project TLDR sync paragraph) — natural place to document the contract
- Each downstream project's `CLAUDE.md` `<!-- now-tldr -->` block (e.g. `/Users/jameschang/Projects/alephco.io/alephco.io-app/CLAUDE.md`) — authors land here and need the contract visible

## Proposed Solutions
### Option A: One-liner in CLAUDE.md TLDR section (recommended)
Add to CLAUDE.md line 100 after the existing description: "**Markdown contract:** the now-tldr block supports `**bold**` and `` `code` `` only — other syntax (italics, links, lists) renders literally. HTML entities are escaped, so `<TagName>`-style references are safe."
- **Effort:** Tiny (1 minute)
- **Risk:** None

### Option B: Mirror the contract into each project's CLAUDE.md
Per-repo redundancy, but ensures discoverability where authors actually edit. Could be a `<!-- now-tldr -->` block comment.
- **Effort:** Small (one comment per repo, 7 repos)

### Option C: Expand the rendering to support full markdown
Add a real markdown renderer (`markdown-it` etc). Defeats the "Python-only, zero deps" project ethos.

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] CLAUDE.md TLDR section documents the supported markdown subset
- [ ] (Optional) Per-repo CLAUDE.md `<!-- now-tldr -->` block has a sibling comment with the contract

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
