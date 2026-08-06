---
title: "Renaming a GitHub source repo silently forced its project to back-burner — the redirect returned HTTP 200 while re-stamping the repo name, so the lookup key missed"
category: integration-issues
tags: [sync-pipeline, cron, github-api, github-events, redirect, projects-sync, classification, heartbeat, silent-failure, observability, config-drift]
symptom: "a project on /now sat in the back-burner section despite having pushed to main a day earlier; the projects-sync workflow succeeded, logged no error, and left a fresh heartbeat"
root_cause: "the source repo was renamed on GitHub (thirstypig/spar -> thirstypig/TIP) but bin/projects-config.json still held the old name. GitHub redirects /repos/{old}/events to the renamed repo, so fetch_repo_events() received a real HTTP 200 with real events and incremented _events_ok. But every event in the response body stamps repo.name with the NEW name, and parse_events() keys its by_repo dict off that returned value, while most_recent_event_time() looks events up by the OLD configured string — an exact-string dict miss returns None, which classify_projects() reads as 'no events' and demotes to back-burner."
module: now-page-sync-pipeline (bin/update-projects.py, bin/projects-config.json, bin/_shared.py)
date_solved: 2026-08-04
severity: medium
---

# Renaming a GitHub source repo silently orphans its events

> **Update (2026-08-05):** the hardening proposed in §2 was **built**, and `todos/149`
> is closed. Everything from "Symptom" through "The fix" describes the 2026-08-04
> incident as it happened and is left in its original tense; §2 and §3 have been
> rewritten to present tense. **One piece of the original guidance was wrong and has
> been inverted** — the proposed case-insensitive name comparison would have created
> a real blind spot. See §2 for the corrected reasoning.

A repo rename is a routine, deliberate act. It should not be able to quietly
misrepresent your portfolio for an unbounded stretch of time — but here it did,
because every layer that could have complained got a well-formed success.

## Symptom

On `/now`, the project card for TIP sat in the **back-burner** section. It had
merged a PR and pushed to `main` roughly 23 hours earlier — comfortably inside the
`ACTIVE_THRESHOLD_DAYS = 7` window that should have placed it in **active**.

Everything that could have flagged it looked healthy:

- the `projects-sync` workflow **succeeded** (33s, green check)
- there was **no** `events fetch failed` line in the log
- `.feeds-heartbeat.json` showed a **fresh** `last_success_utc` for `projects`
- the 48h staleness monitor stayed quiet — correctly, by its own rules

The only visible trace was one line in the production run log
(run `30923706241`, 2026-08-04T15:21Z), and it reads as unremarkable:

```
  vouch: 1 event
  spar: 0 events        ← HTTP 200, real data, zero attributed
  jameschang-co: 1 event
```

`0 events` is indistinguishable from a genuinely quiet project. That is the whole
problem.

## Investigation

The repo had been renamed `thirstypig/spar` → `thirstypig/TIP`, while
`bin/projects-config.json` still carried the old name in both `repo` and
`shipping_repos[]`.

The intuition — "then the fetch must be 404ing" — is wrong, and checking it is what
cracked the case:

```bash
$ gh api repos/thirstypig/spar --jq '.full_name'
thirstypig/TIP
```

GitHub **redirects** a renamed repo's API endpoints. The request succeeds. And the
events it returns are real:

```bash
$ gh api 'repos/thirstypig/spar/events?per_page=100' \
    --jq '.[] | [.type, .repo.name, .created_at] | @tsv' | head -3
DeleteEvent        thirstypig/TIP    2026-08-03T16:24:25Z
PushEvent          thirstypig/TIP    2026-08-03T16:24:23Z
PullRequestEvent   thirstypig/TIP    2026-08-03T16:24:22Z
```

Note the middle column. We asked for `spar`; every event is stamped `TIP`.

## Root cause

Two functions disagree about what the repo is called, and nothing reconciles them.

**1. The request is built from the config's belief** —
`fetch_repo_events()` in `bin/update-projects.py`:

