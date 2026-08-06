---
title: "Five maintenance-mode sites would have rendered as active work — the classifier measures commit recency but the section heading claims intent, and those diverge"
slug: activity-recency-misreads-maintenance-mode-as-active-work
category: logic-errors
tags: [sync-pipeline, cron, projects-sync, classification, proxy-signal, config-drift, now-page, override-design]
symptom: "five family personal sites in permanent maintenance mode would have rendered in the /now 'active' section on the strength of routine content edits, because two of the five had been pushed to hours earlier and three within four days"
root_cause: "classify_projects() decides active vs back-burner from a single signal — recency of the most recent GitHub event across shipping_repos[] within ACTIVE_THRESHOLD_DAYS = 7. Recency answers 'was this touched recently?', but the section heading asserts 'am I still building this?'. For a maintenance-mode project those two questions have opposite answers, and no amount of tuning the threshold reconciles them, because the property the heading claims is intent and intent is not present in any signal the script can observe."
module: now-page-sync-pipeline (bin/update-projects.py, bin/projects-config.json)
date_solved: 2026-08-05
severity: low
---

# Activity recency is a proxy for intent, and proxies drift from what the label claims

Adding five finished personal sites to `/now` should have been a config edit. It
wasn't, because the classifier would have put all five in the wrong section — and
the reason it would have is not a bug in the classifier. The classifier does exactly
what it says. What it says is not what the page claims.

## Symptom

Five family personal sites (`shengchangmd`, `minmeychang`, `jarrenchang`,
`tobinchang`, `rhyschang`) were to be added to `/now` as **back-burner**: all live,
all finished, no plans to expand any of them into a product. Only occasional content
edits from here on.

Every one of them would have rendered as **active**:

```
shengchangmd   pushed 2026-08-05T21:45Z   (hours earlier)
minmeychang    pushed 2026-08-05T21:30Z   (hours earlier)
rhyschang      pushed 2026-08-01T00:54Z   (4 days)
jarrenchang    pushed 2026-08-01T00:51Z   (4 days)
tobinchang     pushed 2026-08-01T00:29Z   (4 days)
```

All five inside `ACTIVE_THRESHOLD_DAYS = 7`. Nothing is malfunctioning. The commits
are real, recent, and correctly attributed.

Note also the three timestamps within 25 minutes of each other on 08-01 — an
independent instance of the fan-out pattern in
`todos/148-pending-p3-chore-commits-promote-projects-to-active.md`.

## Root cause: claim/signal divergence

`classify_projects()` measures one thing:

```python
cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_days)
if latest is not None and latest > cutoff:
    active.append(slug)
```

That is a correct and complete answer to **"was this repo touched in the last seven
days?"**

The `/now` section headings ask a different question. "Active" against "shipping but
not daily" is a claim about *where the work is going* — about intent. For most
projects the two questions correlate well enough that the gap is invisible. They come
apart precisely at maintenance mode: a finished thing that still gets edited.

The gap is not closable by tuning. Lower the threshold and a genuinely active project
that had a quiet week gets demoted. Raise it and everything is active forever. Add
signals — commit size, message parsing, fan-out detection — and you get a more
elaborate proxy that is still a proxy, plus new mis-fire modes of its own. **Intent
is not recoverable from the event stream, because it was never in the event stream.**

This is the same failure family as the two neighbouring docs, at a different layer:

