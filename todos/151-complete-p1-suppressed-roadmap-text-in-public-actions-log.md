---
status: complete
priority: p1
issue_id: "151"
tags: [security, disclosure, copy-layer, project-docs, public-repo]
dependencies: []
---

## Problem Statement

`bin/update-project-docs.py` printed every suppressed roadmap line, in full, to
stdout on each `project-docs-sync` run. The dropped entries carry upstream text
**by construction** — suppressing them is the copy layer's entire purpose — and
`thirstypig/jameschang.co` is a PUBLIC repo, so Actions logs are anonymously
readable for ~90 days.

Found by the 2026-08-16 audit, confirmed still live 2026-09-01: that morning's
17:18 run carried 9 content-bearing lines, including real phase names from the
private `thirstypig/thejudgetool` repo.

## Why it survived a fix

The 2026-08-05 commit that added `_drop_summary()` correctly stopped this text
reaching the committed heartbeat, and justified the remaining print as "stdout
… lands in the workflow log — a channel that isn't committed."

That sentence is true and irrelevant. **Not committed is not the same as not
public.** The control was *moved, not closed*.

**Reusable lesson — the shape of a redaction bug: the sink changed, the taint
didn't.** When fixing a leak, enumerate every sink the tainted value still
reaches, not just the one that prompted the fix.

## Resolution (2026-09-01)

Three commits' worth of change, shipped as two:

1. **stdout leak closed** (`20669693`). Both sinks now emit the same
   `_drop_summary()` value. Docstring records the rule: dropped entries may
   reach NO output channel; route everything through `_drop_summary()`.

2. **`str(e)` leak closed.** `main()`'s catch-all wrote the raw exception to
   BOTH stderr (the Actions log) and `.feeds-heartbeat.json`, which
   `check-feed-health.py:161` renders verbatim into a public issue body. A
   `KeyError` inside `apply_public_copy()` embeds the offending phase name by
   construction. Now records `f"{type(e).__name__} in {slug}/{doctype}"`.
   **Accepted cost:** diagnosing that path now needs a local repro.

3. **`KNOWN_REASONS` dead vocabulary fixed.** It named `"no plain_english
   mapping"`, which nothing emits, while the four real `…not translated`
   reasons fell through to `"other"` — so the breakdown, the entire value of a
   redacted summary, was blank for the most common drift class. The five
   prefixes are now module constants that the emitters AND the classifier both
   read. Observable effect on real data:

   ```
   before:  4 item(s) dropped (4 other)
   after:   4 item(s) dropped (1 description not translated,
                               3 workflow step not translated)
   ```

## Tests

Three added, each verified by reverting its fix and confirming red — not merely
by passing:

- `test_stdout_carries_no_dropped_source_text`
- `test_unexpected_exception_records_type_not_message`
- `test_every_reason_apply_public_copy_emits_is_classified` — drives
  `apply_public_copy()` with input triggering all five drops and asserts the
  emitted prefix set equals `DROP_REASONS`, so a new emit site added without a
  constant fails here.

The pre-existing `SYNTHETIC` fixture was re-based onto prefixes production
actually emits. It had used `"no plain_english mapping"` — **a string it
invented** — which is why the suite stayed green while production degraded.
*A fixture that invents its subject can only ever test itself.*

## Still open

**The fix is forward-only.** Roughly 90 days of EXISTING public Actions logs
still contain the leaked text. Purging requires `gh run delete` on the affected
`project-docs-sync` runs — destructive, irreversible, and destroys the audit
trail, so it is deliberately left as the owner's call rather than done as part
of this fix.
