---
status: done
priority: p1
issue_id: 003
tags: [code-review, performance, cls, images]
dependencies: []
---

# Work-page screenshots: 7.12 MB total, no width/height (CLS failures)

## Problem Statement

The 35 PNGs under `/assets/work/` total **7.12 MB raw**. Individual /work/*/ pages load 1.0–1.3 MB each (e.g., `/work/fantastic-leagues/tech/` = 1,253 KB of PNGs). Worse: every `<img class="screenshot">` in the /work/ tree is missing `width`/`height` attributes, and the aspect ratios vary wildly (some images are 1425×6173 — a 4.3:1 aspect ratio at full page capture). This guarantees CLS >0.1 on /work/*/ pages as lazy-loaded images complete — failing the 2026 Core Web Vitals threshold.

Biggest offenders:
- `judge-tool/live-home.png` — 1425×6173, **808 KB**
- `aleph/roadmap.png` — 1200×862, 436 KB
- `fantastic-leagues/11-home-dashboard.png` — 1512×862, 415 KB
- `aleph/changelog.png` — 1200×862, 394 KB

## Findings

From performance-oracle agent (P1, second finding):
- 35 PNGs totaling 7.12 MB
- Zero images have `width`/`height` attrs → CLS risk
- WebP Q80 would cut 65–75%; AVIF Q55 would cut 80–85%
- Ultra-tall full-page screenshots (3,128–6,173 px tall) are being displayed at ~900 px CSS width — over-rendered

## Proposed Solutions

### Option A: WebP-convert all 35 + add width/height attrs
- Batch-convert via `cwebp` at Q80
- Script to auto-generate the `width`/`height` attrs from ImageMagick `identify` output
- Update each HTML file to point at `.webp`
- **Effort:** Medium (~45 min) • **Savings:** ~5 MB • **Pros:** good compatibility (WebP universal in 2026) • **Cons:** no AVIF

### Option B (Recommended): WebP + downscale ultra-tall screenshots
- Same as A, plus resize images wider than 1600 px to max 1600 px first
- Judge-tool `live-home.png` drops from 808 KB to ~120 KB
- **Effort:** Medium (~1 hour) • **Savings:** ~5.5 MB • **Pros:** best perf • **Cons:** slightly more work

### Option C: AVIF + WebP + PNG `<picture>` per screenshot
- Maximum compression, triple-source markup
- **Effort:** Large (~2 hours with 35 images × 3 encodings) • **Savings:** ~6 MB • **Pros:** absolute best • **Cons:** scope creep for a portfolio page nobody will load on a cold cache

## Technical Details

Batch script (Option B):
```bash
cd /Users/jameschang/Projects/jameschang.co/assets/work
for png in $(find . -name "*.png"); do
  # Downscale if wider than 1600px
  WIDTH=$(sips -g pixelWidth "$png" | awk '/pixelWidth/ {print $2}')
  if [ "$WIDTH" -gt 1600 ]; then
    sips --resampleWidth 1600 "$png" --out "$png.tmp" && mv "$png.tmp" "$png"
  fi
  # Convert to WebP
  cwebp -q 80 "$png" -o "${png%.png}.webp"
done
```

HTML update helper (python one-liner):
```python
# For each <img class="screenshot" src="X.png">, add width/height from identify
# and swap .png → .webp
```

Every image HTML element needs:
```html
<img src="/assets/work/path/file.webp" width="1425" height="6173"
     alt="..." class="screenshot" loading="lazy" decoding="async">
```

## Acceptance Criteria

- [ ] Total `/assets/work/` weight ≤ 2 MB
- [ ] No image wider than 1600 px
- [ ] Every `<img class="screenshot">` has explicit `width` and `height`
- [ ] `/work/*/` pages have Lighthouse CLS ≤ 0.05
- [ ] All images load and render correctly on https://jameschang.co
- [ ] Original PNGs deleted from repo (or archived outside git)

## Work Log

_(blank)_

## Resources

- Performance audit output
- 11 /work/*/ HTML files with screenshot references
- `work/work.css:340` — `.screenshot` base styles