| Doc | What broke |
|---|---|
| [`../integration-issues/github-repo-rename-redirect-silently-orphans-project-events.md`](../integration-issues/github-repo-rename-redirect-silently-orphans-project-events.md) | signal was real, machinery **lost** it (dict key miss) |
| [`self-referential-repo-event-floating-project-card.md`](./self-referential-repo-event-floating-project-card.md) | signal was real but **self-generated** (the cron's own commits) |
| this doc | signal was real, correctly attributed, and simply **means something else** |

Only the first is a bug. The other two are the label overreaching its evidence.

## The rejected fix: emptying the classifier's input

The obvious zero-code fix is `"shipping_repos": []` — no repos, no events, no
recency, permanent back-burner. It works, requires no new field, and would have
shipped in one line.

It is the wrong shape, because `shipping_repos[]` has five consumers, not one:

| Consumer | Effect of emptying it |
|---|---|
| `most_recent_event_time()` | intended: no events → back-burner |
| `events_for_project()` → `render_activity_box()` | card renders "no recent activity" — **the page now states something false** |
| `shipping_repos_for()` | those repos are never fetched at all |
| `repo_key_mismatch()` | can never fire for them — the rename detector goes blind on exactly those repos |
| `_events_ok` / `_events_err` tally | fewer repos in the systemic-failure denominator |

So a "harmless" config edit would silently disable a monitor built specifically to
catch silent misclassification, and would encode a false claim — these projects *do*
have repos — into the data model.

**The general rule: overrides go downstream of measurement, never upstream of it.**
Measure truthfully, render the measurement, then override the *decision* at the last
step before it is used. Anything else corrupts your monitoring and your rendered
evidence along with your output.

Four questions that catch this smell anywhere:

1. **Does the field mean what I'm using it for?** `shipping_repos` means "which
   repos' commits belong to this project" — a fact about the world, not a control
   register.
2. **After my change, is a true statement about the world still representable?**
3. **How many readers does this field have, and did I intend to change all of them?**
4. **Is the override greppable afterward?** `pin: "backburner"` answers "which
   projects are overridden?" instantly. An emptied input is indistinguishable from
   data that was simply never filled in — six months later nobody can tell.

There is a mirrored form worth naming too: *feeding* the sensor (a backdated event, a
dummy commit, a synthetic heartbeat) rather than starving it. Same defect, and it
additionally poisons everything downstream that trusts the input as observed data.

A cheap structural tell: **if implementing your override makes one of your own
data-quality tests wrong, it isn't an override — it's data corruption.**

## The fix

An explicit intent field, in its own namespace, consumed at the decision point:

```python
PIN_ACTIVE = "active"
PIN_BACKBURNER = "backburner"
VALID_PINS = frozenset({PIN_ACTIVE, PIN_BACKBURNER})


def classify_projects(events_by_slug, threshold_days=ACTIVE_THRESHOLD_DAYS,
                      pinned=None):
    pinned = pinned or {}
    ...
    for slug, latest in events_by_slug.items():
        pin = pinned.get(slug)
        if pin is not None and pin not in VALID_PINS:
            print(f"  WARNING: {slug} has unrecognized pin {pin!r} ...")
            pin = None
        if pin == PIN_BACKBURNER:
            backburner.append(slug)
        elif pin == PIN_ACTIVE:
            active.append(slug)
        elif latest is not None and latest > cutoff:
            active.append(slug)
        else:
            backburner.append(slug)
```

`main()` builds the mapping from config:

```python
pinned = {p["slug"]: p["pin"] for p in projects if p.get("pin")}
active_slugs, backburner_slugs = classify_projects(events_by_slug, pinned=pinned)
```

Four properties that make this an override rather than a lie:

- **The measurement is untouched.** A pinned card still fetches its repos and still
  renders its real most-recent commit, so a reader sees the raw signal and can
  privately disagree with the label.
- **Fails loudly, then fails open.** An unrecognized value warns to the cron log and
  falls through to the recency rule — a config typo degrades to a defensible answer,
  never a crashed sync.
- **Closed vocabulary.** `VALID_PINS` makes "which projects are overridden?" a
  one-line query and "are we overriding too much?" a testable assertion.
- **Surgical.** A pin changes only the slug it names; everything else still follows
  recency.

Note this is a *different axis* from the pre-existing `SELF_SLUG` / `pin_self_last()`
mechanism, which controls **ordering within** a section. `pin` controls **section
membership**. They do not interact, and `pin_self_last()` remains hardcoded.

## Prevention

**1. Write the claim and the signal in the same sentence, at the point of
definition.** `ACTIVE_THRESHOLD_DAYS = 7` reads as self-evident until you set it
beside the heading it produces. If the two sentences are not paraphrases of each
other, you have a proxy — budget for an override before shipping.

**2. Audit at the render site, not the compute site.** Headings get reworded by
people who never open the classifier. A heading that grows *stronger* ("recently
touched" → "what I'm building") is a specification change with no code diff, which
makes it the highest-risk edit in this class: no reviewer sees the classifier.

**3. Every proxy classifier ships with a declared override channel in the data
model, distinct from its measured inputs.** Intent fields and measurement fields
answer different questions and have different owners — a human versus an API.

**4. Pair the warn-and-fall-open runtime behavior with a CI assertion on the
vocabulary.** A warning printed on an otherwise-green scheduled run is a warning
nobody reads.

**5. Prefer one explicit override to N heuristics that make the proxy smarter.**
Each heuristic widens the gap between what the code does and what anyone can explain.

### When a pin is right, and when it is papering over

The discriminating question: **if this project's real activity changed tomorrow,
would I want the label to change?**

- **No** → the property is intent, intent is not in the data, no classifier
  improvement recovers it. Pin it.
- **Yes** → the label should track the signal and the signal is wrong. Fix the
  classifier.

Papering-over tells:

- **The pinned set keeps growing.** Two or three pins is a portfolio with unusual
  projects. Half the portfolio is a default that is simply wrong.
- **You re-pin on a cadence to track reality.** You have become the classifier,
  executed by hand.
- **One root cause explains several pins.** Fix the signal once instead of pinning
  each victim.
- **The pin routes around a detectable defect.** Pinning `tip` to active during the
  `todos/149` rename incident would have hidden a real bug behind a plausible config
  line. **Never pin around a failure your monitoring can detect** — fix the fact and
  keep the detector.

## Regression tests

`tests/test_projects.py::TestProjectPinning` (7) covers the override semantics: both
directions, promotion of a project with no events at all, surgicality, backward
compatibility when `pinned` is omitted, warn-and-fall-open on an unrecognized value,
and the constants themselves.

`TestLoadConfig` adds the two config-side guards:
`test_config_pin_values_are_all_recognized` (the CI half of prevention #4) and
`test_family_sites_is_pinned_to_backburner`.

**Gaps worth closing.** Three are not covered today:

1. **The partition invariant.** The pin branch is new code on the only path deciding
   section membership. A slug falling out of *both* lists would vanish from `/now`
   with no error and no heartbeat complaint. Assert
   `sorted(active + back) == sorted(events)` and that the two sets are disjoint.
2. **The config → classifier seam.** `main()` builds `pinned` with an inline dict
   comprehension that nothing tests. Delete that one line and every existing pin test
   still passes while `/now` silently goes wrong.
3. **The rejected alternative, enforced repo-wide.** A test asserting no project
   declares an explicitly empty `shipping_repos[]` would stop the anti-pattern in
   §"The rejected fix" from being reintroduced by someone who never read this doc.
   (Absence of the key is fine — `shipping_repos_for()` falls back to `repo`. An
   explicitly empty list is the smell.)

## One emergent behavior nobody chose

`_backburner_key` sorts slugs that have events ahead of those that don't, newest
first. `family-sites` is among the most frequently pushed entries in the config, so
it renders as the **first** card under "shipping but not daily". Defensible, but it
is an interaction between the pin and the sort that was not designed. If the ordering
matters, assert it; if not, at least know it exists.

## See also

- [`self-referential-repo-event-floating-project-card.md`](./self-referential-repo-event-floating-project-card.md) — same file, same classification machinery, the closest sibling. Its "Generalization" section proposes a `pin_last: true` config flag; a config flag named `pin` now exists but controls section membership, **not** ordering, and `SELF_SLUG` is still hardcoded. That upgrade path has not shipped.
- [`../integration-issues/github-repo-rename-redirect-silently-orphans-project-events.md`](../integration-issues/github-repo-rename-redirect-silently-orphans-project-events.md) — the inverse failure on this same path: the machinery losing a real signal rather than misreading one. Check its heartbeat `last_error` before reaching for a pin.
- [`../integration-issues/cron-script-config-driven-content-rendering.md`](../integration-issues/cron-script-config-driven-content-rendering.md) — the canonical config-as-source-of-truth write-up. `pin` is the first config field consumed by `classify_projects()` rather than `render_card()`: a field that changes *placement* rather than *content*.
- [`../../guides/cron-scripts-architecture.md`](../../guides/cron-scripts-architecture.md) — where the config-driven pattern is taught.
- `todos/148-pending-p3-chore-commits-promote-projects-to-active.md` — the still-deferred fan-out-chore problem, and the strongest evidence for this pattern: its 2026-08-05 re-review records that the pin absorbed the next likely trigger.
