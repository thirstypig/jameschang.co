---
title: "The fail-closed copy layer stripped private roadmap text from the public page, then wrote it verbatim into a committed public heartbeat — the guard leaked through its own error channel"
slug: error-notes-leak-the-content-a-redaction-guard-suppressed
category: security-issues
tags: [disclosure, redaction, public-repo, heartbeat, observability, telemetry, error-handling, project-docs, fail-closed]
symptom: "`.feeds-heartbeat.json` — tracked, committed, and public — carried `\"5 item(s) dropped: phase not allowlisted: <real upstream phase name>...\"` for a private project, while the published HTML page it was generated from correctly contained none of that text"
root_cause: "apply_public_copy() drops any roadmap item that is not explicitly allowlisted and translated, which keeps private upstream strings off the rendered page. _record_sync_heartbeat() then summarized those drops for observability by joining the first three dropped entries verbatim into record_heartbeat(error=...). That value is written to .feeds-heartbeat.json, which every sync workflow commits to this PUBLIC repo, and which check-feed-health.py renders into a public GitHub issue body. The redaction boundary was drawn around the rendering path only; the error/telemetry path went around it."
module: project-docs-sync (bin/update-project-docs.py, .feeds-heartbeat.json, bin/check-feed-health.py)
date_solved: 2026-08-05
severity: high
---

# A redaction guard that leaks through its own error channel

The copy layer exists for exactly one reason: keep a private project's internal
roadmap language off a public page. It does that correctly. Then it wrote the
suppressed text into a different public file, in the name of observability.

## Symptom

Found during an unrelated documentation audit, not by any alarm.

`.feeds-heartbeat.json`, which is **tracked and committed on every sync run**:

```json
"project-docs:judge-tool-roadmap": {
  "last_success_utc": "2026-08-05T15:24:44Z",
  "last_error": "5 item(s) dropped: phase not allowlisted: <real phase name>; ..."
}
```

170 characters of upstream phase names from a private repo, in a public one.
Meanwhile the destination page, `/projects/judge-tool/roadmap/`, contained none of
them — the copy layer had done its job perfectly on the surface it was watching.

Two things made this worse than a stray string:

- **`bin/check-feed-health.py` renders `last_error` into a GitHub issue body.** Had
  that feed gone stale, the leaked names would have been republished into a public
  issue.
- **A test asserted the leak was correct.** `test_roadmap_drops_are_recorded_as_partial_success`
  contained `assert "Security Hardening" in entry["last_error"]` — pinning the leaky
  format as the contract, using a real upstream phase name, in a committed public
  test file.

## Root cause

`apply_public_copy()` fails closed: an unlisted phase or an untranslated item is
dropped rather than rendered. The dropped entries are returned so the caller can
report them. That reporting is where the boundary broke:

```python
sample = "; ".join(dropped[:3])
record_heartbeat(feed_slug,
                 error=f"{len(dropped)} item(s) dropped: {sample}",
                 partial_success=True)
```

Each entry is `"<reason>: <the raw upstream line>"`. Joining them puts the
suppressed content directly into the heartbeat.

**The redaction boundary was drawn around the render path, and the error path went
around it.** Nothing was wrong with the guard. What was wrong is that "public
surface" had been reasoned about as *the page*, when this repo actually publishes
three surfaces: the rendered HTML, the committed JSON artifacts, and the GitHub
issues the monitor opens. The copy layer only knew about the first.

## The fix

Report the **shape** of the drops, never their content:

```python
def _drop_summary(dropped):
    KNOWN_REASONS = ("phase not allowlisted", "no plain_english mapping")
    counts = {}
    for entry in dropped:
        reason = next((r for r in KNOWN_REASONS if entry.startswith(r)), "other")
        counts[reason] = counts.get(reason, 0) + 1
    breakdown = ", ".join(f"{n} {r}" for r, n in sorted(counts.items()))
    return f"{len(dropped)} item(s) dropped ({breakdown})"
```

→ `"5 item(s) dropped (1 no plain_english mapping, 4 phase not allowlisted)"`

Three properties worth keeping:

- **The reasons are our own vocabulary,** authored in `apply_public_copy()`, not
  upstream content. That is what makes them safe to publish.
- **It fails closed too.** An entry whose prefix isn't recognized becomes `"other"`
  rather than having its text forwarded on the assumption it's harmless.
