---
status: pending
priority: p2
issue_id: 006
tags: [code-review, security, headers]
dependencies: []
---

# Add Content Security Policy meta tag

## Problem Statement

GitHub Pages doesn't let you set HTTP headers, so the site has no Content Security Policy. For the current inventory (zero third-party scripts, one self-hosted JS, one CSS file, inline JSON-LD only), a strict CSP via `<meta http-equiv>` is cheap and meaningfully hardens against future accidental regressions (someone pastes a Plausible/Typeform/analytics embed).

## Findings

From security-sentinel agent (P2-2):
- No CSP currently
- No inline `<script>` (aside from JSON-LD, which is `application/ld+json` type — data, not code)
- No inline `style="..."` attributes in HTML (except a handful of footer separators — see todo #014)
- No third-party resources
- Meta-CSP is weaker than header-CSP (parsing starts before the tag is seen) but still useful as a tripwire

## Proposed Solutions

### Option A (Recommended): Single strict meta CSP copied to all 12 HTML pages
```html
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'none'; base-uri 'self'; frame-ancestors 'none'; upgrade-insecure-requests">
```
- **Effort:** Small (~10 min via script to inject into 12 HTML files)
- **Pros:** Hardens against accidental third-party embeds, prevents iframe embedding (clickjacking defense), forces HTTPS on any http link
- **Cons:** Meta-CSP is weaker than header-CSP; small duplication across 12 pages

### Option B: Put Cloudflare in front of GitHub Pages, set real headers
- Free Cloudflare proxy in front; Page Rule or Workers for headers
- **Effort:** Large (~1 hour setup) • **Pros:** real HTTP headers, free analytics as bonus • **Cons:** new infra dependency for a static site

### Option C: Skip CSP
- Accept current state; site has no attack surface worth defending
- **Effort:** None • **Pros:** zero work • **Cons:** no tripwire against future mistakes

## Technical Details

Inject via Python one-liner:
```python
import pathlib
CSP = '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; script-src \'self\'; style-src \'self\'; img-src \'self\' data:; font-src \'self\'; connect-src \'self\'; form-action \'none\'; base-uri \'self\'; frame-ancestors \'none\'; upgrade-insecure-requests">'
for f in pathlib.Path(".").rglob("*.html"):
    s = f.read_text()
    if "Content-Security-Policy" not in s:
        s = s.replace('<meta name="color-scheme"', f'{CSP}\n  <meta name="color-scheme"')
        f.write_text(s)
```

Also add (same mechanism):
```html
<meta name="referrer" content="strict-origin-when-cross-origin">
```

## Acceptance Criteria

- [ ] Every HTML page has the CSP meta tag in `<head>`
- [ ] Site still loads and functions (no CSP violations — check DevTools Console)
- [ ] JSON-LD still parses
- [ ] Theme toggle still works (script.js runs)
- [ ] Images load (including lazy-loaded /work/ screenshots)
- [ ] `securityheaders.com/?q=https://jameschang.co` shows CSP detected

## Work Log

_(blank)_

## Resources

- Security audit output (P2-2)
- MDN CSP reference: https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
