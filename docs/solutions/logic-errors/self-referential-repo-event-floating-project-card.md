---
title: "Self-repo always sorts first in active projects due to cron-generated GitHub events"
slug: "self-referential-repo-event-floating-project-card"
category: "logic-errors"
problem_type: "circular-activity-bias"
component: "bin/update-projects.py"
symptoms:
  - "jameschang-co appears at the top of the active projects section on /now every cron run"
  - "Project sort order is polluted by the cron's own commits, not genuine product activity"
  - "Self-referential repo always looks 'most recently active' because every sync workflow commits to it"
tags:
  - "projects-sync"
  - "activity-sorting"
  - "cron-side-effects"
  - "self-referential-repo"
  - "github-events"
  - "pin-order"
related_files:
  - "bin/update-projects.py"
  - "bin/projects-config.json"
  - "now/index.html"
  - "tests/test_projects.py"
date: 2026-06-13
---

## Problem

The `/now` page's active projects section (`/01`) sorts projects by most-recent GitHub event, descending — so the project you shipped something to yesterday appears first. `jameschang-co` is one of the 11 configured projects, with `shipping_repos: ["thirstypig/jameschang.co"]`.

But every cron workflow on the site commits to this repo: Spotify sync (30m), Google Calendar sync (1h), Plex sync (6h), projects sync (daily), etc. This means `jameschang-co` always had a GitHub event from minutes ago — guaranteeing it sorted first in the active section on every cron run, regardless of whether any real product work had been done on the site.

**Observable symptom:** Refresh `/now`. `jameschang.co` is always card #1 in the active section. Meanwhile Aleph, Fantastic Leagues, and Bahtzang Trader — where actual product shipping is happening — render below it.

## Root Cause

`_active_key(s)` returns the most-recent event datetime for slug `s`. With `reverse=True`, the project with the *latest* event sorts first. For `jameschang-co`, this timestamp is always within minutes of the current run because the cron is literally the agent writing those events.

The problem is structural: **the cron that sorts the projects is also one of the projects being sorted**, and its maintenance commits are indistinguishable from real product activity in the events API.

```python
# Before fix — jameschang-co floats to #1 every run
def _active_key(s):
    dt = events_by_slug.get(s)
    return dt or datetime.min.replace(tzinfo=timezone.utc)

active_slugs.sort(key=_active_key, reverse=True)
# jameschang-co always wins because its most-recent event = "4 minutes ago"
```

## Solution

### 1. Named constant

Added immediately below `ACTIVE_THRESHOLD_DAYS` in `bin/update-projects.py`:

```python
ACTIVE_THRESHOLD_DAYS = 7  # most-recent shipping event within this window → active
SELF_SLUG = "jameschang-co"  # always pinned to the bottom of its section
```

### 2. Named helper function

```python
def pin_self_last(slug, *lists):
    """Move `slug` to the end of whichever list it appears in.

    jameschang.co gets cron commits constantly, so without this it floats
    to the top of the active section on every run.
    """
    for lst in lists:
        if slug in lst:
            lst.remove(slug)
            lst.append(slug)
```

### 3. Call site in `main()` — post-sort, before rendering

```python
active_slugs.sort(key=_active_key, reverse=True)
backburner_slugs.sort(key=_backburner_key)
pin_self_last(SELF_SLUG, active_slugs, backburner_slugs)  # ← added
```

The function handles both lists: if `jameschang-co` is active today, it pins to the bottom of active; if it falls to back-burner, it pins to the bottom of that section instead. No-op when the slug is absent from both lists.

### 4. Bridge fix for the current page

The daily cron fires at 13:00 UTC. The code fix was committed between cron runs, so `now/index.html` still had `jameschang-co` rendered first. The card was manually repositioned to the bottom of the `<!-- ACTIVE-PROJECTS-START --> ... <!-- ACTIVE-PROJECTS-END -->` block in the same push. The next cron run then preserved the correct order via `pin_self_last`.

## Why Post-Sort Mutation Over Sort Key Hacking

The alternative — returning `datetime.min` for `SELF_SLUG` inside `_active_key` — was rejected because:

