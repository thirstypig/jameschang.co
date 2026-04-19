---
status: done
priority: p2
issue_id: 066
tags: [code-review, javascript, accessibility]
dependencies: []
---

# Headshot rotator: setInterval not cleared + prefers-reduced-motion not live

## Problem Statement
Two related issues with the headshot rotation in `script.js`:

1. **setInterval never cleared** (lines 35-39): The 5-second interval runs forever, even when the tab is backgrounded. On tab resume, browsers may batch-deliver queued callbacks, causing a brief strobing flash of faces. Also wastes battery on background tabs.

2. **prefers-reduced-motion checked once** (line 30): The media query is evaluated at page load but never re-checked. If a user enables "Reduce motion" in OS settings while the page is open, the interval keeps ticking. The CSS transition becomes near-instant (0.01ms per styles.css:74-80), so the user sees abrupt 5-second swaps — worse than the smooth crossfade for motion-sensitive users.

## Findings
- `script.js:30` — `if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches)` — one-time check
- `script.js:35-39` — `setInterval` with no corresponding `clearInterval`
- `styles.css:74-80` — CSS reduces transition to 0.01ms for reduced-motion, but JS still ticks

## Proposed Solutions

### Option A: Add visibilitychange listener + motion query listener (Recommended)
```js
let intervalId = null;
const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
const tick = () => { /* existing rotation logic */ };
const start = () => { if (!intervalId) intervalId = setInterval(tick, 5000); };
const stop = () => { clearInterval(intervalId); intervalId = null; };

if (!motionQuery.matches) start();
document.addEventListener("visibilitychange", () => {
  document.hidden ? stop() : (!motionQuery.matches && start());
});
motionQuery.addEventListener("change", (e) => {
  e.matches ? stop() : start();
});
```
- **Effort:** Small (10-15 lines replaces 5)
- **Risk:** None

## Acceptance Criteria
- [ ] Interval pauses when tab is hidden
- [ ] Interval resumes when tab becomes visible (unless reduced-motion is active)
- [ ] Toggling OS reduced-motion preference live stops/starts the rotation
- [ ] No strobing on tab resume

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |
