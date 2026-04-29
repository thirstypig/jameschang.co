---
title: "Server-rendered <time data-rel> elements defeated the no-op content-cache, causing 48 timestamp-only commits/day per sync script"
category: integration-issues
tags: [sync-pipeline, content-cache, timestamps, progressive-enhancement, cron, github-actions]
symptom: "cron sync scripts push commits to main every run even when no upstream content changed"
root_cause: "content_changed() and the Spotify state-cache hash both stripped 'Auto-updated …' lines but not the visible text inside <time data-rel>…</time> elements; that text reformats every wall-clock minute via the now/now.js upgrader, so every cron run produced a fake 'diff' and triggered git commit && push"
module: now-page-sync-pipeline
date_solved: 2026-04-29
severity: medium
---

# `<time data-rel>` elements defeating the no-op content-cache

## The problem

The `/now` page is assembled from six cron-driven sync scripts (WHOOP, Spotify, Plex, public-feeds, projects, trakt-disabled), each of which:

1. Fetches data from an upstream API.
2. Renders the result into a chunk of HTML.
3. Splices that HTML into `now/index.html` between marker comments.
4. **Short-circuits on no-op:** if the rebuilt HTML matches the existing HTML modulo a known set of time-volatile substrings, the script skips writing and exits cleanly.
5. Otherwise calls `git commit && git push origin main` from the GitHub Actions runner.

The short-circuit was implemented in `bin/_shared.py`:

```python
def content_changed(old_content, new_content):
    """Check if content changed meaningfully (ignoring Auto-updated date/time lines)."""
    date_pattern = r"Auto-updated [A-Z][a-z]+ \d+, \d{4}(?: at \d{1,2}:\d{2} [AP]M [A-Z]{2,4})?"
    old_stripped = re.sub(date_pattern, "", old_content)
    new_stripped = re.sub(date_pattern, "", new_content)
    return old_stripped != new_stripped
```

Spotify additionally maintained its own per-run content-hash in `.spotify-state.json` using the same date strip:

```python
date_stripped = re.sub(r"Auto-updated [A-Z][a-z]+ \d+, \d{4}(?: at \d{1,2}:\d{2} [AP]M [A-Z]{2,4})?", "", html_block)
tracks_hash = hashlib.sha1(date_stripped.encode()).hexdigest()[:12]
```

**Symptom:** Spotify (cron every 30 min) was pushing 40-48 commits per day, every single one a one-line diff with no meaningful content change. `git log --oneline` was overwhelmingly noise. The other three sync scripts (Plex/WHOOP/public-feeds) had the same shape and were spamming at lower cadence (every 6h, daily, every 6h respectively).

The fact that the page-update was *the only thing changing* between commits made the noise worth fixing — every commit consumed Actions minutes, GitHub bandwidth, and meaningful-history scannability.

## Investigation

1. **Confirm the cron is actually running through the short-circuit.** Pulled a recent Spotify run from `.github/workflows/spotify-sync.yml` Actions logs. The script printed `Updated now/index.html.` — meaning `content_changed()` returned `True`. So the short-circuit *was* defeated, not bypassed.

2. **Diff a representative pair of commits.** Two consecutive Spotify commits 30 minutes apart, no upstream listening activity in that window:
   ```
   git diff HEAD~2 HEAD~1 -- now/index.html
   ```
   Result: a handful of lines flipped between `16h ago` ↔ `17h ago`, `1h ago` ↔ `just now`, and the `Auto-updated April 29, 2026 at …` eyebrow.

3. **Trace where the relative-time strings come from.** Earlier in the project's history (`feat/real-time-relative-stamps`, 2026-04-23) `bin/_shared.py` gained a `relative_time_html()` helper that emits:
   ```html
   <time datetime="2026-04-29T01:23:45Z" data-rel>17h ago</time>
   ```
   The `datetime` attribute is the upstream play time (stable). The visible text is computed from `relative_time(iso_str)` at sync-time. A companion JS upgrader at `now/now.js:88-112` rewrites `textContent` from `datetime` on `DOMContentLoaded` and every 60 s — meaning **the server-rendered text is just a no-JS / first-paint fallback that the client immediately overwrites**.

