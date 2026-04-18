---
title: "macOS sips --cropOffset ignores offset and crops from center"
slug: sips-cropoffset-centers-instead-of-top-origin
category: tooling
tags: [sips, macos, image-processing, python-pil, cropping]
severity: moderate
component: "bin/ (image prep scripts), asset pipeline"
symptom: "Dashboard screenshots cropped with sips -c lost their header/hero section — crop was taken from the vertical center instead of the top edge"
root_cause: "sips -c always crops from the center of the image. --cropOffset does not shift the origin to (0,0) top-left as expected."
date_solved: 2026-04-17
---

# macOS sips crops from center, not top — use PIL instead

## Problem

When preparing dashboard screenshots for the Aleph and TFL deep-dive pages, `sips -c 1400 1764 --cropOffset 0 0` was expected to keep the top 1400px of a 2424px image. Instead, it cropped from the vertical center, cutting off the "Dashboard" title, hero metric (81%), and progress bar.

## Root cause

`sips -c` (crop to height/width) computes the crop region from the **center** of the source image. The `--cropOffset` flag is documented to shift the crop origin, but in practice it behaves inconsistently — the crop remains center-anchored on macOS. This contradicts typical image-editing conventions where `(0, 0)` means top-left.

## Solution

Use Python PIL for top-anchored crops:

```python
from PIL import Image

img = Image.open('source.png')
desired_height = 1400
cropped = img.crop((0, 0, img.width, desired_height))  # (left, top, right, bottom)
cropped.save('output.png')
```

Then generate web formats:

```bash
cwebp -q 80 output.png -o output.webp
avifenc --min 20 --max 35 output.png output.avif
```

## Prevention

1. **Never use `sips -c` for directional crops.** It always centers. Use PIL, ImageMagick (`convert -crop WxH+0+0`), or `vips` instead.
2. **Always verify crop output visually** before generating optimized variants — check that the expected top/header content is preserved.
3. PIL's `Image.crop()` box tuple is `(left, top, right, bottom)` — explicit, no ambiguity about anchor point.
