---
status: complete
priority: p3
issue_id: "148"
tags: [cron, content, classification, now-page]
dependencies: []
---

## Problem Statement
`bin/update-projects.py` classifies a project as **active** when its most recent
`PushEvent` / `PullRequestEvent` / `ReleaseEvent` across `shipping_repos[]` is less
than `ACTIVE_THRESHOLD_DAYS = 7` old. It has no concept of *what the commit was for*,
so a housekeeping commit mirrored across every repo promotes every project at once.

Observed 2026-08-04: `vouch`, `thirsty-pig`, `tabledrop`, and `bahtzang-trader` were
all rendering as **active** on `/now` on the strength of a single fan-out chore —
`chore: sync port registry — shengchangmd claims block 3120` — merged into each repo
within ~90 seconds of the others on 2026-07-30T06:09–06:10Z. None had shipped real
product work in that window (their prior real commits were 7/23–7/24).

This is not rare: the same fan-out happened 2026-07-23 (`docs(ports): sync port
registry — add vouch (3020) and spar (3110)`), so it fires roughly whenever a new
project claims a port block — twice in the two weeks before this was noticed.

## Findings

**A naive prefix filter does NOT work.** The same logical chore appears under at
least three different message shapes, and a legitimate commit shares one of them:

| repo | message | is it a fan-out chore? |
|---|---|---|
| tabledrop | `Merge pull request #13 from thirstypig/chore/port-registry-3120` | yes |
| bahtzang-trader | `docs(ports): sync port registry — add vouch (3020) and spar (3110)` | yes |
| tabledrop | `Merge pull request #12 from thirstypig/chore/test-coverage-and-doc-sync` | **no — real work** |
| vouch | `chore(docs): refresh generated stats after #20 (#21)` | **no — real work** |

So filtering on `chore:` or `chore/` would drop genuine work. The narrow signal that
actually separates them is the substring **"port registry"**.

**Cost.** Private-repo events have their payload stripped — `payload.commits[]` is
empty (verified against `thirstypig/tabledrop`), same reason `PullRequestEvent`
payloads are dropped at `bin/update-projects.py:238`. So any message-based filter
needs a `/repos/{repo}/commits/{sha}` fetch per candidate event, walking down the
list until a non-chore is found. `MAX_COMMIT_ENRICHMENTS = 15` would likely need
raising (11 projects across ~16 repos, walk depth 1–2 observed).

## Options

1. **Do nothing.** The promotion self-corrects after 7 days. Zero code, zero risk,
   but `/now` misrepresents the portfolio for a week each time it fires.
2. **Narrow named pattern list** — e.g. `CHORE_PATTERNS = (r"port.registry",)`,
   case-insensitive, applied at classification *and* to the rendered "shipped" line
   (otherwise a card reads "back-burner" while displaying a recent commit). Explicit,
   tunable, testable. Costs extra `/commits/{sha}` fetches.
3. **Fan-out detection** — treat an event as housekeeping when near-identical
   timestamps appear across ≥K repos. Costs *nothing* (computable from data already
   fetched) and catches future fan-out chores of any name, but it is a heuristic and
   could mis-fire on a genuine coordinated multi-repo release.

## Decision
**2026-08-04 — deferred by James.** Reviewed; leaving the rule alone for now. The
four affected projects age out on 2026-08-06 on their own. Revisit if the fan-out
becomes frequent enough to keep `/now` persistently wrong.

If revisited, option 2 or 3 — as a **named, tunable, tested rule**, not a silent
heuristic buried in `classify_projects`.

## Re-review 2026-08-05 — still deferred, but cheaper to live with

Reviewed again while adding the five family sites to `/now`. Decision unchanged:
**do nothing.** Two things shifted the cost/benefit further toward deferral.

1. **A manual override now exists.** `pin: "active" | "backburner"` in
   `bin/projects-config.json` (see `classify_projects(pinned=…)` and
   `tests/test_projects.py::TestProjectPinning`) lets a persistently
   misclassified project be corrected with one config line. That is the cheap
   90% of what option 2 would buy, without the per-candidate
   `/repos/{repo}/commits/{sha}` fetches or the `MAX_COMMIT_ENRICHMENTS` raise.
2. **The family-site case was the next likely trigger, and the pin absorbed it.**
   `jarrenchang`, `tobinchang`, and `rhyschang` were all pushed within ~25 minutes
   of each other on 2026-08-01 (00:29 / 00:51 / 00:54) — a textbook fan-out. Under
   the recency rule alone all three would have been promoted to active. They are
   pinned to back-burner instead, so the fan-out is a non-event for them.

What would change the decision: a fan-out that promotes a project James
*doesn't* want pinned — i.e. one whose active/back-burner state should still
track real activity. Only then is automatic detection (option 3, which is free
to compute from data already fetched) worth building over another pin.


## Resolution — 2026-09-01

Built as **option 2**, a named + tunable rule, after rejecting option 3
(fan-out timestamp detection) on its failure mode: it misfires exactly when a
genuine coordinated multi-repo release happens, i.e. the moment you most want
the card to read active. Option 2 fails to a silent no-op instead.

Real commit data across all 27 shipping repos then showed **two** noise
classes, not one:

**Rule 1 — `BOT_ACTORS`.** `actor.login` is already in the events payload, so
this costs no fetch and cannot misfire: a bot push is never human shipping
work. Bots are dropped BEFORE enrichment, leaving the whole
`MAX_COMMIT_ENRICHMENTS` budget for real commits. It affects exactly **one**
repo — `jameschang.co` is the only one `github-actions[bot]` pushes to (29 of
its last 30 events), so everywhere else it is a no-op.

**Rule 2 — `CHORE_PATTERNS`.** Narrow by design: `port[\s\-_]*registry`. The
separator class is not cosmetic — a test written from this todo's own table
caught that the chore appears as "port registry" in a subject and
"port-registry" in a merge branch name, and the first pattern missed the
second. A `chore:` prefix filter stays rejected for the reason recorded above.

Both rules run inside `parse_events()`, so `most_recent_event_time()` and
`events_for_project()` read the same filtered dict and **cannot disagree** —
closing the "card reads back-burner while displaying a recent commit" trap this
todo called out. Enrichment is lazy, so the extra fetches happen only on runs
where a chore is actually in front.

### The consequence that needed a decision

Filtering bots left `jameschang-co` with a feed that is 29/30 bot noise and
human pushes buried past the API window, so the card read back-burner on a day
nine real commits shipped — the "hides real work" failure this todo warned
about, arriving from the other direction. Resolved with `"pin": "active"` in
`bin/projects-config.json`: the pin exists for exactly this divergence, and
`family-sites` was already its first user in the opposite direction. The site
is genuinely always being worked on, so the pin is honest rather than a patch.

### Known limit, accepted

A push is judged by its **head commit alone** — `payload.commits[]` returns
empty from the events API even for public repos. A push that shipped real work
and *ended* with a chore therefore reads as a chore. The fan-out this targets
arrives as its own single-commit push, where head is the right verdict, so this
was accepted rather than fixed with per-push commit-range fetches.

**General lesson: a push is not a unit of intent.** The classifier assumed one
push means one kind of work and took the head commit as the verdict on all of
it. The same assumption at feed level is why 29 meaningless pushes can crowd
out the one that mattered.

Tests: `TestHousekeepingRules` (9), `TestSelfRepoPin` (2).
