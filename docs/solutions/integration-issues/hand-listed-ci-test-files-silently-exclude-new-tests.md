---
title: "CI ran 157 of 525 tests for four months — the workflow named test files explicitly, so every file added after it was written was silently excluded"
slug: hand-listed-ci-test-files-silently-exclude-new-tests
category: integration-issues
tags: [ci, github-actions, testing, coverage, silent-failure, observability, config-drift, enumeration-decay, paths-ignore, one-directional-assertion, allowlist, set-equality, phantom-enforcement]
symptom: "every push showed a green Tests check while 368 of 525 tests — including every test for the feed sync scripts, the project classifier, the docs index, and the credential-expiry checker — were never executed"
root_cause: "the workflow invoked pytest with explicit filenames (`pytest tests/test_shared.py tests/test_feeds.py`) rather than a directory. That list was complete and correct on the day it was written, when exactly three test files existed. Ten more were added over the following 106 days and none was ever registered, because a test file that is merely NOT LISTED produces no failure — the omission and full success emit an identical green check. A second, compounding half: `paths-ignore` included `docs/**`, which skipped CI entirely on docs-only commits, disabling the one test that catches docs-index drift precisely on the commits where that drift occurs."
module: ci + test guards (.github/workflows/ci-tests.yml, tests/test_site_e2e.py, tests/test_docs_index.py, .git/hooks/pre-commit)
date_solved: 2026-08-05
severity: high
---

# A hand-listed CI test set decays into a green check that proves nothing

This is not a story about a careless config. The config was **correct when it was
written** and became wrong by standing still, one safe-looking commit at a time.

## Symptom

There wasn't one. That is the entire problem.

Every push to `main` showed a green **Tests** check. The suite grew from 71 tests to
525. The counts in `README.md`, `CLAUDE.md`, and commit messages tracked that growth
faithfully. Nothing was ever red that should have been green, and nothing looked
wrong at any point.

The gap only surfaced during an unrelated stack-detection sweep, when the workflow
file was read for the first time in months:

```yaml
- name: Run unit tests
  run: python -m pytest tests/test_shared.py tests/test_feeds.py -v
- name: Run E2E tests
  run: python -m pytest tests/test_site_e2e.py -v
```

Measured against the pre-fix tree (`e0dc859`):

```
pytest tests/ --collect-only                                       → 503 tests
pytest tests/test_shared.py tests/test_feeds.py tests/test_site_e2e.py → 157 tests
```

**157 of 503 ran. 31%.**

## Investigation

### The list was right on day one

`ab66b6c` (2026-04-19, *"Add test suite: 71 tests (unit + E2E) with CI workflow"*)
created the workflow. At that commit:

```
$ git ls-tree ab66b6c tests/
tests/test_feeds.py
tests/test_shared.py
tests/test_site_e2e.py
```

Three test files; the workflow named all three. **100% coverage at authoring time.**
There was no mistake to catch in review.

