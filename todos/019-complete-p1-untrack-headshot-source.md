---
status: pending
priority: p1
issue_id: 019
tags: [code-review, performance, security, assets]
dependencies: [018]
---

# Untrack 2.7 MB headshot source PNG — deploys to Pages but is never referenced

## Problem

`assets/JamesChang.Headshot.png` ships as `https://jameschang.co/assets/JamesChang.Headshot.png` even though zero HTML/CSS references it. Bandwidth waste + every `git clone` pulls 2.7 MB.

Commit `2e1eaa0` had already untracked it; commit `40612ee` accidentally re-added it when regenerating variants from the new source.

## Proposed Solutions

### Option A (Recommended): gitignore + untrack (keep file on disk)
```bash
git rm --cached assets/JamesChang.Headshot.png
echo "assets/JamesChang.Headshot.png" >> .gitignore
git add .gitignore
git commit -m "Untrack 2.7 MB headshot source (stripped + regen workflow)"
```
- Source stays on disk for future regens
- Stops deploying to Pages
- Git history past that point no longer bloats with blob on every commit

### Option B: Move source outside the repo
- Keep in `~/Pictures/site-sources/` or similar
- Document path in `bin/README.md`
- Cleanest long-term; slightly less portable across machines

## Dependencies

Must happen **after** metadata strip (todo #018) — otherwise the untracked file on disk still has the leaky XMP.

## Acceptance Criteria
- [ ] `curl -sI https://jameschang.co/assets/JamesChang.Headshot.png` returns 404
- [ ] `git ls-files | grep JamesChang.Headshot.png` returns empty
- [ ] `.gitignore` contains the path
- [ ] Local source still exists for regens

## Resources
- performance-oracle review 2026-04-15, P1
