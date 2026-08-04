---
status: complete
priority: p3
issue_id: "146"
tags: [code-review, content, consistency]
---

## Problem Statement
The `snapshot-banner` div was removed from `projects/judge-tool/tech/index.html` (because the live `/tech` URL at thejudgetool.com/tech was broken), but the same banner remains on `projects/judge-tool/roadmap/index.html` and `projects/judge-tool/changelog/index.html`, both linking to their respective live URLs (`thejudgetool.com/roadmap`, `thejudgetool.com/changelog`).

## Findings
- **Removed from:** `projects/judge-tool/tech/index.html`
- **Still present:** `projects/judge-tool/roadmap/index.html:105–108`, `projects/judge-tool/changelog/index.html:105–108`
- **Reason for removal:** Live `/tech` link was broken at time of commit
- **Caught by:** security-sentinel during /ce:review on 2026-05-13

## Proposed Solutions

**Option A — Remove banners from roadmap + changelog too**
Consistent with tech page. Simple. Loses the "live version" link for users who want to navigate to the live app.

**Option B — Restore banner on tech page when live /tech link is fixed**
When `thejudgetool.com/tech` is back up, restore the snapshot-banner on tech to match roadmap/changelog.

**Option C — Leave as-is**
Cosmetic asymmetry only. The `test_deep_dive_block_order` test now handles optional banners correctly. No functional impact.

## Acceptance Criteria
- [x] All three judge-tool sub-pages have consistent banner presence (all or none)

## Work Log
- 2026-05-13: Identified during /ce:review. Low priority — no functional or security impact.
- 2026-06-25: Resolved via Option A. Removed snapshot-banner divs from `projects/judge-tool/roadmap/index.html` and `projects/judge-tool/changelog/index.html` for consistency with tech page (which has no banner). Implementation in commit 5292f04.
