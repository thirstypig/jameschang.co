---
status: pending
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
