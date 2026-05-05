---
status: pending
priority: p3
issue_id: 131
tags: ['code-review', 'simplicity', 'css', 'bucketlist']
dependencies: []
---

# Extract chip + favorites styling to notebook.css classes

## Problem Statement
Two new chunks of inline-style sprawl shipped this session:

1. **`bucketlist/bucketlist.js:24-38`** — `chip()` function builds a span with 11 inline `el.style.x = ...` assignments (font-family, font-size, text-transform, letter-spacing, padding, margin, border, color, border-radius, white-space, plus a color override).

2. **`now/index.html:444-455` and `:475-486`** — two near-identical `<div>` blocks for "favorites" sub-sections inside the Plex/Spotify columns, each with 6 inline `style="..."` attributes (margin-top, padding-top, border-top dashed, plus inner spacing).

Both work. Both also bloat the JS/HTML and make restyling annoying.

**Surfaced by:** code-simplicity-reviewer (#1, #3) during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Add two classes to `notebook.css` (recommended)

```css
/* Chip — used by bucketlist.js for priority/difficulty tags */
.nb-chip {
  font-family: var(--mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 1px 6px;
  margin-left: 6px;
  border: 1px solid var(--c, var(--rule));
  color: var(--c, var(--dim));
  border-radius: 2px;
  white-space: nowrap;
}

/* Favorites sub-block inside an .nb-feed column on /now */
.nb-feed-favorites {
  margin-top: 8px;
  padding-top: 10px;
  border-top: 1px dashed var(--rule);
}
.nb-feed-favorites p { margin: 0 0 6px; }
.nb-feed-favorites ul { margin: 0; padding-left: 18px; }
```

In `bucketlist.js`:
```js
function chip(label, color) {
  const el = document.createElement('span');
  el.className = 'nb-chip';
  if (color) el.style.setProperty('--c', color);
  el.textContent = label;
  return el;
}
```

In `now/index.html`, replace each favorites `<div style="…">` with `<div class="nb-feed-favorites">`.

**Effort:** Small (~20 min)
**Risk:** Low. Visual diff before/after via headless screenshot.

### Option B — Keep inline
Justifiable per CLAUDE.md "no build step" framing — but other JS-built UI on the site (the hitlist renderer in `now/now.js`) follows the same inline-style pattern, so the precedent isn't strong either way.

## Acceptance Criteria
- [ ] Two new classes in `notebook.css`
- [ ] `bucketlist.js` chip helper uses class + CSS var
- [ ] `now/index.html` favorites blocks use class
- [ ] Visual diff shows no regression on light + dark
- [ ] LOC saved ≈ 25 across both files

## Resources
- `bucketlist/bucketlist.js:24-38`
- `now/index.html:444-455,475-486`
- `notebook.css` (target for new classes)
