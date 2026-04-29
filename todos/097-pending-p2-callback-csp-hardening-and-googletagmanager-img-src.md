---
status: pending
priority: p2
issue_id: 097
tags: ['code-review', 'security', 'csp', 'oauth']
dependencies: []
---

# OAuth callback CSP gaps: missing `base-uri`/`form-action` and `googletagmanager.com` img-src

## Problem Statement
Two issues on `whoop/callback/index.html` and `spotify/callback/index.html`:

1. **Missing CSP directives.** `default-src 'none'` does NOT cover `base-uri` or `form-action` (no fallback). A future XSS or markup bug could pivot via `<base href>` injection or form hijack to exfiltrate the OAuth `code=` query param.

2. **`img-src` missing `googletagmanager.com`.** CLAUDE.md notes the main pages added it 2026-04-28 to unblock GA4 measurement pixels; callbacks were missed. Pixels render but are silently blocked by CSP.

**Surfaced by:** security-sentinel + architecture-strategist during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Add the missing directives
- Add `base-uri 'none'; form-action 'none'; object-src 'none'` to both callback CSP meta tags
- Add `https://www.googletagmanager.com` to `img-src` on both
- **Effort:** Small (~5 min, two files)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] Both callback pages carry `base-uri 'none'`, `form-action 'none'`, `object-src 'none'`
- [ ] Both `img-src` directives include `googletagmanager.com`
- [ ] Existing CSP byte-equality assertions in `tests/test_site_e2e.py` updated if pinned

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