- **The full lines still go to stdout**, which lands in the workflow log — visible to
  the operator, not a committed artifact. Debuggability was the original goal and it
  survives; only the destination changed.

Also done: the already-committed `last_error` value was scrubbed from
`.feeds-heartbeat.json`, and the test that asserted the leak was rewritten to assert
the redaction, with a synthetic phase name replacing the real one.

## Prevention

**1. Enumerate your publication surfaces before drawing a redaction boundary.**
This repo has three, and only one was considered:

| Surface | Public? | Was it considered? |
|---|---|---|
| Rendered HTML on the site | yes | yes — the guard works here |
| Committed JSON artifacts (`.feeds-heartbeat.json`, `admin/docs/index.json`) | yes | **no** |
| GitHub issues opened by the monitor | yes | **no** |

A generated file that is *committed* is as public as a page. It is easy to miss
because it looks like infrastructure rather than content.

**2. Error and telemetry paths need the same redaction as the happy path — and they
are where it is usually forgotten.** The reasoning is seductive: the error branch is
rare, it's for debugging, and including the offending value is what makes an error
message useful. That instinct is correct in a private log and wrong in a published
artifact. Ask of every diagnostic: *where does this string come to rest, and who can
read it there?*

**3. Log the shape, publish the shape; keep the content in the ephemeral channel.**
Counts, reasons, indices, and hashes are almost always enough to act on. If the raw
value is genuinely needed to debug, send it somewhere that isn't committed.

**4. A test that asserts a leak will defend it.** The existing test *required* the
dropped phase name to appear in `last_error`. Anyone who fixed the leak would have
broken a test and might reasonably have concluded they were wrong. When you write a
test over an error message, be deliberate about whether you're pinning the
*diagnostic quality* or the *payload* — and never pin the payload for content that a
guard elsewhere exists to suppress.

**5. Guard tests must not contain the thing they guard against.** The test used a
real upstream phase name in a public repo. Use synthetic sentinels
(`ZZSyntheticGatedPhase`) so the test is leak-safe by construction — the pattern
`TestCopyMapMechanism` already established here.

## Regression tests

`tests/test_project_docs.py::TestDropSummaryRedactsSourceText` (5), all synthetic:

| Test | Guards |
|---|---|
| `test_summary_contains_no_dropped_source_text` | the leak itself |
| `test_summary_reports_count_and_reason_breakdown` | the note stays useful after redaction |
| `test_unrecognized_reason_degrades_to_other_rather_than_passing_through` | fail-closed on an unknown prefix |
| `test_heartbeat_records_the_redacted_summary` | the wiring, end to end |
| `test_committed_heartbeat_file_carries_no_dropped_source_text` | the shipped artifact itself — catches a legacy value that predates the fix |

The last one is the important one: it asserts against the **committed file**, not
just the function, so a leaked value can't sit in the repo unnoticed the way this one
did.

## Known limitation, unchanged by this fix

The heartbeat note is **passive**. `check-feed-health.py` gates only on
`last_success_utc` age, and `partial_success=True` refreshes that timestamp — so a
`last_error` on a healthy feed is *structurally guaranteed* never to open an issue.
It is visible only by reading the JSON. Several docs describe drops as "surfacing" in
the heartbeat, which reads as alerting; it isn't. This feed had been silently dropping
five roadmap items per run, and the only reason anyone noticed was an unrelated audit.

## See also

- [`secret-leak-guard-for-generated-committed-public-artifact.md`](./secret-leak-guard-for-generated-committed-public-artifact.md) — the sibling case and the closest prior art: the same insight that a *generated, committed* file is a public surface, applied to `admin/docs/index.json`. That guard scans the artifact; this incident is what happens on a surface no such scan covers.
- [`../integration-issues/feed-heartbeat-on-noop-path-hides-upstream-api-failure.md`](../integration-issues/feed-heartbeat-on-noop-path-hides-upstream-api-failure.md) — introduced `partial_success=True`, the mode this leak travelled on. Useful pairing: that doc explains why the mode exists, this one shows the cost of putting untrusted content into it.
- [`../integration-issues/hand-listed-ci-test-files-silently-exclude-new-tests.md`](../integration-issues/hand-listed-ci-test-files-silently-exclude-new-tests.md) — `tests/test_project_docs.py` was one of the ten files CI never executed, so the test asserting the leaky format had not run in CI since the day it was written.