4. **The `Auto-updated` line was already getting stripped — why wasn't the relative-time line?** Read `content_changed()` carefully. The `date_pattern` regex covered only the "Auto-updated April 29, 2026 at 10:15 AM PDT" eyebrow. The `<time data-rel>17h ago</time>` text was untouched, so `re.sub(date_pattern, "", …)` did not normalize it away.

5. **Confirm the same bug shape applies to the Spotify state cache.** `update-spotify.py:207` does its own SHA-1 over `date_stripped` — the strip pattern was identical. Same defect, same effect (the cache always missed).

## Root cause

`content_changed()` was specified to ignore "wall-clock-driven decorations," but the spec was incomplete. When the live-relative-stamps feature shipped on 2026-04-23, it introduced a new wall-clock-driven decoration (`<time data-rel>…</time>` text) without extending the strip pattern. The two-line oversight quietly downgraded the no-op short-circuit across **every cron sync script that calls `content_changed()`**, plus the Spotify state-cache hash.

The bug was easy to miss because:

- The HTML diff each commit produced was tiny (one or two lines flipping `Nh ago` → `(N+1)h ago`).
- The actual end-user experience was unaffected — the `now/now.js` upgrader rewrites the text on every page load, so visitors always saw correct relative times.
- The fake diffs were correlated with cron cadence, not user activity, so it didn't show up as user-facing flakiness.
- `git log` noise is a "smell" rather than an alert — it doesn't fail tests or trip a monitor.

## Solution

Extend the strip to cover both decoration classes, generalize it as a reusable helper, and have the Spotify state-cache hash route through the same helper.

In `bin/_shared.py`:

```python
_VOLATILE_DATE_RE = re.compile(
    r"Auto-updated [A-Z][a-z]+ \d+, \d{4}(?: at \d{1,2}:\d{2} [AP]M [A-Z]{2,4})?"
)
# Match the visible text inside a <time data-rel> element ("17h ago", "just now"
# etc.). The text reformats on every wall-clock minute via now/now.js, so
# without stripping it here every cron run sees a "diff" on a no-op rebuild
# and pushes a timestamp-only commit.
_VOLATILE_REL_TIME_RE = re.compile(
    r"(<time\b[^>]*\bdata-rel\b[^>]*>)[^<]*(</time>)"
)


def strip_volatile(content: str) -> str:
    """Strip time-volatile substrings so content-equality checks compare the
    upstream payload, not the wall-clock-driven 'Nm ago' / 'Auto-updated …'
    decorations. Keeps the surrounding <time datetime="..." data-rel> shell so
    structural diffs (added/removed feed entries) are still detected."""
    content = _VOLATILE_DATE_RE.sub("", content)
    content = _VOLATILE_REL_TIME_RE.sub(r"\1\2", content)
    return content


def content_changed(old_content: str, new_content: str) -> bool:
    """Check if content changed meaningfully (ignoring time-volatile substrings)."""
    return strip_volatile(old_content) != strip_volatile(new_content)
```

The capture groups in `_VOLATILE_REL_TIME_RE` and the `re.sub(…, r"\1\2", …)` replacement preserve the surrounding `<time datetime="…" data-rel>` opening tag and `</time>` closing tag. That matters: a structural diff (a feed entry added or removed) still flips the bytes around the `<time>` element, so the no-op short-circuit only fires when the *upstream payload* is unchanged.

Then in `bin/update-spotify.py`:

