---
status: done
priority: p3
issue_id: 028
tags: [code-review, performance, images]
dependencies: []
---

# Re-encode headshot-640.webp at lower quality — reclaim ~3 KB

## Problem

`assets/headshot-640.webp` grew from 17.8 KB → 21.4 KB when regenerated from the new source. Cost to retina users. Marginal.

## Proposed Solutions

Re-encode `headshot-640.webp` at `-q 75` (was `-q 82`):
```bash
cwebp -q 75 assets/headshot-640.png -o assets/headshot-640.webp
```
Tradeoff: minor visual quality loss at 2x retina on a 160 px displayed avatar. Indistinguishable in practice.

## Acceptance Criteria
- [ ] `headshot-640.webp` under 18 KB
- [ ] No visible quality drop at normal viewing scale

## Resources
- performance-oracle review 2026-04-15, P2
