---
status: pending
priority: p3
issue_id: 013
tags: [code-review, agent-native, schema]
dependencies: []
---

# Add dateModified to schema + explicit availability signal

## Problem Statement

1. Footer shows "Last updated April 14, 2026" as human-readable `<time>`, but no `dateModified` on any schema object. Agents comparing site freshness across sources have no structured signal.

2. No explicit "open to new roles" signal. A recruiting agent asking "is James available for senior PM work?" has to infer — currently the answer is ambiguous (he's running a founder vehicle but still credentials as Senior PM).

## Findings

From agent-native-reviewer agent (P2-C, P3-D).

## Proposed Solutions

### Option A: Add `dateModified` to WebSite + Person schemas
```json
"dateModified": "2026-04-14"
```
- Regenerate on every push (or manually on major updates)
- **Effort:** Small (~5 min)

### Option B: Add explicit availability via hero text + `Person.seeks`
- Add a one-line "Currently: open to senior PM roles alongside Aleph Co." under hero
- Schema: `"seeks": { "@type": "Demand", "name": "Senior Product Manager role" }`
- **Effort:** Small (~10 min) • **Cons:** user may not want this framing

### Option C: Add a `/now` page (Derek Sivers pattern)
- `/now.html` with 200 words about current focus + availability
- Links from hero
- **Effort:** Medium (~20 min) • **Pros:** benchmark sites (Lee Robinson, Paco) use this • **Cons:** scope creep

## Technical Details

Patch JSON-LD:
```json
{
  "@type": "WebSite",
  "dateModified": "2026-04-14"
},
{
  "@type": "Person",
  ...
  "seeks": { ... }
}
```

## Acceptance Criteria

- [ ] `dateModified` on WebSite and/or Person schemas
- [ ] (If Option B/C) Availability signal visible to humans AND in schema

## Work Log

_(blank)_

## Resources

- Agent-native review (P2-C, P3-D)
