---
status: done
priority: p2
issue_id: 079
tags: ['code-review', 'seo', 'pattern']
dependencies: []
---

# Privacy page lacks JSON-LD; either add WebPage schema or document the exception

## Problem Statement
Every other content page on the site has a JSON-LD `<script type="application/ld+json">` block. `privacy/index.html` has zero. If the omission is intentional (privacy policies arguably don't need indexing schema), the exception isn't documented anywhere — a future contributor running visual parity could add it back inconsistently.

**Surfaced by:** pattern-recognition-specialist during /ce:review on 2026-04-28.

**Files:**
- `privacy/index.html` (currently no JSON-LD block)
- `tests/test_site_e2e.py::TestJsonLD` (currently doesn't require it; doesn't exempt either)

## Proposed Solutions
### Option A: Add a minimal `WebPage` schema (recommended)
Mirror the `/now/` page's JSON-LD block — `@type: WebPage`, name, description, dateModified, isPartOf the WebSite. Tiny addition, removes the inconsistency.
- **Effort:** Tiny

### Option B: Document the exception in CLAUDE.md
Add a sentence: "Privacy policy intentionally has no JSON-LD — Google's structured-data tooling doesn't index privacy pages and the schema would be noise." Update `tests/test_site_e2e.py::TestJsonLD` to exempt privacy.
- **Effort:** Tiny

Either is acceptable. Option A is more consistent with the rest of the site.

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] Privacy page has a JSON-LD block (Option A) OR exception is documented (Option B)
- [ ] e2e tests still pass

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
