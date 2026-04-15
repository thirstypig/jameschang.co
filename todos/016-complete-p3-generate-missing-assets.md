---
status: pending
priority: p3
issue_id: 016
tags: [code-review, polish, seo, images]
dependencies: [002]
---

# Generate missing `og-image.png`, `favicon.svg`, `apple-touch-icon.png`

## Problem Statement

HTML references three asset files that don't exist:

| Reference | File | Current state |
|---|---|---|
| `<meta property="og:image">` | `/assets/og-image.png` | 404 |
| `<link rel="icon" type="image/svg+xml">` | `/assets/favicon.svg` | 404 |
| `<link rel="apple-touch-icon">` | `/assets/apple-touch-icon.png` | 404 |

Result: when sharing `jameschang.co` on LinkedIn/Slack/iMessage, the preview falls back to auto-scraping the headshot (if found) or shows nothing. No favicon in browser tabs. No iOS home-screen icon.

## Findings

From security-sentinel agent (P3-5) + README.md:40-43 (already tracked as "missing before launch").

## Proposed Solutions

### Option A (Recommended): Generate all three from existing headshot
- **OG image (1200×630 PNG):** crop/extend headshot with name + role overlay using an image editor or Figma
- **Favicon SVG:** simple monogram "JC" or silhouette; or use a tool like https://realfavicongenerator.net/
- **apple-touch-icon.png (180×180):** scaled from favicon or headshot
- **Effort:** Medium (~30 min — mostly OG image design) • **Pros:** proper social unfurls

### Option B: Use headshot as-is for all three
- Crop headshot to 1200×630 for OG (no text overlay — letterboxed face)
- Scale headshot down to 180×180 for apple-touch
- Generate favicon.svg with simple "JC" text
- **Effort:** Small (~15 min) • **Cons:** OG preview is just a floating face, less shareable

### Option C: Remove the broken references
- Delete the `<meta>` / `<link>` lines that reference missing files
- **Effort:** Tiny • **Cons:** worse share previews than Option A/B

## Technical Details

Files to create:
- `/Users/jameschang/Projects/jameschang.co/assets/og-image.png` (1200×630)
- `/Users/jameschang/Projects/jameschang.co/assets/favicon.svg`
- `/Users/jameschang/Projects/jameschang.co/assets/apple-touch-icon.png` (180×180)

Favicon quick stub:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" rx="16" fill="#a03623"/>
  <text x="50" y="68" text-anchor="middle" font-family="serif"
        font-size="56" font-weight="500" fill="#faf8f5">JC</text>
</svg>
```

OG image can be built in Figma, Canva, or via a tool like https://www.opengraph.xyz/.

## Acceptance Criteria

- [ ] All three files exist in `/assets/`
- [ ] `curl -sI https://jameschang.co/assets/og-image.png` returns 200
- [ ] LinkedIn share preview shows the OG image with title + description
- [ ] Chrome/Safari tab shows favicon
- [ ] iOS "Add to Home Screen" shows the apple-touch-icon

## Work Log

_(blank)_

## Resources

- Security review (P3-5)
- README.md "Missing before launch" section
- https://realfavicongenerator.net/ (favicon generator)
- https://www.opengraph.xyz/ (OG image generator)
