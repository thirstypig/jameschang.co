---
status: complete
priority: p3
issue_id: 118
tags: ['code-review', 'seo', 'sitemap']
dependencies: []
---

# `sitemap.xml` `lastmod` stuck at `2026-04-27` for every URL

## Problem Statement
`sitemap.xml` has uniform `lastmod=2026-04-27` despite multiple post-cutover changes (resume pipeline, /now feeds, project shipping lists). Crawlers may underweight the site.

**Surfaced by:** pattern-recognition-specialist during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Manual bump on substantive HTML changes
- Add to commit checklist
- **Effort:** Process change

### Option B: Pre-commit hook generates from `git log -1 --format=%cs <file>`
- Automatic; never drifts
- Tiny script
- **Effort:** Small (~30 min)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] `sitemap.xml` `lastmod` reflects each URL's actual most recent content edit
- [ ] If automated: hook runs in pre-commit dance and is documented in CLAUDE.md

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
