---
status: complete
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

## Resolution — 2026-09-01

**#1 — parity test added.** `test_every_admin_doc_on_disk_is_indexed` in
`tests/test_docs_index.py`, the third such check after guides and solutions;
`admin/docs` was the largest root and the only one without one.

The discovery rule turned out to be already encoded in `iter_root_files()`
(skip `_templates/`, skip `_`-prefixed filenames), so of 8 unindexed files 5
are excluded *by rule* and only the 3 predicted frontmatter-free stubs needed
allowlisting. The test walks disk applying that rule itself rather than calling
`iter_root_files()` — otherwise a bug in discovery would be mirrored into the
expectation instead of failing. A sibling test
(`test_admin_doc_omission_allowlist_has_no_stale_entries`) fails if an
allowlisted stub later gains frontmatter or is deleted, so the exemption list
cannot quietly outlive its files and mask a real regression at that path.

Verified by stripping `type:` from a real PRD
(`admin/docs/projects/aleph/prds/PRD-001-cpc-certificate.md`) and confirming
the test goes red, then restoring it — not by watching a green run.

**#2 — `now/project-cards.js` deleted** (option (a)). By 2026-09-01 the file
was referenced by **zero HTML and zero JS**, its auto-render had been commented
out for ~3 months, and its array carried a phantom `wcrn` while missing four
real projects (`family-sites`, `pasadenaworks`, `tip`, `vouch`) — the drift had
widened, not held.

The case for keeping it was that it's a fallback if the cron dies. The evidence
killed that: activating it the documented way would have rendered a project that
has never existed and silently dropped four that do. **It was not a fallback, it
was a trap with instructions attached** — and CLAUDE.md carried the
instructions. Both the file and that paragraph are gone, along with its line in
`docs/guides/cron-scripts-operations.md`'s file tree.

**General lesson.** A mirror survives on the assumption that someone will notice
when it drifts. Nobody does, because a mirror nothing renders produces no signal
at all — the drift here was found by an audit, not by use. So a mirror needs a
test at birth or it needs deleting; there is no stable third state.
