---
status: done
priority: p2
issue_id: 038
tags: [code-review, performance]
dependencies: []
---

# Remove backdrop-filter from .theme-toggle — invisible at 32px

## Problem
`backdrop-filter: blur(20px) saturate(1.3)` on the 32px theme toggle pill is invisible at that size and wastes a compositing layer.

## Proposed Solutions
Remove `backdrop-filter` and `-webkit-backdrop-filter` from `.theme-toggle`.

## Acceptance Criteria
- [ ] No backdrop-filter on .theme-toggle. Visual appearance unchanged.