```python
url = f"https://api.github.com/repos/{repo}/events?per_page=100"
```

`repo` here is the configured string (`thirstypig/spar`). The call returns 200, so
`_events_ok += 1` runs and the function returns the data. It never looks at
what the response says the repo is actually named.

**2. The results are keyed by GitHub's belief** —
`parse_events()` in `bin/update-projects.py`:

```python
repo = ev.get("repo", {}).get("name", "")   # -> "thirstypig/TIP"
...
by_repo[repo].append(entry)                  # keyed under the NEW name
```

**3. The lookup uses the config's belief again** —
`most_recent_event_time()`:

```python
shipping_repos = project.get("shipping_repos") or [project["repo"]]
latest = None
for r in shipping_repos:                     # "thirstypig/spar"
    for ev in events_by_repo.get(r, []):     # miss -> [] -> loop never runs
        ...
return latest                                # None
```

`events_for_project()` misses identically, which is why the card also
lost its "shipped" line.

**4. `None` means back-burner** — `classify_projects()`:

```python
if latest is not None and latest > cutoff:
    active.append(slug)
else:
    backburner.append(slug)                  # <- lands here
```

So: a 200 response, real data in hand, `_events_ok` incremented, and the project
still reads as dormant.

## Why the existing guards all miss it

This repo already learned the lesson that a cron script must not record a healthy
heartbeat on a path a swallowed error could reach
(see [`feed-heartbeat-on-noop-path-hides-upstream-api-failure.md`](./feed-heartbeat-on-noop-path-hides-upstream-api-failure.md)).
The guard that came out of it, in `main()`:

```python
if _events_ok == 0 and _events_err > 0:
```

That is deliberately **systemic-only** — it catches a dead `TLDR_FETCH_TOKEN`
(every repo 401s) without letting one flaky repo abort the whole run. A renamed repo
produces a genuine `_events_ok += 1`, so the gate is never even close to firing, and
the success-path `record_heartbeat("projects", ...)` calls ran clean with no `error=` (before the 2026-08-05 hardening; they now carry `mismatch_heartbeat_kwargs()`).

The distinction worth internalizing: the earlier bug was **the fetch failed and we
didn't notice**. This one is **the fetch succeeded and we misfiled the result**. No
error-handling guard, however careful, will catch the second class — there is no
error. The data is correct; the *attribution* is wrong.

That also means it never self-heals. It recurs identically on every run until a
human edits the config.

*(As of 2026-08-05 something does now say so — see §2. The mismatch is logged and
recorded as `last_error` in `.feeds-heartbeat.json`. It still does not open a GitHub
issue: `bin/check-feed-health.py` gates only on `last_success_utc` age, so a fresh
heartbeat carrying an error is rendered into an issue body but never triggers one.)*

## The fix

Update `bin/projects-config.json` so config and GitHub agree again:

```json
{
  "slug": "tip",
  "repo": "thirstypig/TIP",
  "name": "TIP",
  "shipping_repos": ["thirstypig/TIP"]
}
```

Re-running the sync immediately reclassified it:

```
Updated now/index.html. Active: 8 (aleph, fantastic-leagues, tip, vouch,
thirsty-pig, tabledrop, bahtzang-trader, jameschang-co); back-burner: 3
(tastemakers, ktv-singer, judge-tool).
```

**One thing that is *not* part of the fix:** the PAT. Fine-grained personal access
tokens select repositories by **ID**, not by name, so `TLDR_FETCH_TOKEN` access
survives a rename untouched — no re-grant, no rotation. The production log proves
it: the redirected fetch returned private-repo data successfully. Do not go hunting
for a token problem here.

## Prevention

### 1. The convention (cheapest, and the actual root-cause fix)

**When a source repo is renamed on GitHub, update `repo` and every
`shipping_repos[]` entry in `bin/projects-config.json` in the same change.** Do not
rely on the redirect. Now recorded in `CLAUDE.md` under the project-cards config
section.

