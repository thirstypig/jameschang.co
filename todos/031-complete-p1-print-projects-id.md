---
status: done
priority: p1
issue_id: 031
tags: [code-review, quality]
dependencies: []
---

# Fix print stylesheet — #projects targets nonexistent ID (should be #work)

## Problem
styles.css line ~823 has `#projects { order: 5; }` in the print media query, but the HTML section uses `id="work"`. The Work section gets no order value in print and renders out of position in the PDF resume.

## Proposed Solutions
Change `#projects` to `#work` in the print media query.

## Acceptance Criteria
- [ ] Print-rendered PDF shows Work section in the correct position (after Experience, before Education).
