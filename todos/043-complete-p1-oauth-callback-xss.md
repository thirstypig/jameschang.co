---
status: done
priority: p1
issue_id: 043
tags: [code-review, security]
dependencies: []
---

# XSS in WHOOP + Spotify OAuth callback pages via unescaped query params

## Problem
`/Users/jameschang/Projects/jameschang.co/whoop/callback/index.html` and `/Users/jameschang/Projects/jameschang.co/spotify/callback/index.html` use `innerHTML` with template literals that interpolate `params.get('code')`, `params.get('error')`, and `params.get('error_description')` directly. Attacker-crafted URL like `https://jameschang.co/whoop/callback/?error=<img src=x onerror=alert(1)>` executes script on the jameschang.co origin. Script can exfiltrate cookies, localStorage, or call `navigator.clipboard.writeText` to swap the auth code the owner pastes into their terminal.

## Proposed Solutions
Rewrite both callback pages to build DOM via `document.createElement` and `.textContent` — never innerHTML with interpolation. Add a strict CSP meta: `default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'` (scoped to just the callback page).

## Acceptance Criteria
- [ ] No `innerHTML` with interpolated query params
- [ ] Every external value rendered via textContent
- [ ] CSP meta tag added
- [ ] Test with malicious query params shows escaped output, not executed
