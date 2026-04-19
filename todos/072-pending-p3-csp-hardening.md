---
status: done
priority: p3
issue_id: 072
tags: [code-review, security]
dependencies: []
---

# CSP hardening: add object-src 'none' + hitlist URL protocol validation

## Problem Statement
Two defense-in-depth improvements:

1. **Missing `object-src`** in all CSP headers: Falls back to `default-src 'self'`, allowing `<object>`/`<embed>` from same origin. Should be explicitly `'none'` per CSP best practices.

2. **Hitlist URL protocol validation** (`now/index.html:419-420`): If `thirstypig.com/places-hitlist.json` were compromised, a `javascript:` URL in the links could execute script. Add protocol check: `if (!/^https?:\/\//i.test(url)) return;`

## Proposed Solutions

### Option A: Fix both in one pass
1. Add `object-src 'none';` to all CSP meta tags
2. Add URL protocol check in hitlist renderer
- **Effort:** Small
- **Risk:** None

## Acceptance Criteria
- [ ] All CSP meta tags include `object-src 'none'`
- [ ] Hitlist renderer validates URL protocol before setting href

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |
