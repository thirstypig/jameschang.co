---
status: pending
priority: p2
issue_id: 056
tags: [code-review, security, quality]
dependencies: []
---

# WHOOP build_html does zero escaping; escape_html missing single-quote handling

## Problem
`bin/update-whoop.py` builds HTML with f-strings containing numeric WHOOP data — safe today but any future text field (workout name, sport label) would XSS into /now. Additionally, `escape_html()` in all scripts handles `& < > "` but not `'` — fine for double-quoted attributes (which is what the site uses) but fragile if future code uses single quotes.

## Proposed Solutions
(1) After extracting `bin/_shared.py` (todo 050), call `escape_html()` on every text field in WHOOP's build_html. (2) Add `.replace("'", "&#39;")` to escape_html. Grep rule: any f-string interpolating a field named name/title/summary/repo/show/episode without escape_html wrap should be treated as a bug.

## Acceptance Criteria
- [ ] All text fields in all three scripts flow through escape_html; escape_html handles single quotes; no un-escaped interpolation of external strings remains.
