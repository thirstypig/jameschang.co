---
status: done
priority: p2
issue_id: 025
tags: [code-review, simplicity, css]
dependencies: []
---

# Drop the dotted underline on project card titles — third redundant affordance

## Problem

`.project-card h3 a` has three visual cues that the card is clickable:
1. `border-bottom: 1px dotted var(--muted)` (title underline)
2. `.project-card:has(h3 a):hover { border-color: var(--accent); cursor: pointer; }` (card hover)
3. Stretched-link `::after { inset: 0 }` making the whole card clickable

Pick two, not three. The dotted underline reads cluttered next to the hover state.

## Proposed Solutions

### Option A (Recommended): Remove the dotted underline
Keep card hover + stretched-link. Title is visually distinct via font-weight alone; hover makes clickability obvious.

### Option B: Replace dotted with a single subtle arrow glyph after title
Costs complexity without clear win.

### Option C: Status quo
Three affordances. Works but cluttered.

## Technical Details

`styles.css` around the stretched-link block — remove these two lines:
```css
.project-card h3 a { ... border-bottom: 1px dotted var(--muted); }
.project-card h3 a:hover { ... border-bottom-color: var(--accent); }
```

## Acceptance Criteria
- [ ] Card titles have no underline
- [ ] Hover state still visible (card border changes to accent)
- [ ] Click anywhere on card still navigates

## Resources
- code-simplicity-reviewer review 2026-04-15, SIMPLIFY #4
