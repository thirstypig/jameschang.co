---
status: pending
priority: p1
issue_id: 002
tags: [code-review, performance, lcp]
dependencies: []
---

# Headshot is 514 KB PNG for a 160 px circle — LCP killer

## Problem Statement

`/assets/headshot.png` is **535×579 px, 526,376 bytes** and renders inside a 160×160 CSS box (120 px on mobile). The file is:
1. **~3.3× oversized in pixels** — DPR2 only needs ~320 px wide
2. **Wrong format** — PNG for a photographic portrait; WebP/AVIF would drop 80–95%
3. **The LCP element** on the homepage (preloaded with `fetchpriority="high"`)

Expected LCP impact: 300–800 ms improvement on Slow 4G once fixed.

## Findings

From performance-oracle agent (P1):
- Raw: 514 KB → target ~8–25 KB (AVIF or WebP at 320×320)
- Serves as LCP; currently preloaded so it's on the critical render path
- `.headshot { width: 100% }` inside a 160 px column — intrinsic size irrelevant past 320 px DPR2

Total homepage weight drops from ~570 KB to ~65 KB. Single biggest perf win in the audit.

## Proposed Solutions

### Option A: Single WebP at 320 px (simple)
- Resize headshot to 320×320 px, convert to WebP Q80 (~15 KB)
- Update `<img src="/assets/headshot.webp" width="320" height="320" ...>`
- Keep `.png` as fallback via `<picture>` if desired
- **Effort:** Small (~10 min) • **Pros:** trivial, huge win • **Cons:** no AVIF

### Option B (Recommended): `<picture>` with AVIF + WebP + PNG fallback
- Generate `headshot-320.avif` (~8 KB), `headshot-320.webp` (~15 KB), keep `headshot-320.png` (~60 KB) as fallback
- Use `<picture>` with `<source>` elements
- Add `srcset` for 2x retina (`headshot-640.avif` etc.)
- **Effort:** Small (~15 min) • **Pros:** maximum compatibility + best perf • **Cons:** 3 files vs 1

### Option C: Drop the headshot entirely
- Hero currently shows headshot in the About section (not in hero itself)
- Could remove it to ship even faster
- **Effort:** Tiny • **Cons:** loses personal touch; user already decided to keep it

## Technical Details

Commands (Option B, using `cwebp` and `avifenc`):
```
cd /Users/jameschang/Projects/jameschang.co/assets
sips --resampleHeightWidth 320 320 headshot.png --out headshot-320.png
cwebp -q 80 headshot-320.png -o headshot-320.webp
avifenc --min 25 --max 35 headshot-320.png headshot-320.avif
# 2x variants
sips --resampleHeightWidth 640 640 headshot.png --out headshot-640.png
cwebp -q 80 headshot-640.png -o headshot-640.webp
avifenc --min 25 --max 35 headshot-640.png headshot-640.avif
```

HTML change (`index.html:159` area):
```html
<picture>
  <source srcset="/assets/headshot-320.avif 1x, /assets/headshot-640.avif 2x" type="image/avif">
  <source srcset="/assets/headshot-320.webp 1x, /assets/headshot-640.webp 2x" type="image/webp">
  <img src="/assets/headshot-320.png" alt="James Chang" class="headshot"
       width="320" height="320" loading="eager" fetchpriority="high" decoding="async">
</picture>
```

Update preload (`index.html:33`): remove the preload — `fetchpriority="high"` on the img does the same thing and is `<picture>`-compatible.

Also update JSON-LD `image` reference to the new file.

## Acceptance Criteria

- [ ] Homepage LCP element is <50 KB (preferably <20 KB)
- [ ] `<img>` has explicit `width` and `height` attributes
- [ ] `<picture>` serves AVIF → WebP → PNG fallback chain
- [ ] Homepage Lighthouse perf score ≥ 98
- [ ] Visual quality indistinguishable at 160 px and 320 px (zoomed)
- [ ] JSON-LD `image` field points to a valid URL

## Work Log

_(blank)_

## Resources

- Performance audit output
- `index.html:33, 159` (preload link + img tag)
- MDN: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/picture
