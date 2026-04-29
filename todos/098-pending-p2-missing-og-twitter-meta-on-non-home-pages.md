---
status: pending
priority: p2
issue_id: 098
tags: ['code-review', 'seo', 'social-share']
dependencies: []
---

# 16 of 17 content pages missing Open Graph + Twitter card meta

## Problem Statement
Only `/index.html` carries `og:title` / `og:image` / `og:description` and Twitter card meta. Every project deep-dive (12 pages), `/now/`, `/projects/`, and `/privacy/` will render as a blank link card with no preview when shared on LinkedIn / Twitter / Slack / iMessage.

CLAUDE.md implies "all pages share the same head boilerplate" — this is drift from that contract.

Same pattern for `apple-touch-icon`: only declared on `/index.html`. Other 15 pages fall back to a screenshot when pinned to iOS home screen (asset already exists at `/assets/apple-touch-icon.png`).

**Surfaced by:** pattern-recognition-specialist during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Add per-page OG/Twitter quartet + apple-touch-icon to each non-callback page
- Per-page `og:title`, `og:description`, `og:url`, `og:type` + `twitter:card`
- Reuse `og:image` `/assets/og-image.*` as the default
- Add `<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">` to each non-home content page
- **Effort:** Medium (~1-2h, 16 files; mostly templated)

### Option B: Add a `tests/test_site_e2e.py` parity assertion
- After fix, lock the contract so future pages don't drift again
- **Effort:** Small (~15 min)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] Every non-callback HTML page has og:title / og:description / og:image / og:url / twitter:card
- [ ] Every non-home content page has apple-touch-icon link
- [ ] E2E test asserts presence on all standard pages
- [ ] Validate one URL with the Twitter Card validator + LinkedIn Post Inspector

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
