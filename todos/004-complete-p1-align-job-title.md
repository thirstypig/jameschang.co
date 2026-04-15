---
status: pending
priority: p1
issue_id: 004
tags: [code-review, agent-native, seo, consistency]
dependencies: []
---

# Job title is inconsistent across 4 places

## Problem Statement

A search/LLM agent pulling James's job title from the site gets different answers depending on where it looks:

| Location | Value |
|---|---|
| `<title>` in `<head>` | "James Chang — Founder & Product Manager" |
| Hero visible text (`index.html:130`) | "Senior Product Manager" |
| JSON-LD `jobTitle` (`index.html:51`) | "Founder & Product Manager" |
| `llms.txt:3` | "senior product manager" |

A recruiting agent comparing to a "Senior Product Manager" job spec gets inconsistent matches. An LLM writing a summary will hedge ("James, who is variously described as…"). Same person, four different strings.

## Findings

From agent-native-reviewer agent (P1-A):
- `<title>` and JSON-LD agree on "Founder & Product Manager"
- Visible hero and llms.txt agree on "Senior Product Manager"
- No single canonical string

## Proposed Solutions

### Option A (Recommended): Unify on "Senior Product Manager" (matches hero, llms.txt)
- Update `<title>` → "James Chang — Senior Product Manager"
- Update JSON-LD `jobTitle` → "Senior Product Manager"
- Add `additionalName` or extend Person schema to capture "Founder, Aleph Co." via `affiliation` or `worksFor`
- **Effort:** Small (~5 min)
- **Pros:** Matches visible hero, recruiter-optimized, cleanest for ATS
- **Cons:** Downplays founder framing slightly

### Option B: Unify on "Founder & Senior Product Manager" (captures duality)
- Update hero, `<title>`, JSON-LD, llms.txt all to the compound title
- **Effort:** Small • **Pros:** Honest • **Cons:** Long string, compound titles confuse some ATS parsers

### Option C: Keep hero simple, fix schemas to match
- Hero stays "Senior Product Manager" (visual)
- `<title>` → "James Chang — Senior Product Manager"
- JSON-LD `jobTitle` → "Senior Product Manager", add `worksFor: Aleph Co.` for founder framing via relationship
- **Effort:** Small • **Equivalent to A in practice**

## Technical Details

Files to edit:
- `/Users/jameschang/Projects/jameschang.co/index.html:8` — `<title>`
- `/Users/jameschang/Projects/jameschang.co/index.html:51` — JSON-LD `jobTitle`
- `/Users/jameschang/Projects/jameschang.co/index.html:10` — `<meta name="description">` if needed
- `/Users/jameschang/Projects/jameschang.co/index.html:14-16` — OG tags
- `/Users/jameschang/Projects/jameschang.co/llms.txt:3` — already lowercase-matching hero

Note: `worksFor` at JSON-LD already references Aleph Co. — that's the right place for the founder framing.

## Acceptance Criteria

- [ ] Single canonical job title string appears identically in `<title>`, `<meta>` tags, OG tags, JSON-LD `jobTitle`, and hero
- [ ] `llms.txt` matches the same canonical string (case-insensitive fine)
- [ ] Agent-native test: curl both `/` and `/llms.txt`, compare title strings — identical
- [ ] `jobTitle` in schema is recruiter-searchable (e.g., "Senior Product Manager" not a compound)

## Work Log

_(blank)_

## Resources

- Agent-native review output
- `index.html` head region
