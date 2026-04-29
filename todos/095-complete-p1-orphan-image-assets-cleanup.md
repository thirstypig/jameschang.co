---
status: complete
priority: p1
issue_id: 095
tags: ['code-review', 'performance', 'assets']
dependencies: []
---

# ~6.7 MB of orphan image assets bloat repo and slow CI checkouts

## Problem Statement
At least 18 large `.png` / `.jpg` files in `/assets/` are not referenced by any HTML, CSS, JS, or Python. Cumulative ~6.7 MB. Slows `git clone` and every cron-runner checkout (saves ~2-5s per CI run × 6 active workflows).

Confirmed orphans (file + size):
- `assets/JamesChang.Headshot.png` (2.6 MB)
- `assets/TFL.Admindashboard.png` (1.14 MB)
- `assets/work/fantastic-leagues/11-home-dashboard.png` (807 KB)  *(WebP+AVIF still referenced)*
- `assets/work/fantastic-leagues/admin-dashboard-full.png` (586 KB)  *(WebP+AVIF still referenced)*
- `assets/aleph.admindashboard.png` (570 KB)
- `assets/IMG_0416 copy_cleanup.jpg` (560 KB)
- `assets/JamesProProfile.png` (526 KB)
- `assets/work/fantastic-leagues/team-page-ai.png` (498 KB)
- ~10 more (Screenshot 2026-04-17, James Chang.Eye.jpg, localiq-*, now-*, thirstypig-home.png, x_DSC3049.jpg, etc.)

**⚠️ Verify before deleting:** `headshot-320.png` IS referenced — agent flagged it but it's used.

**Surfaced by:** performance-oracle during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Grep-then-git-rm sweep
- For each candidate: `git grep -l "filename" || git rm assets/filename`
- Commit as `chore(assets): drop N orphan images`
- **Effort:** Small (~30 min including double-checks)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] Each orphan confirmed unreferenced via `git grep` before deletion
- [ ] `headshot-320.png` (and any other near-named asset) verified before sweep
- [ ] Tests pass after deletion (`tests/test_site_e2e.py` checks asset references)

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
