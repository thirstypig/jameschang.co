---
status: done
priority: p3
issue_id: 041
tags: [code-review, architecture]
dependencies: []
---

# Consider figure/figcaption for testimonial blockquotes

## Problem
Testimonials use `<div class="testimonial">` wrapping `<blockquote>` + `<cite>`. Semantically, `<figure>` + `<figcaption>` is the recommended HTML5 pattern for blockquote-with-attribution.

## Proposed Solutions
Optional: wrap each testimonial in `<figure>` and move `<cite>` into `<figcaption>`.

## Acceptance Criteria
- [ ] Testimonials use semantic figure/figcaption markup, or decision documented to keep current markup.
