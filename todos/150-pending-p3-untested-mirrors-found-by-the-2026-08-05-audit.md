---
status: pending
priority: p3
issue_id: "150"
tags: [testing, docs-index, now-page, enumeration-decay, audit]
dependencies: []
---

## Problem Statement

Two instances of the enumeration-decay / one-directional-assertion class found by
the 2026-08-05 audit remain open. Both are lower severity than the five closed the
same day, which is why they were deferred rather than skipped. Full class write-up:
`docs/solutions/integration-issues/hand-listed-ci-test-files-silently-exclude-new-tests.md`.

## 1. `admin/docs` has no disk-vs-index parity test

`docs/guides` and `docs/solutions` both got disk-derived set-equality tests
(`test_every_guide_on_disk_and_the_test_plan_are_indexed`,
`test_all_solutions_on_disk_are_indexed`). `admin/docs` — the **largest** root at 43
docs — has only shape and path-existence checks, i.e. the direction already covered.

**Regression it would catch:** `adapt_hub` returns `None` for any doc whose
frontmatter lacks `type:`. Lose that one line while reformatting a PRD and the doc
vanishes from the /admin board — no error, no log anyone reads, green suite.
`test_committed_index_matches_a_fresh_rebuild` cannot help: both sides come from the
same builder, so a doc missing from the index is missing from both.

**Needs an allowlist.** Three files are legitimately frontmatter-free today:
`admin/docs/README-DOCS.md` (the system's map), and the `notes.md` / `roadmap.md`
stubs under `admin/docs/projects/aleph/`. Same `DELIBERATE_OMISSIONS` shape as
`TestSitemap::test_every_public_page_is_in_the_sitemap`.

## 2. `now/project-cards.js` embeds a drifted, untested project array

The file carries a 10-project data array that includes `slug: 'wcrn'` — which has
never existed in `bin/projects-config.json` — and is missing `vouch`, `tip`, and
`family-sites`. No test references the file.

**Currently inert:** the `DOMContentLoaded` auto-render line is commented out by
design (CLAUDE.md: it would overwrite the cron's live shipped timestamps). So this
is latent, not live.

**Regression it would cause:** uncommenting that one line — which CLAUDE.md
documents as the supported way to activate the JS layer — renders a phantom project
and drops three real ones onto `/now`.

**Options:** (a) delete the file if the JS layer is not going to be used; (b) add a
test asserting its slug set matches `projects-config.json`; (c) generate the array
from config at build time instead of hand-maintaining it. (a) is cheapest and (c)
removes the mirror entirely — the file has not been activated in the ~2 months since
it was added.

## Why deferred

Neither breaks a live page today. #1 is board-only; #2 is behind a commented-out
line. Both were found during a documentation pass, and closing them was outside the
scope of that pass. Recorded here so the audit's tail doesn't evaporate.
