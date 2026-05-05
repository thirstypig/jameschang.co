---
title: "Content outside a sync mechanism's contract surface freezes silently — WHOOP eyebrow date and orphan feed-stale issues"
category: integration-issues
tags: [sync-pipeline, markers, content-cache, github-issues, contract-surface, cron]
symptom: "static text near a sync target stops updating; GitHub feed-stale issues stay open after a feed is retired"
root_cause: "sync mechanisms only act on the explicit contract surface they were given (between-marker HTML for replace_marker(); heartbeat dict keys for check-feed-health.py). Content outside that surface is structurally invisible to the sync — it freezes on its last hand-edit, or in the issue case, sits open forever because the cleanup loop never visits the retired slug"
module: now-page-sync-pipeline
date_solved: 2026-05-04
severity: low
---

# Marker boundaries and contract surfaces — when "outside the contract" means "frozen forever"

## The problem

Two unrelated-looking incidents shipped on 2026-05-04 share the same underlying bug class.

### Incident 1 — WHOOP eyebrow date freeze (commit `454c4f4`)

The `/now` WHOOP block has a hand-written eyebrow line ("As of {date}…") above the sync-managed grid of stat tiles. The eyebrow lived **outside** the `<!-- WHOOP-START -->` / `<!-- WHOOP-END -->` marker pair. `bin/update-whoop.py` calls `_shared.replace_marker()`, which only rewrites content **between** markers. The eyebrow text was therefore never touched by the daily cron — it had been frozen at "April 27" since the notebook redesign cut over, despite the WHOOP feed updating every day.

A reader on May 4 saw "As of April 27" sitting above a grid of fresh May 3 readings. The data was current; the chrome lied.

### Incident 2 — Orphan feed-stale issues (commit `248afd2`)

`bin/check-feed-health.py` opens / comments / closes GitHub issues based on per-feed heartbeats stored in `.feeds-heartbeat.json`. The script iterated `data.items()` from that file. When the `github` feed was folded into the new `projects` feed (during the per-project shipping refactor), the `github` slug stopped writing heartbeats — but its open feed-stale issue sat there forever because the cleanup loop never visited a slug that wasn't a heartbeat key.

The contract was "for each heartbeat, decide whether the issue should be open." It needed to also be "for each open `feed-stale` issue, check whether the slug still exists; if not, close it."

## The shared lesson

Both bugs are the same shape:

- A sync mechanism has an **explicit contract surface** — the inputs / outputs it was designed to act on.
- Content adjacent to that surface (chrome around the marker; issues for retired slugs) **looks** like it's part of the system but isn't.
- The sync runs cleanly. No error. No warning. The frozen content just… stays frozen.

The fix in both cases is one of:

1. **Bring it inside the contract.** Move the eyebrow date inside `<!-- WHOOP-START -->` / `<!-- WHOOP-END -->` so `replace_marker()` actually rewrites it. (The chosen fix for incident 1.)
2. **Add an explicit code path that owns it.** Add a second loop that scans open `feed-stale` issues and closes orphans. (The chosen fix for incident 2.)

What you cannot do is leave it dangling and assume the existing sync will magically handle it. Wall-clock-driven decorations and retired slugs are structurally invisible to the cron until somebody widens the contract.

## Why these are easy to miss

- The hand-edit that introduced the WHOOP eyebrow felt safe — the rest of the WHOOP section was already inside the markers and updating, so an extra line "near" them seemed like part of the same surface. It wasn't.
- The github→projects refactor cleanly removed the heartbeat write; the open issue was a downstream artifact in a different file (`.github/issues`) that nobody thought about during the refactor.
- Neither bug fails a test. Neither produces an alert. Both surface only to a human reading the rendered page or the GitHub issue tab.

## Solution

### Incident 1

Moved the WHOOP eyebrow date string inside the marker pair so each daily sync rewrites it alongside the recovery / sleep / strain tiles. Same code path now owns both.

### Incident 2

Extended `bin/check-feed-health.py` with a second loop that lists open issues with the `feed-stale` label and closes any whose feed slug isn't present in the current heartbeat dict. The cleanup is idempotent (closing an already-closed issue is a no-op via the GitHub API's behavior) and runs every 6 hours alongside the existing staleness sweep.

## Prevention

Three guardrails for future work on the `/now` sync pipeline and the feed-health monitor:

1. **Marker discipline.** When adding *any* time-sensitive text to a feed section in `now/index.html`, default to placing it inside the `<!-- {FEED}-START -->` / `<!-- {FEED}-END -->` block. If it must live outside (e.g., a section heading), mark it with a code comment naming the convention so future hands don't assume the sync handles it. CLAUDE.md's "Data feeds on /now" section names this rule explicitly.

2. **Bidirectional cleanup.** Any sync that maintains side-effects in an external system (GitHub issues, comments, labels, releases) must reconcile in both directions: not just "ensure the right thing exists for each input," but also "ensure no stale thing exists for an input that no longer exists." The orphan-loop pattern in `check-feed-health.py` is the template.

3. **Operational signal.** Both bugs surfaced when a human read the page / issue tab and noticed "huh, that should have updated." There's no programmatic alert for "static content drifted from reality." Treat any near-the-marker chrome with skepticism on each /ce:review.

## Cross-references

- **Fix commits:** `454c4f4` (WHOOP eyebrow brought inside markers), `248afd2` (orphan feed-stale issue cleanup).
- **Sibling solution doc:** `docs/solutions/integration-issues/relative-time-html-defeats-content-changed-cache.md` — same family (content-cache contract was also incomplete on its surface). The two together describe the full "stuff the sync pipeline can fail to see" problem space: relative-time text *defeating* the no-op cache (false positive — looks changed when it isn't) and out-of-marker chrome *bypassing* the sync entirely (false negative — looks updated when it isn't).
- **Touched code:** `bin/_shared.py::replace_marker`, `bin/check-feed-health.py` (orphan cleanup loop), `now/index.html` (WHOOP marker boundary).
