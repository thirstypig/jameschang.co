---
status: pending
priority: p1
issue_id: 022
tags: [code-review, consistency, content]
dependencies: []
---

# FBST analytics page uses two different names for itself

## Problem

`/work/fantastic-leagues/analytics/index.html` refers to itself by two names across the same page:

| Location | Value |
|---|---|
| `<title>` (line 9) | `The Fantastic Leagues — Product & AI — James Chang` |
| JSON-LD `name` (line 20) | Same |
| Breadcrumb leaf (line 64) | `Product & AI` |
| Eyebrow (line 85) | `Product & AI` |
| **project-nav aria-current** (line 73) | `Product metrics` ← |
| `/work/index.html:114` card | `Product metrics` ← |

Readers coming from the /work/ hub expect "Product metrics" and land on a page titled "Product & AI." Minor but confusing.

## Proposed Solutions

### Option A (Recommended): Normalize to "Product metrics"
The nav and hub card already use it. Update the page title, JSON-LD name, breadcrumb, and eyebrow.

### Option B: Normalize to "Product & AI"
Update the hub card + project-nav instead. Loses the more descriptive "metrics" framing.

### Option C: Use both: "Product metrics & AI"
Compromise label. Slightly longer but captures both dimensions.

## Acceptance Criteria
- [ ] One name used across `<title>`, JSON-LD `name`, breadcrumb, eyebrow, project-nav, hub card
- [ ] aria-current still marks the correct item

## Resources
- pattern-recognition review 2026-04-15, H2
