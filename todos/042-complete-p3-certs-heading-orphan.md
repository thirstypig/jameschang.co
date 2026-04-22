---
status: done
priority: p3
issue_id: 042
tags: [code-review, architecture]
dependencies: []
---

# Wrap certifications in a grouping element

## Problem
`<h3 class="certs-heading">Certifications</h3>` at index.html line ~536 sits directly inside `<section id="education">` as a sibling of `<article class="degree">`, not nested in any grouping element. It is semantically an orphan heading.

## Proposed Solutions
Wrap certifications (h3 + ul + details) in a `<div>` or second `<article>` for grouping.

## Acceptance Criteria
- [ ] Certifications heading has a parent grouping element.
