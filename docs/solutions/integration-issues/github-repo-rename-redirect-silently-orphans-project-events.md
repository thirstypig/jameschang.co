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
`fetch_repo_events()`, `bin/update-projects.py:157`:

```python
url = f"https://api.github.com/repos/{repo}/events?per_page=100"
```

`repo` here is the configured string (`thirstypig/spar`). The call returns 200, so
line 164 runs `_events_ok += 1` and the function returns the data. It never looks at
what the response says the repo is actually named.

**2. The results are keyed by GitHub's belief** —
`parse_events()`, `bin/update-projects.py:214` and `:249`:

```python
repo = ev.get("repo", {}).get("name", "")   # -> "thirstypig/TIP"
...
by_repo[repo].append(entry)                  # keyed under the NEW name
```

**3. The lookup uses the config's belief again** —
`most_recent_event_time()`, `bin/update-projects.py:370–377`:

```python
shipping_repos = project.get("shipping_repos") or [project["repo"]]
latest = None
for r in shipping_repos:                     # "thirstypig/spar"
    for ev in events_by_repo.get(r, []):     # miss -> [] -> loop never runs
        ...
return latest                                # None
```

`events_for_project()` (`:276–285`) misses identically, which is why the card also
lost its "shipped" line.

**4. `None` means back-burner** — `classify_projects()`, `:380–397`:

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
The guard that came out of it is at `bin/update-projects.py:513`:

```python
if _events_ok == 0 and _events_err > 0:
```

That is deliberately **systemic-only** — it catches a dead `TLDR_FETCH_TOKEN`
(every repo 401s) without letting one flaky repo abort the whole run. A renamed repo
produces a genuine `_events_ok += 1`, so the gate is never even close to firing, and
`record_heartbeat("projects")` at `:590` runs clean with no `error=`.

The distinction worth internalizing: the earlier bug was **the fetch failed and we
didn't notice**. This one is **the fetch succeeded and we misfiled the result**. No
error-handling guard, however careful, will catch the second class — there is no
error. The data is correct; the *attribution* is wrong.

That also means it never self-heals. It recurs identically on every run until a
human edits the config, and no monitor will ever say so.

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

### 2. The hardening (designed, not yet built — `todos/149`)

`fetch_repo_events()` is the right place: it is the only function holding both the
configured name and the raw response at once. A single string compare per repo:

```python
data = fetch_json(url, headers=headers, timeout=15) or []
_events_ok += 1
# GitHub 301-redirects a renamed repo's /events endpoint, so a 200 does NOT
# prove the config string is still the repo's real name. Every event stamps
# repo.name with the CURRENT name; compare it against what we asked for, or
# these events get keyed under a name most_recent_event_time() never looks up.
if data:
    returned = data[0].get("repo", {}).get("name", "")
    if returned and returned.lower() != repo.lower():
        _renamed_repos.append((repo, returned))
```

Two open design questions, both genuine:

**Warn only, or also self-heal by re-keying?** Self-healing keeps the page correct
with zero intervention. But GitHub's rename redirect is a courtesy, not a contract —
it can lapse if the old name is claimed by someone else. Silently depending on it
means the config stays wrong indefinitely and the same failure returns later, with
nobody able to connect "TIP went dark" to "renamed eight months ago." If you
self-heal, you **must** also nag, or you have only deferred the bug and made it
harder to diagnose.

**How loud?** `record_heartbeat("projects", error=..., partial_success=True)`
refreshes `last_success_utc` while recording `last_error`, so it shows in
`.feeds-heartbeat.json` without tripping the 48h monitor. That fits a transient
partial skip — but a rename is *permanent and self-perpetuating* until fixed by
hand, which is arguably the opposite of what `partial_success` was designed for. The
stronger option is to extend `bin/check-feed-health.py` to treat a non-empty
`last_error` as issue-worthy even when `last_success_utc` is fresh, reusing the
GitHub-issue channel that already emails on creation rather than inventing a new one.

### 3. Regression tests

The bug mechanism is testable without any network. Sketch, in the style of
`tests/test_projects.py`:

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

Plus, once the hardening lands: mismatch detected; names matching (false-positive
guard); an empty event list (no `repo.name` to compare — must not be read as a
rename); and case-only differences (`spar` vs `Spar` is the same repo, not drift).

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
- `todos/149-pending-p2-repo-rename-silently-misclassifies-project.md` — the open work item tracking the hardening above.
