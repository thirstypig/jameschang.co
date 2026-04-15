---
status: pending
priority: p2
issue_id: 011
tags: [code-review, agent-native, schema, contact]
dependencies: []
---

# Expose email via Person.contactPoint (machine-readable)

## Problem Statement

The only machine-readable email on the site is inside a `class="print-only"` element — which is technically in the HTML but semantically marked "print only." A conservative agent may skip it. There's no `ContactPoint` in JSON-LD. Simultaneously, security review flagged that the JS-reveal obfuscation is ineffective because the email is already in plaintext 4 other places.

The pragmatic move is to stop pretending the email is hidden and expose it cleanly.

## Findings

From agent-native-reviewer (P1-B) + security-sentinel (P3-2 Option B):
- `script.js:6-8` builds email at runtime
- `index.html:136, 149, 511, 513` — email or mailto: already in HTML
- No `ContactPoint` schema

Both reviewers independently converge on: "obfuscation is theater; expose it honestly."

## Proposed Solutions

### Option A (Recommended): Add `contactPoint` to Person schema + keep JS reveal
- Minimum change: JSON-LD `contactPoint: { email: "jimmychang316@gmail.com", contactType: "professional" }`
- Keep JS reveal for the visible link
- **Effort:** Small (~5 min) • **Pros:** agent-discoverable, user-facing stays the same

### Option B: Drop JS reveal, use plain `mailto:` everywhere
- Delete email-reveal block from `script.js` (saves 13 lines)
- Replace `<a href="#" data-email>reveal email</a>` with `<a href="mailto:jimmychang316@gmail.com">jimmychang316@gmail.com</a>`
- Add `contactPoint` to schema
- **Effort:** Small (~10 min) • **Pros:** honest, simpler, one less JS feature • **Cons:** slight spam risk (but email is already plaintext in 4 places so this is moot)

### Option C: Do both — A now, B later
- Ship A immediately for agent discoverability
- Revisit B during next simplification pass

## Technical Details

Patch JSON-LD in `/index.html` around line 54:
```json
"contactPoint": [{
  "@type": "ContactPoint",
  "email": "jimmychang316@gmail.com",
  "contactType": "professional"
}]
```

For Option B, also delete `script.js:5-16` and simplify `index.html:136, 510-511`.

## Acceptance Criteria

- [ ] JSON-LD includes `contactPoint` with email and contactType
- [ ] Schema validates
- [ ] Google Rich Results Test still passes
- [ ] (If Option B) script.js is shorter; footer shows plain `mailto:` link

## Work Log

_(blank)_

## Resources

- Agent-native review (P1-B)
- Security review (P3-2)
