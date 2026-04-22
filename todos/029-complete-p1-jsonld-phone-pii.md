---
status: done
priority: p1
issue_id: 029
tags: [code-review, security]
dependencies: []
---

# Remove personal phone number from JSON-LD structured data

## Problem
index.html line 69 has `"telephone": "+1-626-340-7371"` in JSON-LD. Unlike print-only HTML hidden via CSS, JSON-LD is always in the DOM and actively consumed by Google, scrapers, and data brokers. Creates spam/phishing risk.

## Proposed Solutions
Remove the `telephone` field from JSON-LD entirely. Review the `contactPoint` block at line 79 which also contains email.

## Acceptance Criteria
- [ ] No `telephone` field in JSON-LD; contactPoint reviewed for necessity.
