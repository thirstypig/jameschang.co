---
status: pending
priority: p2
issue_id: 036
tags: [code-review, quality]
dependencies: []
---

# Remove dead CSS — .display-tagline a and .tagline-metric rules

## Problem
styles.css has ~13 lines of CSS for `.display-tagline a`, `.display-tagline a:hover`, and `.tagline-metric` but the hero tagline in HTML contains no links and no element with `.tagline-metric`. These rules are dead.

## Proposed Solutions
Delete the `.display-tagline a`, `.display-tagline a:hover`, and `.tagline-metric` rulesets from styles.css.

## Acceptance Criteria
- [ ] No dead selectors for removed HTML elements remain in styles.css.