This is worth stating plainly because the failure is *invisible*: nothing will
remind you, and the redirect makes everything appear to work.

### 2. The hardening (BUILT 2026-08-05 — `todos/149` closed)

`fetch_repo_events()` was the right place: it is the only function holding both the
configured name and the raw response at once. What shipped, in
`bin/update-projects.py`:

- `repo_key_mismatch(configured_repo, events)` — returns the name GitHub filed the
  events under, or `None` when they agree.
- `_repo_key_mismatches` — module-level accumulator of `(configured, actual)` pairs.
- `mismatch_heartbeat_kwargs()` — turns the accumulated pairs into
  `record_heartbeat()` kwargs.
- A call inside `fetch_repo_events()` right after `_events_ok += 1`, which logs a
  warning naming the fix, and both success-path `record_heartbeat("projects",
  **mismatch_heartbeat_kwargs())` calls in `main()`.

```python
for ev in events:
    name = ((ev.get("repo") or {}).get("name") or "").strip()
    if name and name != configured_repo:
        return name
return None
```

**The comparison is EXACT, and that is the corrected part of this document.** An
earlier draft of this section proposed `returned.lower() != repo.lower()` and
asserted that case-only differences were "the same repo, not drift." That was
wrong for this codebase, and adopting it would have built a blind spot into the one
guard whose entire job is to eliminate blind spots.

The reason is that the invariant being protected is **not** "was this repo renamed."
It is "will the configured string equal the dict key these events land under."
`parse_events()` keys `by_repo` off the response's `repo.name`; `most_recent_event_time()`
looks up with `events_by_repo.get(r, ...)` using the config string. Python dict keys
hash case-sensitively, and `.get()` never invokes `defaultdict.__missing__` — so
config `thirstypig/spar` against a returned `thirstypig/Spar` misses just as totally
as a full rename, returns `None`, and demotes the project. A case-insensitive
compare would suppress the warning for a drift that still silently breaks the page.

There is also no false-positive cost to being exact: `fetch_repo_events()` is called
with the same strings from `shipping_repos_for()` that are later used as lookup keys,
so an exact mismatch is proof of a real lookup failure, never a cosmetic one.

Both open design questions were resolved:

**Warn only, or also self-heal by re-keying? → Warn only.** Self-healing would keep
the page correct with zero intervention, and that is exactly the objection: it
removes the only pressure to fix the config. GitHub's rename redirect is a courtesy,
not a contract — it can lapse if the old name is claimed by someone else — so a
self-healed page would go dark much later with nobody able to connect "TIP went
quiet" to "renamed eight months ago." Reporting a wrong answer loudly beats silently
producing a right one from stale config. Pinned by
`test_fetch_records_mismatch_and_still_returns_the_data`, which asserts the returned
data is passed through untouched.

**How loud? → `partial_success=True`.** This section previously argued *against*
that option on the grounds that a rename is permanent and self-perpetuating, which is
the opposite of the transient partial skip `partial_success` was built for. The
counter-argument that won: the sync genuinely ran and produced a correct page for
every other project, so freezing `last_success_utc` would false-trip the 48h monitor
and train you to ignore it. The mismatch needs to be *visible*, not *paging*.

The stronger option this section originally preferred — extending
`bin/check-feed-health.py` to treat a non-empty `last_error` as issue-worthy even
when `last_success_utc` is fresh — was **not** built. That remains the open upgrade
path: today the mismatch surfaces only in `.feeds-heartbeat.json` and the run log,
so it is discoverable but not pushed to you.

### 2b. Known blind spot

A repo with **zero events** carries no `repo.name` to compare against, so a rename on
a genuinely quiet repo is undetectable. This is accepted rather than solved: with no
activity, back-burner is the correct classification regardless, so the
misclassification the guard exists to prevent cannot occur. The gap only closes when
the repo becomes active again — at which point the guard fires on the first event.

### 3. Regression tests