`git log` shows only three commits ever touched the file: the creation, an Actions
version bump (`770a2d9`, which didn't touch the pytest lines), and the fix. **The
list was never edited across 108 days and ten new test files.**

### How it decayed

| Test file | Added | Tests today | Ever in the CI list? |
|---|---|---|---|
| `test_shared.py` | 2026-04-19 | 48 | **yes** — day 1 |
| `test_feeds.py` | 2026-04-19 | 11 | **yes** — day 1 |
| `test_site_e2e.py` | 2026-04-19 | 98 | **yes** — day 1 |
| `test_trakt.py` | 2026-04-21 | 10 | no |
| `test_projects.py` | 2026-04-22 | 94 | no |
| `test_feed_builders.py` | 2026-04-22 | 20 | no |
| `test_spotify.py` | 2026-04-22 | 20 | no |
| `test_whoop.py` | 2026-04-22 | 21 | no |
| `test_gcal.py` | 2026-05-07 | 32 | no |
| `test_project_docs.py` | 2026-05-29 | 78 | no |
| `test_feed_health.py` | 2026-06-03 | 5 | no |
| `test_docs_index.py` | 2026-07-23 | 47 | no |
| `test_check_expiry.py` | 2026-07-24 | 41 | no |

*(Counts are a snapshot from 2026-08-05, the day of the fix — the suite is 550 today.
`docs/test-plan.md` is the maintained inventory; this column is history, not a live
figure. Likewise "503" below is measured at the pre-fix commit `e0dc859`, while the
fix commit message cites 525 against the working tree of that moment; both are correct
for their trees.)*

Two details make the pattern worse than "someone forgot."

**Drift began two days after CI was created.** The commit that introduced it —
`2a6d3f0`, *"Add 14 tests (Trakt + GA4 + privacy) and sync all docs (86 total)"* —
**updated the documented test count and not the workflow.** The number was maintained
as prose; the executable list was not. Three days later, 137 tests existed and 81 ran.

**The visible metric actively suppressed suspicion.** "503 tests" was never a false
statement. It was simply never *the* number that mattered, and it rose steadily for
four months while the executed number sat still.

**There was never a performance argument.** The whole suite runs in under three
seconds.

### What was actually unguarded

The blind spot was not a random 69%. It was **100% of the tests for every feed sync
script, the project classifier, the roadmap adapters, the docs index, the
credential-expiry checker, and the staleness monitor.** The 157 that ran covered
shared helpers, one legacy feed file, and the HTML/E2E surface.

Three concrete regressions that could have shipped green:

1. **A secret leaking into a committed public artifact.**
   `tests/test_docs_index.py::TestExclusionsAndRealIndex::test_committed_index_is_public_safe`
   scans the committed `admin/docs/index.json` — a generated file that embeds the
   rendered HTML of every hub doc. Its sibling asserts no entry in
   `bin/build-docs-index.py`'s `ROOTS` can reach the gitignored `docs/superpowers/`,
   `docs/archive/`, or `docs/screenshots/`. A one-line widening of `ROOTS` sweeps
   gitignored design specs into a committed JSON file **in a public repo**, with CI
   green. This guard landed 2026-07-23 — into a CI config that had already been
   stale for three months.

2. **The regression test for an outage that already happened.**
   `tests/test_whoop.py::TestWhoopApiErrorSkipsHeartbeat` and the Spotify equivalent
   encode the heartbeat-correctness invariant from a real July 2026 incident
   ([`feed-heartbeat-on-noop-path-hides-upstream-api-failure.md`](./feed-heartbeat-on-noop-path-hides-upstream-api-failure.md)).
   The test written *because the bug shipped once* was never executed by CI.

3. **Injection from a third-party feed.**
   `tests/test_gcal.py::TestRender::test_javascript_url_not_rendered_as_anchor`
   pushes `URL:javascript:alert(1)` through the iCal parser and asserts no live
   anchor is emitted. The Google Calendar feed is external input rendered into a
   published page.

Also unrun: the four idempotency classes guarding the `content_changed()` invariant
(nondeterminism there makes every cron run commit forever), and the 12 `TestLoadConfig`
assertions over `bin/projects-config.json`, whose failure mode is a crashed 6 AM cron.

## The fix

```yaml
- name: Run unit tests
  run: python -m pytest tests/ --ignore=tests/test_site_e2e.py -v

- name: Run E2E tests
  run: python -m pytest tests/test_site_e2e.py -v
```

**Glob the directory; make the exception an exclusion, not an inclusion.** This is
the load-bearing detail:

- An **inclusion** list decays *dangerously* — a forgotten entry runs nothing, silently.
- An **exclusion** list decays *safely* — a forgotten entry runs an extra test.

E2E stays a separate step only for a readable log, and it is `--ignore`d from the
first step rather than the first step naming its members.

### The second half: `paths-ignore`

```yaml
paths-ignore:
  - 'todos/**'
  - '.feeds-heartbeat.json'
  - '.spotify-state.json'
```

`docs/**` and root `*.md` were removed. They were harmless while `test_docs_index.py`
never ran in CI; the moment globbing brought it into scope they became actively
harmful, because that file exists to catch **one** mistake — editing a doc without
re-running `bin/build-docs-index.py` — and a docs-only commit is exactly when that
mistake happens.

| Commit shape | CI runs? | Index guard effective? |
|---|---|---|
| `docs/foo.md` + rebuilt `admin/docs/index.json` | yes (`admin/` not ignored) | yes |
| `docs/foo.md` alone, rebuild forgotten | **no** | **no** — stale index ships |

`todos/**` stays ignored; verified that no test reads it (it appears only in
docstrings).

### Verification

Switching CI to the whole suite risks a test that is green locally only because of a
file CI never sees. Checked explicitly by removing the gitignored
`tests/fixtures/*roadmap*.md` and re-running: `TestCopyMapCompletenessLocal` **skips
cleanly with a reason** rather than erroring (`426 passed, 1 skipped`). Also ran
without `.env` sourced, so no local secret propped anything up.

## Prevention

### Name the class

> A configuration that **enumerates** the members of a set that is expected to grow,
> where discovery was done once by a human and never again. Correct at birth, wrong
> by increments, and each increment costs nothing to skip.

**Why it is invisible:** the failure mode of omission is a **green check**. Every
other CI failure announces itself. This one emits a signal *identical* to full
success, and nobody re-reads a passing workflow. It is also anti-correlated with
attention — the moment you add a test file is the moment you are focused on the code
under test, not on a registry three directories away. And here the drift accumulated
in the direction that *feels* like added safety.

### The rule

**Prefer discovery over enumeration. When you must enumerate, make the enumeration
assert its own completeness against the thing it mirrors.**

In descending order of preference:

1. **Glob it.** Prefer `pytest tests/` and `--ignore` the exceptions.
2. **If enumeration is load-bearing** (a security boundary, an ordering), pair it
   with a set-difference assertion derived from the filesystem — not a hand-typed
   magic number.
3. **Ask of any allowlist: what does adding a member look like, and what happens if
   I forget?** If the answer to the second is "nothing," it will happen.
4. **A claim that something is enforced must name the enforcer, in a form you can
   grep.** "The pre-commit hook enforces this" survived in two documents for months
   because it was unfalsifiable at a glance. "`ci-tests.yml` runs `pytest tests/`" can
   be checked in five seconds — and a claim that can be checked is a claim that will
   be.

### Other instances of this shape in this repo — audited

**Found by this audit, and closed the same day (2026-08-05):**

- `tests/test_site_e2e.py` `EXPECTED_MARKERS` — a hand-list of 14 feed markers,
  checked in one direction only (list ⊆ page). Currently in sync, but adding a feed
  and forgetting to register its marker yields a green check on an unguarded marker
  pair — and a missing marker pair is precisely what makes a cron "silently skip that
  page forever." Fix: assert the page's marker set **equals** `EXPECTED_MARKERS`, or
  derive the expected set from the `replace_marker()` call sites.
  **→ CLOSED.** `TestFeedMarkers::test_no_marker_on_the_page_is_unguarded` regexes
  every `<!-- X-START -->` off the page and asserts `on_page - set(EXPECTED_MARKERS)`
  is empty. Set-equality was chosen over deriving from `replace_marker()` call sites —
  those are spread across five scripts, so deriving would have re-created the
  enumeration problem one layer over. `TLDR-{slug}` markers are excluded by prefix
  (generated per project by `render_card()`, not bootstrap markers); that exclusion is
  itself an allowlist of one, and the weakest joint in the new guard.
- `TestSitemap::test_sitemap_urls_resolve` — one-directional (sitemap → files). The
  reverse currently has four unlisted pages, all intentional (`/admin/` is noindex,
  the OAuth callbacks are utility pages), but a genuinely new public page would be
  absent from the sitemap with CI green.
  **→ CLOSED.** `TestSitemap::test_every_public_page_is_in_the_sitemap` computes
  `set(HTML_FILES) - listed - DELIBERATE_OMISSIONS`, and the four predicted pages are
  its four entries, each with an inline reason. Note the shape of the fix: the
  exemption did not disappear, it moved from *implicit* (absent, invisible) to
  *explicit* (listed, so a new page forces a decision) — the same inclusion→exclusion
  inversion this doc argues for above.

**Still open:**

- `bin/build-docs-index.py` `ROOTS` — see below. A new top-level `docs/` subdirectory
  is silently invisible to the board, and no test forces a decision about it. This is
  the only instance from the original audit that has not been closed.

**Legitimate exceptions, documented as such:**

- `bin/build-docs-index.py` `ROOTS` — a 4-entry allowlist whose comment reads *"NEVER
  glob `docs/**`"*. Here the enumeration **is** the security boundary and globbing
  would be the bug. It still decays in the other direction: a new top-level `docs/`
  subdirectory is silently invisible to the board, with no test forcing a decision.
- `PROJECT_DOCS` in `update-project-docs.py` and `GUIDANCE` in `check-feed-health.py`
  — both already guarded, the latter with an explicit `_fallback_guidance()` prefix
  match so an unlisted slug degrades to generic text rather than vanishing.

**Good pattern already dominant:** `tests/test_site_e2e.py` derives `HTML_FILES` from
a recursive glob and computes `STANDARD_PAGES` / `NAV_PAGES` / `DEEP_DIVES` from it by
filter. `test_all_solutions_on_disk_are_indexed` globs and compares sets, with the
docstring *"Count-from-disk, not a magic number."* The right instinct was already in
the codebase — it just hadn't reached the workflow file.

### A related documentation inaccuracy — FIXED 2026-08-05, and it names a second class

`relative-time-html-defeats-content-changed-cache.md` claims *"Pre-commit hook running
the test suite enforces that the no-op assertion still passes."* It does not —
`.git/hooks/pre-commit` is a filename blocklist and never invokes pytest. Combined
with the CI gap, the `content_changed` invariant had **neither** of its two documented
enforcement points actually running for the untested files. CLAUDE.md and the project
memory carry the same overstatement. Either correct the claim or make it true.

> **Resolution: both, deliberately.** The hook gained a real test gate (`SKIP_TESTS=1`
> to bypass; the suite runs in ~3s, so there was no cost argument), *and* the false
> claims were corrected in place rather than quietly overwritten. Making a claim true
> does not retire the lesson, because the lesson is not about this hook.
>
> **Name the second class — it is not enumeration decay.** That is a *config* that
> stops describing a set. This is a *document* describing a guard that was never
> built: **phantom enforcement**. It is worse in one specific way — enumeration decay
> leaves a real runnable artifact you can go read, whereas a phantom guard is
> load-bearing *belief*. Two documents deferred to "the pre-commit hook covers it" for
> months without anyone opening a 40-line shell script sitting in the repo.
>
> A second instance surfaced the same day: `CLAUDE.md` also claimed the hook was
> "version-controlled; distribute to teammates via git clone." `.git/hooks/` is never
> tracked by git — a fresh clone has no hook at all.

## See also

- [`feed-heartbeat-on-noop-path-hides-upstream-api-failure.md`](./feed-heartbeat-on-noop-path-hides-upstream-api-failure.md) — the same shape one layer down. That doc's rule, *"a heartbeat must mean 'upstream really succeeded,' never 'the script didn't crash'"*, translates exactly: a green check must mean "the suite passed," never "the two files someone listed in April passed."
- [`marker-boundary-content-staleness.md`](./marker-boundary-content-staleness.md) — the general principle this is an instance of: *a monitor is blind outside its declared contract surface.* Substitute "test suite" for "monitor" and "the hand-listed pytest args" for "contract surface."
- [`../security-issues/secret-leak-guard-for-generated-committed-public-artifact.md`](../security-issues/secret-leak-guard-for-generated-committed-public-artifact.md) — its entire guard lives in `tests/test_docs_index.py`, which was **doubly dark**: absent from the CI arg list *and* skipped by `paths-ignore` on docs-only commits.
- [`github-repo-rename-redirect-silently-orphans-project-events.md`](./github-repo-rename-redirect-silently-orphans-project-events.md) — its 2026-08-05 hardening shipped `TestRepoKeyMismatch` into `tests/test_projects.py`, a file CI had never executed until hours later the same day.
- [`../logic-errors/activity-recency-misreads-maintenance-mode-as-active-work.md`](../logic-errors/activity-recency-misreads-maintenance-mode-as-active-work.md) — same epistemology from the other end: a test that *cannot fail* and a test that *never runs* are both non-evidence.
