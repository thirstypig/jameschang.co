---
status: complete
priority: p3
issue_id: 117
tags: ['code-review', 'seo', 'jsonld']
dependencies: []
---

# `aleph/how-it-works/` JSON-LD `@type` is `Article`; siblings use `TechArticle`

## Problem Statement
`projects/aleph/how-it-works/index.html` declares `@type: Article` in JSON-LD; sibling deep-dive pages `fantastic-leagues/tech/` and `judge-tool/tech/` use `TechArticle` for the same role ("how the product is built"). Pick one; current state confuses crawler categorization.

**Surfaced by:** pattern-recognition-specialist during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Promote Aleph to `TechArticle`
- Aligns with the other two
- **Effort:** Trivial

### Option B: Demote the other two to `Article`
- Less specific schema; not preferred
- **Effort:** Trivial

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] All 3 deep-dive landing pages use the same JSON-LD `@type`

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