```python
from _shared import strip_volatile

# Content-hash cache: skip HTML write if upstream tracks + podcast haven't
# changed. Strip both the Auto-updated date AND the <time data-rel> visible
# text — both reformat every minute via now/now.js, so without stripping
# them every cron run sees a fake "diff" and pushes a timestamp-only commit.
tracks_hash = hashlib.sha1(strip_volatile(html_block).encode()).hexdigest()[:12]
```

After the fix, `content_changed()` returns `True` only when an actual track plays, episode changes, or an entry is added/removed — the Spotify cron now commits roughly *as often as the user actually listens to something new* instead of every 30 minutes.

## Prevention

The hard part is keeping `strip_volatile()` in sync with whatever wall-clock-driven decorations the rendered HTML acquires over time. Three guardrails:

1. **Single source of truth.** Every server-side render of a relative-time element goes through `_shared.relative_time_html()`. Adding a new caller is fine — adding a *new* server-rendered relative-time helper that bypasses `_shared` would re-create this bug. Code review should treat any new pattern of "render a wall-clock-derived string into now/index.html" as a flag.

2. **Companion strip.** `strip_volatile()`'s docstring explicitly names what it strips. Any new emitter pattern (e.g., a "released N days ago" badge with a different element shape) needs a matching regex added to `strip_volatile()` in the same change. Pre-commit hook running the test suite enforces that the no-op assertion in `tests/test_shared.py::TestContentChanged` still passes against new fixture content.

3. **Operational signal.** The fake-commit symptom is detectable from `git log` cadence. If you ever see a sync script committing more frequently than its upstream is producing distinct events (Spotify committing every 30 min when listening is sparse, WHOOP committing daily when no new sleep data arrived), treat it as the same bug class first — the cause is almost certainly *something* in the rendered HTML changing on a wall clock that `strip_volatile()` doesn't know about yet.

## Verification

After the fix landed in `a258625`, monitor:

```bash
# Spotify commits in the last 24h — should track listening cadence, not cron cadence
git log --since="24 hours ago" --grep="Spotify" --oneline | wc -l
```

Pre-fix: 40-48. Post-fix: equal to the number of distinct listening sessions in the window (typically 5-15).

The matching test guard:

```python
# tests/test_shared.py
def test_strip_volatile_removes_relative_time_text(self):
    """Wall-clock-driven 'Nh ago' inside <time data-rel> must not count
    as a content change between sync runs."""
    a = '<li>Track A <time datetime="2026-04-29T00:00:00Z" data-rel>1h ago</time></li>'
    b = '<li>Track A <time datetime="2026-04-29T00:00:00Z" data-rel>2h ago</time></li>'
    assert content_changed(a, b) is False
```

A structural-diff regression test ensures the strip doesn't over-match:

```python
def test_strip_volatile_preserves_structural_diffs(self):
    """Adding a new feed entry must still register as a content change
    even if its <time data-rel> text differs."""
    a = '<li>A <time datetime="t1" data-rel>1h</time></li>'
    b = '<li>A <time datetime="t1" data-rel>1h</time></li><li>B <time datetime="t2" data-rel>1h</time></li>'
    assert content_changed(a, b) is True
```

## Cross-references

- **Fix commit:** `a258625` (`refactor: code-review batch B — Python sync hardening`).
- **Origin commit** (where the bug was introduced): `3b56de4` on the now-deleted `feat/real-time-relative-stamps` branch — the `relative_time_html()` helper and the `now/now.js` upgrader landed without a corresponding update to `content_changed()`.
- **Sibling sync-pipeline solution docs:**
  - `docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md` — the WHOOP/Trakt encrypted-committed-token pattern that runs in the same cron pipeline.
  - `docs/solutions/integration-issues/plex-home-server-api-via-relay-for-github-actions.md` — Plex relay URL pattern, also routed through `_shared.content_changed()`.
- **Memory:** `project_now_page_feeds.md` includes the `<time data-rel>` ↔ `content_changed()` interaction under the "Live-relative timestamps" section so future agents browsing memory see it before they touch the strip pattern.
