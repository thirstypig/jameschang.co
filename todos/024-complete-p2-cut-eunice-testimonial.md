---
status: done
priority: p2
issue_id: 024
tags: [code-review, content, simplicity]
dependencies: []
---

# Cut the Eunice testimonial — too generic

## Problem

`/index.html:227-231`:
> *"Jimmy has strong technical knowledge that makes project implementation successful."* — Eunice · Creative Consultant

Simplicity review called this out: "Strong technical knowledge" + "makes project implementation successful" is LinkedIn-recommendation boilerplate. Reader can't tell whether Eunice worked with him for a week or a decade. Two strong specific quotes (Jaime, Chirag) read as curated; three-with-one-weak reads as stretching.

## Proposed Solutions

### Option A (Recommended): Remove the Eunice block, keep Jaime + Chirag
- LOC reduction: ~5
- Signal improvement: noticeable

### Option B: Rewrite Eunice's quote to something more specific
Requires richer source material; user's source was brief. If user wants to keep her, ask for a more specific 1-2 sentences from the full rec.

### Option C: Keep as-is
No change. Accept the mixed signal.

## Acceptance Criteria
- [ ] Testimonial section has 2 specific quotes (Jaime, Chirag) or 3 if user provides better Eunice text
- [ ] Grid still renders cleanly with 2 items (CSS already handles 2-column)

## Resources
- code-simplicity-reviewer review 2026-04-15, CUT #2
