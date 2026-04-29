---
status: pending
priority: p2
issue_id: 111
tags: ['code-review', 'css', 'performance', 'print-pipeline']
dependencies: []
---

# Orphan print order rules + gtag-init.js not deferred

## Problem Statement
Two unrelated small drifts:

1. **Orphan print order rules** in `notebook.css`. `.nb-hero { order: 0 }` (line 1321) and `.nb-footer { order: 8 }` (line 1329) are listed in the print flex order ladder, but the same selectors are `display: none !important` at lines 1212/1223. Same at line 1328: `#contact { order: 7 }` while `<section id="contact" class="nb-footer-contact">` is hidden via the `.nb-footer-contact` rule. Dead order assignments. Either remove or convert to a comment documenting intent.

2. **`gtag-init.js` not deferred.** `<script src="/assets/js/gtag-init.js"></script>` blocks parsing while the file fetches (~2-5ms). The script only pushes to `dataLayer`; running after parse is correct. Add `defer`. Affects 16 HTML pages.

**Surfaced by:** architecture-strategist + performance-oracle during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Two-line cleanup
- Remove the 3 orphan order rules (or comment them)
- Add `defer` attribute to gtag-init.js script tag (sed across 16 files)
- **Effort:** Trivial (~10 min)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] Print order block in notebook.css has no rules for `display: none` sections
- [ ] `<script src="/assets/js/gtag-init.js" defer></script>` on every HTML page
- [ ] resume.pdf renders identically (regenerate + spot-check)
- [ ] GA4 still records pageviews (verify in Real-Time)

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
