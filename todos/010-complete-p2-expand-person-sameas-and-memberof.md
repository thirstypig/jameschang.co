---
status: pending
priority: p2
issue_id: 010
tags: [code-review, agent-native, schema]
dependencies: []
---

# Expand Person.sameAs + add memberOf for board role

## Problem Statement

`Person.sameAs` currently lists only LinkedIn, GitHub, and alephco.io. The 6 other product URLs James operates (Bahtzang, Fantastic Leagues, Judge Tool, Thirsty Pig, etc.) are not connected to the Person entity in structured data. An LLM researching "James Chang's products" has to walk prose to find them.

Also, the Chinese American Museum board role lives only in visible HTML — not in Person schema as `memberOf` or `affiliation`.

## Findings

From agent-native-reviewer agent (P2-D, P2-E).

## Proposed Solutions

### Option A (Recommended): Expand sameAs + add memberOf
- Add: bahtzang.com, thefantasticleagues.com, thejudgetool.com, thirstypig.com, /resume.pdf to `sameAs`
- Add: `memberOf` with CAM org node
- **Effort:** Small (~10 min) • **Pros:** clean agent linkage • **Cons:** none

### Option B: Skip sameAs, use explicit SoftwareApplication schemas (see todo #009)
- Related but different mechanism
- **Covered by todo #009**

## Technical Details

Patch `/Users/jameschang/Projects/jameschang.co/index.html:54-59` area:
```json
"sameAs": [
  "https://www.linkedin.com/in/jimmychang316",
  "https://github.com/thirstypig",
  "https://alephco.io",
  "https://bahtzang.com",
  "https://thefantasticleagues.com",
  "https://thejudgetool.com",
  "https://thirstypig.com"
],
"memberOf": [{
  "@type": "Organization",
  "name": "Chinese American Museum",
  "url": "https://camla.org",
  "sameAs": "https://camla.org"
}]
```

## Acceptance Criteria

- [ ] `sameAs` includes all 6 product URLs + LinkedIn + GitHub
- [ ] `memberOf` encodes CAM board affiliation
- [ ] Schema validates
- [ ] Google Rich Results Test still passes

## Work Log

_(blank)_

## Resources

- Agent-native review (P2-D, P2-E)
