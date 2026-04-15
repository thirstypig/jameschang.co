---
status: pending
priority: p3
issue_id: 015
tags: [code-review, simplicity, security]
dependencies: [011]
---

# Drop JS email-reveal obfuscation — use plain `mailto:` throughout

## Problem Statement

`script.js:5-16` builds the email string at click time from user+domain concatenation and attaches handlers to `data-email` / `data-email-cta` elements. The email is **already plaintext in 4 other HTML locations** (inside `class="print-only"` spans at `index.html:136, 149, 511, 513` plus a `mailto:` at `:511`). The JS obfuscation therefore buys zero incremental protection — any harvester parses the raw HTML.

The real protection against spam in 2026 is Gmail's spam filter, not HTML obfuscation. Remove the ceremony.

## Findings

From security-sentinel agent (P3-2 Option B): "The JS reveal is mostly performance theater — accept it or remove it. … the email is already plaintext in five places. I recommend Option B: drop the JS reveal, put a plain mailto in the footer."

Also from agent-native-reviewer (P1-B): a crawl-visible email in a non-print-only location would help agents.

## Proposed Solutions

### Option A (Recommended): Delete email-reveal JS, use plain `mailto:` everywhere
- `script.js` loses 13 lines → ~20 lines total (just theme toggle)
- Footer + hero CTA become `<a href="mailto:jimmychang316@gmail.com">jimmychang316@gmail.com</a>` (or "Email")
- Removes `data-email` / `data-email-cta` attributes from HTML
- **Effort:** Small (~10 min)
- **Pros:** simpler JS, honest, one less UI interaction, better for agents
- **Cons:** email sits visibly on the page (but already does via print-only)

### Option B: Keep JS reveal, remove the redundant `.print-only mailto:` links
- Keeps the "reveal on click" aesthetic
- Would need to commit to the obfuscation being the only path
- **Effort:** Small • **Cons:** obfuscation is still defeatable by any scraper

### Option C: Leave as-is
- **Effort:** None • **Cons:** ceremony without benefit

## Technical Details

Remove from `script.js`:
```js
// Everything from "// --- Email reveal ---" through the closing brace of the forEach
```

Update `index.html`:
- Line 136: change `<a href="#" data-email-cta>...</a>` → `<a href="mailto:jimmychang316@gmail.com">email</a>`
- Line 510-511: change `<a href="#" data-email class="no-print">reveal email</a>` + print-only sibling → single `<a href="mailto:jimmychang316@gmail.com">jimmychang316@gmail.com</a>`

## Acceptance Criteria

- [ ] `script.js` no longer contains email-reveal logic
- [ ] All `data-email` / `data-email-cta` attributes removed from HTML
- [ ] Footer shows plain email as a `mailto:` link, visible on screen
- [ ] Total JS size reduced by ~700 bytes raw
- [ ] No regression in theme toggle behavior

## Work Log

_(blank)_

## Resources

- Security review (P3-2 Option B)
- Agent-native review (P1-B — email discoverability)
