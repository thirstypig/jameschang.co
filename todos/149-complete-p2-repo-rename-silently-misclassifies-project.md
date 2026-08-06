---
status: complete
priority: p2
issue_id: "149"
tags: [cron, classification, now-page, monitoring, reliability]
dependencies: []
---

## Problem Statement
Renaming a source repo on GitHub silently forces its project to **back-burner** on
`/now`, with no error, no failed workflow, and a green heartbeat.

Found 2026-08-04: `thirstypig/spar` was renamed to `thirstypig/TIP`, but
`bin/projects-config.json` still said `thirstypig/spar`. The project had pushed to
`main` ~1 day earlier and was rendering as back-burner.

## Root Cause
GitHub **redirects** `/repos/{old-name}/events` to the renamed repo, so
`fetch_repo_events()` receives a normal **HTTP 200 with real event data** —
`_events_ok` increments, nothing is logged, the workflow succeeds.

But the response body stamps each event with the **new** name
(`repo.name = "thirstypig/TIP"`), and `parse_events()` keys `by_repo` off that value
(`bin/update-projects.py:214`). `most_recent_event_time()` then looks the events up
by the **config** string `thirstypig/spar` (`:370–377`) — a key miss — and returns
`None`, which `classify_projects()` reads as "no events" → back-burner.

Confirmed in the production cron log for run `30923706241` (2026-08-04T15:21Z):

```
  vouch: 1 event
  spar: 0 events        ← 200 OK, real data, zero attributed
```

with **no** `events fetch failed` line — proving the fetch succeeded and the loss
happened at the key lookup, not the network.

## Why existing guards miss it
The heartbeat-correctness guard added 2026-07-10 only bails on the *systemic* case
(`_events_ok == 0 and _events_err >= 1` — a dead `TLDR_FETCH_TOKEN`). A single
renamed repo is indistinguishable from a project that is genuinely quiet, so it
records a healthy heartbeat and the 48h staleness monitor never fires. Same class of
failure as `docs/solutions/integration-issues/feed-heartbeat-on-noop-path-hides-upstream-api-failure.md`,
but one level deeper — the fetch really did succeed; the *attribution* is what broke.

Note: fine-grained PATs select repositories by **ID**, not name, so `TLDR_FETCH_TOKEN`
access survives a rename — the token is not the failure point and needs no re-grant.

## Immediate fix (done 2026-08-04)
`bin/projects-config.json` updated to `thirstypig/TIP` for both `repo` and
`shipping_repos[]`; slug renamed `spar` → `tip` across config, portfolio, docs hub,
and tests. TIP now classifies as active.

## Hardening (built 2026-08-05)
`repo_key_mismatch(configured_repo, events)` in `bin/update-projects.py` returns the
name GitHub actually filed the events under when it differs from the configured
string. `fetch_repo_events()` calls it on every successful fetch, appends any hit to
`_repo_key_mismatches`, and logs a warning naming the fix. `mismatch_heartbeat_kwargs()`
turns the accumulated pairs into `record_heartbeat("projects", error=…,
partial_success=True)` at both success exits in `main()` — so the mismatch lands in
`.feeds-heartbeat.json` as `last_error` while `last_success_utc` still refreshes and
the 48h staleness monitor does not false-trip.

Three decisions worth recording:

- **Exact comparison, not rename-detection.** The invariant is "does the config
  string equal the key `parse_events()` files these events under" — so a case-only
  drift, which breaks the dict lookup just as completely, is reported too.
- **Report-only; explicitly NOT self-healing.** Re-keying to the returned name would
  keep the card correct and thereby remove the only pressure to fix the config,
  masking the very drift the warning exists to surface. Reporting a wrong answer
  loudly beats silently producing a right one from stale config.
- **Known blind spot.** A repo with zero events carries no name to compare, so a
  rename on a genuinely quiet repo stays undetectable. Acceptable: with no activity,
  back-burner is the correct classification regardless.

Verified against the live config — no false positives across the public repos,
including the mixed-case `thirstypig/TheFantasticLeagues`. Tests:
`tests/test_projects.py::TestRepoKeyMismatch` (8).

## Convention added
`CLAUDE.md` now states the rule: **when a source repo is renamed, update `repo` +
`shipping_repos[]` in the same change.**
