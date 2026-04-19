---
status: done
priority: p1
issue_id: 064
tags: [code-review, security, content]
dependencies: []
---

# Privacy policy inaccurate — references removed GA4, missing CSP and referrer

## Problem Statement
`privacy/index.html` has three issues:
1. **Stale GA4 reference** (line 41): States "Google Analytics 4 may be used for anonymous traffic analytics" — GA4 was removed from the site on 2026-04-16 per CLAUDE.md. Privacy policies must accurately reflect data processing practices (GDPR).
2. **Missing CSP meta tag**: Every other HTML file has a Content-Security-Policy meta tag. The privacy page has none.
3. **Missing referrer meta tag**: Every other main page has `<meta name="referrer" content="strict-origin-when-cross-origin">`. The privacy page does not.

## Findings
- `privacy/index.html:41-43` — GA4 paragraph still present
- `privacy/index.html` — no `<meta http-equiv="Content-Security-Policy">` tag
- `privacy/index.html` — no `<meta name="referrer">` tag
- Flagged by Security Sentinel, Architecture Strategist, and Simplicity reviewer

## Proposed Solutions

### Option A: Fix all three in one pass (Recommended)
1. Remove or replace the GA4 paragraph with "No analytics or tracking scripts are installed."
2. Add the standard CSP meta tag matching other pages
3. Add the referrer meta tag
- **Effort:** Small
- **Risk:** None

## Acceptance Criteria
- [ ] No mention of Google Analytics 4 in privacy policy (or updated to reflect no-analytics reality)
- [ ] CSP meta tag present matching other pages
- [ ] Referrer meta tag present
- [ ] Content accurately reflects current data processing practices

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |
