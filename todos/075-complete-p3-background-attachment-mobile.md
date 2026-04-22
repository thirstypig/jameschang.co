---
status: done
priority: p3
issue_id: 075
tags: [code-review, performance, css]
dependencies: []
---

# background-attachment: fixed causes potential scroll jank on mobile

## Problem Statement
`styles.css:93` applies `background-attachment: fixed` to the body. On iOS Safari, this is silently converted to `scroll`. On some Android browsers, it forces a separate composited layer for the full page height, causing scroll jank on lower-end devices. Not affecting Lighthouse (simulated fast device), but could impact real-world mobile experience.

## Proposed Solutions

### Option A: Disable on touch devices (Recommended)
```css
@media (hover: none) {
  body { background-attachment: scroll; }
}
```
- **Effort:** Small (2 lines)
- **Risk:** None — iOS Safari already ignores it

## Acceptance Criteria
- [ ] `background-attachment: fixed` disabled on touch/mobile devices
- [ ] Desktop visual unchanged

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |
