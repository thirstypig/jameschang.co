---
status: pending
priority: p1
issue_id: 032
tags: [code-review, quality]
dependencies: []
---

# Hide testimonials in print stylesheet

## Problem
The print flexbox reorder lists hero, about, experience, education, skills, projects, memberships, and hides case-studies. But `#testimonials` has no `order` rule and no `display: none`. It renders at `order: 0`, appearing at the top of the printed PDF alongside the hero. Testimonials are not resume content.

## Proposed Solutions
Add `#testimonials { display: none; }` inside the print block.

## Acceptance Criteria
- [ ] Testimonials section does not appear in printed PDF.
