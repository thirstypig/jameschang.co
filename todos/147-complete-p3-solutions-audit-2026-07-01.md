---
status: complete
priority: p3
issue_id: "147"
tags: [code-review, documentation, audit]
dependencies: []
---

## Quarterly Solutions Audit — 2026-07-01

Audited all 19 docs under `docs/solutions/` against current repo state.
Verified file paths, test class/function names, numeric counts, and cross-references.

### Summary

- **Total docs scanned:** 19
- **VERIFIED:** 11 (all testable claims match)
- **DRIFTED:** 7 (at least one stale claim per doc)
- **UNVERIFIABLE:** 1 (`sips-cropoffset-centers-instead-of-top-origin.md` — purely tooling advice, no repo-specific file paths)

---

### DRIFTED docs

- **`accessibility/wcag-contrast-light-mode-accent-muted.md`** (date_solved: 2026-04-16)
  - `component:` field names `styles.css` — file does not exist (replaced by `notebook.css` in the 2026-04-27 notebook redesign).

- **`integration-issues/cron-script-config-driven-content-rendering.md`** (resolved: 2026-06-25)
  - Claims "Applied to all 9 projects: aleph, fantastic-leagues, bahtzang-trader, judge-tool, tabledrop, tastemakers, thirsty-pig, ktv-singer, jameschang-co." — `bin/projects-config.json` now has 10 projects (vouch added 2026-07-01).

- **`integration-issues/per-project-adapters-for-heterogeneous-roadmap-sources.md`** (date_solved: 2026-05-29)
  - Claims "59 tests" in `tests/test_project_docs.py` — file now has 63 test methods (4 added since the doc was written).

- **`security-issues/csp-unsafe-inline-removal-via-script-externalization.md`** (date_solved: 2026-04-28)
  - Claims "18 HTML pages (16 standard + 2 OAuth callbacks)." — now 20 HTML pages (18 standard + 2 callbacks). New pages added since writing: `bucketlist/index.html`, `projects/fantastic-leagues/ai-insights/index.html`, `projects/fantastic-leagues/analytics/index.html`. The test `test_csp_homogeneous_across_15_pages` and its comment reference "15 of 16 pages" but the HOMOGENEOUS_CSP_PAGES set is built dynamically so the logic is correct — only the doc's count and the test name/comment are stale.

- **`ui-bugs/css-dark-mode-dual-selector-consistency.md`** (resolved: 2026-04-18)
  - `components:` lists `work/work.css` and `styles.css` — neither file exists (retired with the 2026-04-27 notebook redesign; `work/work.css` was renamed/retokenised into `projects/projects.css`).

- **`ui-bugs/print-stylesheet-project-card-layout-line-wrapping.md`** (resolved: 2026-06-23)
  - Claims 5 specific test methods in `tests/test_site_e2e.py::TestPrintStylesheet`: `test_print_card_name_font_size`, `test_print_card_single_line`, `test_print_no_wrapping_mid_project_name`, `test_print_flex_properties_present`, `test_resume_pdf_project_section_visual`. None of these method names exist in `TestPrintStylesheet` (the class has 7 methods with different names).

- **`ui-bugs/project-card-styling-consistency-rollout-to-all-nine.md`** (resolved: 2026-06-23)
  - Claims "All 347 tests pass" — total is now 375.
  - Claims 9 projects — now 10 (vouch added 2026-07-01).

---

### Recommendation

Low urgency — all drifted claims are in doc metadata/counts, not in the operational fix itself. The core lessons remain valid. Update the 7 drifted docs to reflect current state; highest priority is the `print-stylesheet-project-card-layout-line-wrapping.md` doc since its claimed test methods simply don't exist (they may have been planned but not implemented under those names).

---

## Re-run + resolution — 2026-07-13

Re-audited **all 21 docs** under `docs/solutions/` (was 19 at the 2026-07-01 pass; `feed-heartbeat-on-noop-path-hides-upstream-api-failure.md` and `spotify-development-mode-lockdown-strands-personal-app-feed.md` were added since). Run via 3 parallel audit agents cross-checked against the live repo (`pytest --collect-only`, file existence, `grep` for test/class names, cross-reference resolution).

**Result: 9 VERIFIED, 10 DRIFTED (all fixed this pass), 2 low-nit-only.** Counts had drifted *further* since 2026-07-01 (projects 10→11 with `spar`; tests 375→381).

Fixed — **surgical** (clean current-state pointer errors):
- `per-project-adapters…`: `59 tests` → 63; cron `14:15 UTC` → 13:15 UTC.
- `self-referential…`: "one of the 10 configured projects" → 11.
- `feed-heartbeat…`: stale inline line refs (WHOOP `:278/:283`→`:301/:306`; projects `:556/:561`→`:585/:590`).
- `print-stylesheet…`: **5 cited test names never existed** — replaced with the one real guard (`test_print_card_name_overrides_screen_size`) + a note the single-line/no-wrap/flex/SSIM tests are unwritten candidates.
- `relative-time…`: two cited `test_strip_volatile_*` names don't exist — marked illustrative + pointed to the real `TestContentChanged` guards; `now/now.js` upgrader ref `88-112`→`310-334`.

Fixed — **frontmatter retarget** (retired files):
- `wcag-contrast…`: `component: styles.css` annotated RETIRED 2026-04-27 (tokens now in `notebook.css`; `--muted` gone).
- `css-dark-mode…`: `components: work/work.css + styles.css` → `notebook.css` / `projects/projects.css` (both retired in the notebook redesign).

Fixed — **dated audit banner** (historical counts preserved, current state noted rather than falsifying a dated narrative):
- `csp-unsafe-inline…`: 18→20 HTML pages / 16→18 standard / 15→17 homogeneous.
- `project-card-…-all-nine`: 9→11 projects, 347→381 tests (the "all nine" narrative is left intact as historical).
- `cron-script-config-driven…`: 9→11 projects.

Left as historical prose (accurate to the event, low value to change): `plex…` (token sent as header vs the documented query param), `static-site-branding…` (prose says "7 AM PT"; cron is 6 AM PT).

All fixes are doc-metadata/reference corrections — no operational lesson changed. **Resolved.**
