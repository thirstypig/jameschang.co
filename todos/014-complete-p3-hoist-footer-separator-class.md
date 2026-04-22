---
status: done
priority: p3
issue_id: 014
tags: [code-review, simplicity, css]
dependencies: []
---

# Hoist repeated inline `<span style="margin: 0 0.5rem;">·</span>` to a utility class

## Problem Statement

The same inline-styled separator appears 11+ times across `/work/**/index.html` and `work/index.html`:
```html
<span style="margin: 0 0.5rem;">&middot;</span>
```

Should be a CSS class.

## Findings

From code-simplicity-reviewer agent (P2.1).

## Proposed Solutions

### Option A (Recommended): Add `.sep` utility class, replace instances
- CSS: `.footer-meta .sep { margin: 0 0.5rem; opacity: 0.5; }` (or extend the existing `.crumbs .sep`)
- HTML: `<span class="sep">&middot;</span>`
- **Effort:** Small (~10 min via sed/find-replace across 11 files)
- **Savings:** ~250 bytes, cleaner HTML

### Option B: Leave as-is
- Inline style is local and harmless
- **Effort:** None • **Cons:** adds noise to HTML

## Technical Details

One-liner to find + update:
```python
import pathlib, re
for f in pathlib.Path(".").rglob("*.html"):
    s = f.read_text()
    s = s.replace('<span style="margin: 0 0.5rem;">&middot;</span>',
                  '<span class="sep">&middot;</span>')
    f.write_text(s)
```

Plus CSS in `work/work.css`:
```css
.footer-meta .sep { margin: 0 0.5rem; opacity: 0.5; }
```

## Acceptance Criteria

- [ ] Zero `style="margin: 0 0.5rem;"` inline attributes in repo
- [ ] `.sep` class rendered identically to previous inline style
- [ ] All 11 HTML files updated

## Work Log

_(blank)_

## Resources

- Simplicity review (P2.1)
