---
status: pending
priority: p2
issue_id: 039
tags: [code-review, performance]
dependencies: []
---

# Audit /now/ page dependency on work.css

## Problem
now/index.html line 14 loads `/work/work.css`. If only a few classes (.work-main, .work-hero, .work-section, .module) are needed, the full 464-line file may be mostly wasted bytes.

## Proposed Solutions
Audit which classes from work.css are actually used on the /now/ page. Either inline the needed rules into styles.css, or confirm the dependency is justified.

## Acceptance Criteria
- [ ] /now/ page loads only the CSS it actually uses, or the full load is explicitly justified.