- **The sort key encodes two different concerns**: the natural event-recency ranking (correct for all other projects) and the override rule (correct only for `jameschang-co`). Embedding the rule inside the comparator makes both harder to read.
- **Fragile to sort direction changes.** If `reverse=True` ever becomes `reverse=False` for any reason, the sentinel inverts to "always first" instead of "always last."
- **Breaks testability.** A sort-key sentinel requires running the full sort pipeline to observe the ordering effect. `pin_self_last()` is a pure function with zero dependencies — directly unit-testable with a plain list.

Post-sort mutation makes the rule explicit and separate. A reader of `main()` sees: (1) sort by recency, (2) then apply the exception. The two concerns don't interfere.

## Tests Added

`tests/test_projects.py` — `class TestPinSelfLast`:

```python
def test_pins_to_bottom_of_active(self):
    active = ["jameschang-co", "aleph", "fl"]
    back = ["judge-tool"]
    _projects.pin_self_last("jameschang-co", active, back)
    assert active[-1] == "jameschang-co"
    assert back == ["judge-tool"]

def test_pins_to_bottom_of_backburner(self):
    active = ["aleph"]
    back = ["jameschang-co", "judge-tool"]
    _projects.pin_self_last("jameschang-co", active, back)
    assert back[-1] == "jameschang-co"
    assert active == ["aleph"]

def test_noop_when_already_last(self):
    active = ["aleph", "jameschang-co"]
    _projects.pin_self_last("jameschang-co", active)
    assert active == ["aleph", "jameschang-co"]

def test_noop_when_slug_absent(self):
    active = ["aleph", "fl"]
    back = ["judge-tool"]
    _projects.pin_self_last("jameschang-co", active, back)
    assert active == ["aleph", "fl"]
    assert back == ["judge-tool"]
```

## Detection Signals — How to Spot This Class of Bug

- A project card sorted by recency always shows today's timestamp, even when you haven't shipped anything to it
- The timestamp matches the cron run time, not meaningful developer activity
- `shipping_repos[]` for the project includes the same repo the cron itself commits to

**Diagnostic:** check `/repos/thirstypig/jameschang.co/events` — if all recent events are `PushEvent` with `chore: update Spotify/Plex/gcal` commit messages, that's the contamination.

## Generalization — If More Self-Referential Projects Are Added

The current approach hardcodes `SELF_SLUG`. If a second project's `shipping_repos` also included this repo, it would need the same treatment. The upgrade path:

**Config flag (recommended for scale):** Add `"pin_last": true` to `projects-config.json` for any self-referential project. `update-projects.py` reads the flag and builds the pin list from config rather than a hardcoded constant. Zero code changes to add a second case.

**Event-type filtering (principled but overkill):** Filter each project's events to exclude pushes where the committer is `github-actions[bot]`. Distinguishes real product work from automated maintenance across all projects. Requires parsing `payload.commits[].author` — more code, more brittle. Worth revisiting if this grows to dozens of projects.

**Empty `shipping_repos` (simplest):** If `jameschang-co` had `shipping_repos: []`, it would always have zero events and always fall to back-burner by the existing threshold logic — no special-case code needed. Trade-off: loses any genuine activity signal if real feature work is added to the site later. Reasonable for a personal site, but `pin_self_last` preserves the option to show real activity while still deprioritizing the project.

## See Also

- [`integration-issues/marker-boundary-content-staleness.md`](../integration-issues/marker-boundary-content-staleness.md) — the broader principle that sync scripts should only act on their declared contract surface; unexpected content outside markers freezes silently
- [`integration-issues/relative-time-html-defeats-content-changed-cache.md`](../integration-issues/relative-time-html-defeats-content-changed-cache.md) — another cron side-effect: wall-clock strings in `<time data-rel>` elements defeat the `content_changed()` no-op cache, causing spurious commits
- [`integration-issues/per-project-adapters-for-heterogeneous-roadmap-sources.md`](../integration-issues/per-project-adapters-for-heterogeneous-roadmap-sources.md) — bootstrap-aware heartbeat gating (don't alert on feeds that have never succeeded); a related pattern in the same cron pipeline
