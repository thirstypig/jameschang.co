---
status: done
priority: p3
issue_id: 071
tags: [code-review, performance, images]
dependencies: []
---

# Image optimization: oversized headshots + work screenshots lack AVIF

## Problem Statement
Two image optimization opportunities:

1. **Oversized headshots**: Secondary headshots (2-7) are served at source dimensions (up to 1244x803) for a 160x160 CSS display (320x320 at 2x). Total AVIF weight for headshots 2-7: ~177 KB. If resized to 320x320, each would be ~5-8 KB. Secondary headshots also lack srcset 1x/2x variants.

2. **Work screenshots lack AVIF**: 12 work subpage screenshots use bare `<img src="...webp">` without `<picture>` wrappers or AVIF variants. Homepage case study images use `<picture>` with AVIF and see ~35-40% compression improvement. Worst offenders: `judge-tool/live-home.webp` (270 KB, 1425x6173), `fantastic-leagues/live-home.webp` (127 KB, 1425x3336).

## Proposed Solutions

### Headshots: Resize to 320x320 and add srcset
Batch resize all headshot images and add 1x (160px) / 2x (320px) variants with proper srcset.
- **Effort:** Medium
- **Risk:** None

### Screenshots: Generate AVIF variants and wrap in <picture>
Convert WebP screenshots to AVIF, wrap in <picture> elements across 12 HTML files.
- **Effort:** Medium-Large (batch conversion + 12 file edits)
- **Risk:** None

## Acceptance Criteria
- [ ] All headshot images sized appropriately for display context
- [ ] Secondary headshots have srcset with 1x/2x variants
- [ ] Work subpage screenshots wrapped in `<picture>` with AVIF sources

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |
