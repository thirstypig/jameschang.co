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

## Blast radius (measured 2026-09-01, after the fix)

The fix is forward-only. The historical exposure turned out to be **differently
shaped than first assumed** — the initial framing said "~90 days of Actions
logs," which understated the durable half and overstated the transient one.

| sink | span | volume | lifetime |
|---|---|---|---|
| Public Actions logs | 2026-08-05 → 09-01 | 28 runs | expire ~2026-12-01 |
| **Committed `.feeds-heartbeat.json`** | 2026-07-23 → 08-05 | **273 commits** | **permanent** |

**The git-history half is the real one, and it predates the sink this todo is
named for.** The `print()` to stdout was *introduced by* the 2026-08-05 fix
(`5446ff0f`); before that, the raw text went into the committed heartbeat
instead (`53acb275`, 2026-07-23). So the 8/05 commit did not create the leak —
it **relocated** it from a permanent public artifact to a transient one, which
is a real improvement that was described as a fix.

**What is actually exposed:** 3 distinct strings, all `phase not allowlisted`,
44–52 characters each, all from `project-docs:judge-tool-roadmap` — i.e. phase
names from the private `thirstypig/thejudgetool` roadmap. The pre-8/05 code
sampled `dropped[:3]`, which capped it. Scanned for credential patterns and
high-entropy tokens: **none**. Read them with

```bash
git show 5446ff0f~1:.feeds-heartbeat.json | python3 -c \
  "import json,sys; print(json.load(sys.stdin)['project-docs:judge-tool-roadmap']['last_error'])"
```

## Decision: no purge

Deliberately doing nothing destructive.

- **Git history rewrite** (`filter-repo` + force push) would rewrite 273
  commits, break every clone and fork, and still not retract what GitHub has
  already cached or what anyone has already cloned. Wildly disproportionate to
  three roadmap phase names.
- **Deleting the 28 Actions runs** is cheap but pointless: they expire on their
  own by December, and deleting them destroys the audit trail that proved the
  leak was live.

Revisit only if the three strings turn out to be genuinely sensitive — that is
the owner's call, and the command above shows them.
