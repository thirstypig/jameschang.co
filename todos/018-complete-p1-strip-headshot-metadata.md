---
status: done
priority: p1
issue_id: 018
tags: [code-review, security, privacy, assets]
dependencies: []
---

# Strip XMP/EXIF metadata from headshot PNG (Canva + Meta tracking IDs leaking)

## Problem

`assets/JamesChang.Headshot.png` (2.7 MB) is committed + served, and `exiftool` on it returns:

- `Attrib:Data` — Canva document ID, user ID, brand-kit ID
- `Attrib:FbId 525265914179580` — Meta/Facebook tracking ID
- `pdf:Author: Jimmy C`
- `dc:title: Untitled design - 1`
- `xmp:CreatorTool: Canva (Renderer) doc=... user=... brand=...`
- Created date (2026-03-05)

All reachable via `curl https://jameschang.co/assets/JamesChang.Headshot.png | exiftool -`.

Also: the already-generated responsive variants (`headshot-320.png`, `headshot-640.avif`, etc.) were rendered from this source and may inherit some of the metadata.

## Proposed Solutions

### Option A (Recommended): Strip metadata in place + regenerate variants
```bash
exiftool -all= assets/JamesChang.Headshot.png
# Then regenerate 320/640 variants from the stripped source (see bin/ history)
# Strip the already-committed variants too:
exiftool -all= assets/headshot-*.png assets/headshot-*.webp assets/headshot-*.avif
exiftool assets/JamesChang.Headshot.png  # verify: should be empty
```
Small (~5 min) • Low risk • Keeps source in repo for regen workflow

### Option B: Re-untrack the 2.7 MB source (pairs with todo #019 which handles the Pages-serving concern)
Strip + don't track.

### Option C: Do Option A AND Option B
Recommended: strip metadata from all variants, keep the stripped source in repo (so regenerate-from-source works), **also** gitignore + rm --cached per todo #019. The `-all=` step is independent of deploy hygiene.

## Acceptance Criteria
- [ ] `exiftool assets/JamesChang.Headshot.png` shows no XMP/Attrib/pdf:Author
- [ ] Same for all `assets/headshot-*.{png,webp,avif}` variants
- [ ] Visual parity — crops + resize unchanged

## Resources
- security-sentinel review 2026-04-15, P1.2
- performance-oracle review 2026-04-15, P1 (bandwidth aspect)
