---
status: pending
priority: p1
issue_id: 030
tags: [code-review, performance]
dependencies: []
---

# Replace or remove GA4 placeholder G-XXXXXXXXXX

## Problem
The placeholder `G-XXXXXXXXXX` fires real network requests to googletagmanager.com on every page load across all HTML files. Wastes bandwidth, collects no data, and the TODO comment in source signals an unfinished site.

## Proposed Solutions
Replace with real Measurement ID in all HTML files, or remove the GA snippet entirely until the real ID is available.

## Acceptance Criteria
- [ ] No `G-XXXXXXXXXX` placeholder in any HTML file.
