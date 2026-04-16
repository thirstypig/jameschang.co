---
status: done
priority: p2
issue_id: 037
tags: [code-review, quality]
dependencies: []
---

# Remove unnecessary !important flags from CSS

## Problem
`.project-meta` has 3 `!important` declarations (margin-top, font-size, color) fighting only the parent `.project-card p` rule. `.case-outcome` has `margin-top: 1.5rem !important`. None of these need `!important` — specificity can be raised with `.project-card .project-meta` instead.

## Proposed Solutions
Raise specificity and drop all `!important` flags from .project-meta and .case-outcome.

## Acceptance Criteria
- [ ] Zero `!important` declarations in .project-meta and .case-outcome rules.
