---
status: done
priority: p3
issue_id: 074
tags: [code-review, accessibility, javascript]
dependencies: []
---

# Minor JS/accessibility fixes: lightbox keyboard access + hitlist console.warn

## Problem Statement
Two minor improvements:

1. **Lightbox not keyboard-focusable**: Dashboard pages use `<figure onclick="...showModal()">` which is not keyboard-accessible. A keyboard-only user cannot open the lightbox. The `<dialog>` itself handles Escape correctly. Fix: add `tabindex="0"` and `role="button"` to the figure, or wrap contents in a `<button>`.

2. **Hitlist catch block missing console.warn**: Per the documented solution in `docs/solutions/integration-issues/silent-fetch-failure-csp-graceful-fail-debugging.md`, the catch block should include `console.warn('[hitlist]', e)` before `container.remove()` to surface future failures in dev tools.

## Findings
- `work/fantastic-leagues/dashboard/index.html:95` — `<figure onclick="...">` not keyboard-accessible
- `work/aleph/dashboard/index.html:91` — same issue
- `now/index.html:~306` — `catch (e) { container.remove(); }` — no console.warn

## Proposed Solutions
1. Add `tabindex="0" role="button"` and keydown handler to clickable figures
2. Add `console.warn('[hitlist]', e);` before `container.remove()`
- **Effort:** Small
- **Risk:** None

## Acceptance Criteria
- [ ] Dashboard lightbox images are keyboard-focusable and activatable
- [ ] Hitlist fetch failures produce a console.warn for debugging

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |
