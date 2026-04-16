---
status: pending
priority: p3
issue_id: 040
tags: [code-review, quality]
dependencies: []
---

# Remove redundant color: var(--text) declarations

## Problem
`.display-tagline` and `.project-card p` both declare `color: var(--text)` which is already inherited from `body`. Also `.contact-line .dot` has a mobile override `display: inline` that does nothing since inline is the default.

## Proposed Solutions
Remove the redundant `color: var(--text)` from .display-tagline and .project-card p. Remove the mobile `.contact-line .dot { display: inline; }` rule.

## Acceptance Criteria
- [ ] No redundant inherited-value declarations.
