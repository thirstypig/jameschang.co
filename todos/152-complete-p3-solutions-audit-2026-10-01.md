---
status: complete
priority: p3
issue_id: "152"
tags: [code-review, documentation, audit]
dependencies: []
---

## Quarterly Solutions Audit — 2026-10-01

Audited all 21 docs under `docs/solutions/` against current repo state.
Verified file paths, test class/function names, numeric counts, and cross-references.

### Summary

- **Total docs scanned:** 21
- **VERIFIED:** 13 (all testable claims match)
- **DRIFTED:** 5 (at least one stale claim per doc — all fixed this pass)
- **UNVERIFIABLE:** 3 (external systems: macOS sips behavior, Plex relay IP, Spotify vendor policy)
- **Historical-only:** 3 (pre-notebook-redesign; wcag-contrast, css-dark-mode, oauth-rotation — no current repo claims to verify; acknowledged in doc text)

---

### DRIFTED docs (all fixed in this pass)

- **`integration-issues/cron-script-config-driven-content-rendering.md`** (resolved: 2026-06-25)
  - Audit note said "it now holds **12**" — `bin/projects-config.json` now has **13** projects (`pasadenaworks` added 2026-09-01).
  - Fixed: "12" → "13", added `pasadenaworks` to the parenthetical list.

- **`integration-issues/per-project-adapters-for-heterogeneous-roadmap-sources.md`** (date_solved: 2026-05-29)
  - Claimed "63 tests" in `tests/test_project_docs.py` — file now has **87** test methods.
  - Aleph roadmap path in body text and example code was `docs/plans/roadmap.md` — actual path in the `PROJECT_DOCS` adapter call (line 861) and confirmed by `CLAUDE.md` is `docs/product/roadmap.md`.
  - Fixed: test count 63 → 87; both path references `docs/plans/` → `docs/product/`.
  - Also fixed the same stale path in three comments/docstrings in `bin/update-project-docs.py` (lines 16, 344, 366).

- **`logic-errors/self-referential-repo-event-floating-project-card.md`** (date: 2026-06-13)
  - Said "`jameschang-co` is one of the **12** configured projects" — now **13**.
  - Fixed: "12" → "13".

- **`integration-issues/hand-listed-ci-test-files-silently-exclude-new-tests.md`** (date_solved: 2026-08-05)
  - Count note said "the suite is **550** today" — `CLAUDE.md` confirms **609** tests as of 2026-10-01.
  - Fixed: 550 → 609, added date "(2026-10-01)".

- **`ui-bugs/project-card-styling-consistency-rollout-to-all-nine.md`** (resolved: 2026-06-23)
  - Audit note (stamped 2026-08-05) said "Current state (2026-08-05): **12** projects … and **520** tests" — now **13** projects and **609** tests.
  - Fixed: date stamp 2026-08-05 → 2026-10-01, project count 12 → 13, added `pasadenaworks`, test count 520 → 609.

---

### Fixes also applied to source code

- `bin/update-project-docs.py` — three comments/docstrings referenced the old Aleph roadmap path `docs/plans/roadmap.md` while the actual adapter call on line 861 already used `docs/product/roadmap.md`. Fixed to match.

---

### Recommendation

All fixes are metadata/count corrections — no operational lesson changed. The next audit should check whether `per-project-adapters` test count drifts again as `test_project_docs.py` grows (it went 59 → 63 → 87 across three audits).