`tests/test_projects.py::TestRepoKeyMismatch` — 8 tests, no network required:

| Test | Pins |
|---|---|
| `test_returns_new_name_when_events_are_attributed_elsewhere` | the core detection |
| `test_returns_none_when_names_agree` | false-positive guard |
| `test_returns_none_for_empty_events` | the §2b blind spot, asserted rather than left implicit |
| `test_case_only_difference_is_reported` | the inverted guidance — case-only drift **must** flag |
| `test_malformed_events_are_skipped_not_crashed` | events with no `repo` key or a blank name |
| `test_fetch_records_mismatch_and_still_returns_the_data` | report-only; data passes through untouched |
| `test_heartbeat_is_clean_when_no_mismatches` | no false `last_error` on a healthy run |
| `test_heartbeat_is_partial_success_when_mismatched` | `partial_success=True` + both names in the note |

**Still missing, and worth adding.** Nothing tests the *raw mechanism* — the dict
miss itself, independent of the detector. Both `events_for_project()` and
`most_recent_event_time()` remain untested against events keyed under a different
name, which is the actual bug this document is about:

```python
def test_events_for_project_misses_events_keyed_under_new_name(self):
    """Reproduces the raw mechanism: events keyed by the NEW repo name,
    config still pointing at the OLD one -> zero events attributed."""
    project = {"slug": "tip", "repo": "thirstypig/spar",
               "shipping_repos": ["thirstypig/spar"]}
    events_by_repo = {"thirstypig/TIP": [_push_event("thirstypig/TIP")]}
    assert _projects.events_for_project(project, events_by_repo) == []
    assert _projects.most_recent_event_time(project, events_by_repo) is None
```

The detector tests prove the *warning* fires. This would prove the *damage* it warns
about — so a future refactor that normalizes keys (and thereby fixes the bug) fails
loudly here instead of leaving eight tests guarding a problem that no longer exists.

### 4. Name the general class

The transferable lesson is broader than repo renames:

> An upstream API can return **HTTP 200 with semantically shifted data** — a
> redirect, a renamed field, a schema version bump. Error handling cannot see this.
> Whenever a local identifier is used *both* to build a request *and* to look up its
> response, verify the response still agrees with the identifier you sent.

Worth checking at every seam where config and an upstream service each hold a name:
Goodreads shelf IDs, Plex library names, calendar feed IDs. And before considering
any rename done, grep the whole repo for the literal old string.

## See also

- [`feed-heartbeat-on-noop-path-hides-upstream-api-failure.md`](./feed-heartbeat-on-noop-path-hides-upstream-api-failure.md) — the direct predecessor: a heartbeat recorded on a path reachable after a swallowed error. This bug is one level deeper — the fetch genuinely succeeded, so that guard cannot help.
- [`cron-script-config-driven-content-rendering.md`](./cron-script-config-driven-content-rendering.md) — same script, same config-as-source-of-truth theme; the adjacent failure mode where hand-edits inside markers are overwritten.
- [`../logic-errors/self-referential-repo-event-floating-project-card.md`](../logic-errors/self-referential-repo-event-floating-project-card.md) — same `classify_projects()` machinery, also silently wrong output with a green run.
- [`marker-boundary-content-staleness.md`](./marker-boundary-content-staleness.md) — the broader principle: a monitor is blind outside its declared contract surface.
- [`../logic-errors/activity-recency-misreads-maintenance-mode-as-active-work.md`](../logic-errors/activity-recency-misreads-maintenance-mode-as-active-work.md) — the **inverse** failure on this same classification path. Here the machinery lost a real signal and wrongly demoted a project; there the signal was real but meant something other than what the section heading claims. Debugging "why is this project in the wrong section?" should check this doc's heartbeat `last_error` **first** — a mismatch is a bug to fix, not a case for the `pin` override.
- `todos/149-complete-p2-repo-rename-silently-misclassifies-project.md` — the work item, closed 2026-08-05, recording the three implementation decisions (exact compare, report-only, known blind spot).
