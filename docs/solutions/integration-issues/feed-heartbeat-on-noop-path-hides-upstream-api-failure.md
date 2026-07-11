---
title: "A health heartbeat recorded on the no-op path masked a 2-week Spotify 403 outage — the staleness monitor never fired"
category: integration-issues
tags: [sync-pipeline, cron, github-actions, heartbeat, staleness-monitor, health-check, spotify, silent-failure, observability]
symptom: "a /now feed stopped updating for weeks while its GitHub Actions workflow kept succeeding and the feed-staleness monitor never opened an issue"
root_cause: "update-spotify.py's api_get() swallowed HTTPError and returned None; a 403 on the data endpoints therefore looked identical to 'nothing playing', so the script took its no-op 'unchanged, skip write' path — which still called record_heartbeat('spotify') with no error=. The heartbeat's last_success_utc stayed fresh every 30 minutes, so check-feed-health.py (fires when last_success_utc > 48h) never saw the feed as stale. The feed silently degraded to 'Nothing recent'."
module: now-page-sync-pipeline (bin/update-spotify.py, bin/check-feed-health.py, bin/_shared.py)
date_solved: 2026-07-10
severity: medium
---

# A no-op-path heartbeat hid a silent Spotify 403 outage from the staleness monitor

## Symptom

The `/now` page's Spotify feed showed **"Nothing recent — the Action runs every few hours"** with an `Auto-updated June 24` timestamp that never advanced. Meanwhile:

- The `spotify-sync.yml` GitHub Actions workflow reported **success on every run** (every 30 minutes, 8–15s each) — no red X, no failure email.
- The **feed-staleness monitor never fired** — no `feed-stale` GitHub issue was opened, even though the feed had been dead for **more than two weeks**.

In other words: three independent safety nets (the feed content, the workflow status, the staleness monitor) all reported "fine" while the feed was broken. The outage was only discovered when a human noticed the frozen date.

## Investigation

1. **Checked the rendered block + state file.** `now/index.html`'s `SPOTIFY` marker showed the empty state; `.spotify-state.json` had `last_podcast.captured_at: 2026-06-17` and its last commit was `2026-06-24 21:07 UTC`. Nothing since.
2. **Checked the workflow runs** — `gh run list --workflow=spotify-sync.yml`. Every run for weeks was `completed / success`. This ruled out "workflow broken" and reframed the question: *the sync is running fine but producing no commit.*
3. **Read the actual script stdout from a run log** — this was the key step:
   ```
   API /me/player/recently-played failed: HTTP 403 (could not parse error body)
   API /me/player/currently-playing failed: HTTP 403 (could not parse error body)
   Stale podcast (>7d old), hiding.
   Tracks + podcast unchanged, skipping write.
   ```
   Two distinct failures were stacked here: (a) an **external cause** — the Spotify API returning `403` while token *refresh still succeeded*; and (b) an **observability bug** — the script treating that 403 as "nothing to report" and recording a healthy heartbeat anyway.

## Root cause

### Two layers

**External (the trigger):** Spotify's data endpoints returned **HTTP 403** (not 401). Token refresh (`get_access_token()`) still succeeded — no "Token refresh failed" line — so the refresh token was alive. A 403-not-401 on user-data endpoints means *authenticated but not authorized*: a scope/grant problem on Spotify's side, not an expired token and not a code bug. (Fix for the feed itself: re-run `./bin/spotify-auth.sh` to mint a fresh grant with the correct scopes — the script requests `user-read-recently-played user-read-playback-state` — and update the `SPOTIFY_REFRESH_TOKEN` secret; if it persists, check spotify.com/account/apps and the Developer Dashboard app state.)

**Internal (why it went silent for 2 weeks — the real lesson):** `api_get()` swallowed the `HTTPError` and returned `None`, and `fetch_recent_tracks()` mapped `None` → `[]`. So a 403 was **indistinguishable from "user genuinely hasn't listened."** The script then:

1. Rendered the empty "Nothing recent" block (same as it had been since June 24).
2. Computed the content hash, which matched the already-empty block.
3. Took the no-op branch — **which recorded a success heartbeat**:

```python
# bin/update-spotify.py (before the fix)
tracks_hash = hashlib.sha1(strip_volatile(html_block).encode()).hexdigest()[:12]
old_hash = state.get("last_tracks_hash")

if tracks_hash == old_hash and not state_dirty:
    record_heartbeat("spotify")          # ← fires even though the API 403'd
    print("Tracks + podcast unchanged, skipping write.")
    return
```

### Why the heartbeat matters

The staleness monitor keys **only on `last_success_utc`**, by design:

```python
# bin/check-feed-health.py
STALE_HOURS = 48
...
last = info.get("last_success_utc")        # last_run alone doesn't count
if not last:
    return float("inf")
...
is_stale = hours > STALE_HOURS
```

And `record_heartbeat(feed, error=None)` in `_shared.py` **refreshes `last_success_utc` whenever `error` is falsy**. Calling it with no `error=` on the no-op path told the monitor "this feed just succeeded" — every 30 minutes, forever. `last_success_utc` never aged past 48h, so no issue was ever opened. A 403 masqueraded as "healthy but quiet."

## The fix

Distinguish **"the API said no"** from **"nothing playing,"** and refuse to record a healthy heartbeat on the former. A module-level flag set in the one place that already knows about the failure:

```python
# bin/update-spotify.py — flag set at the HTTPError source
_api_error = False

def api_get(token, path, params=None):
    ...
    except HTTPError as e:
        global _api_error
        _api_error = True
        print(f"API {path} failed: {sanitize_error(e)}", file=sys.stderr)
        return None
```

```python
# bin/update-spotify.py — main() bails BEFORE any heartbeat when a fetch errored
tracks = fetch_recent_tracks(token)
current = fetch_current_podcast(token)

if _api_error:
    # A data endpoint returned an HTTP error (most often a 403 after a scope was
    # revoked — token refresh still succeeds, so it isn't caught upstream). Leave
    # /now untouched and DON'T record a heartbeat: a transient error self-heals
    # next run, while a persistent one lets the staleness monitor open a single
    # issue after 48h instead of the feed dying silently for weeks.
    print(
        "Spotify API error — leaving /now unchanged and skipping the heartbeat "
        "so the staleness monitor can flag it. Re-auth with ./bin/spotify-auth.sh.",
        file=sys.stderr,
    )
    return
```

**Why `return` and not `sys.exit(1)`:** failing the workflow would emit a red run + email *every 30 minutes*. The intended alerting channel is the staleness monitor, which opens exactly **one** issue after 48h with feed-specific guidance (for Spotify: *"Run `./bin/spotify-auth.sh` and update the `SPOTIFY_REFRESH_TOKEN` GitHub Secret."*). Skipping the heartbeat routes the failure to that channel: transient errors self-heal on the next run; persistent ones trip the monitor once.

### Regression tests

`tests/test_spotify.py::TestSpotifyApiErrorSkipsHeartbeat`:
- `test_api_error_skips_heartbeat_and_leaves_page` — when a fetch sets `_api_error`, `main()` records **no** heartbeat and rewrites **no** HTML.
- `test_no_api_error_still_records_heartbeat` — the happy "quiet but healthy" path still heartbeats, so a genuinely-idle feed isn't misreported as stale.

## Blast radius — this anti-pattern lives in two other scripts

An audit of all cron feed scripts found the **identical vulnerability** in two more. The signature: an `api_get`/events helper that **degrades an HTTP error into an empty payload**, then `record_heartbeat(<slug>)` with no `error=` on a path reachable after that swallowed error.

| Script | Swallows HTTPError to empty? | Guards the heartbeat? | Status |
|---|---|---|---|
| `update-spotify.py` | was Yes → `None` | now bails on `_api_error` before heartbeat | **fixed 2026-07-10** |
| `update-whoop.py` | Yes → `{"records": []}` | now bails on `_api_error` before heartbeat | **fixed 2026-07-10** |
| `update-projects.py` | Yes → `[]` (events) | now bails when `_events_ok==0 and _events_err>0` | **fixed 2026-07-10** |
| `update-plex.py` | Returns `None`, distinguished (`:55`) | Yes — `error=` heartbeat (`:144`) | already correct |
| `update-public-feeds.py` | blocks return `None` (`:128`…) | Yes — `error=` passed (`:348`) | already correct |
| `update-project-docs.py` | `None` → error tuple (`:729`) | Yes — early error return (`:788`) | already correct |

All three fixes share the shape "flag the failure at the `HTTPError` source, check it before the heartbeat." Spotify and WHOOP hit shared-scope single-user endpoints, so **any** `HTTPError` sets a module-level `_api_error` and `main()` returns before the heartbeat. `update-projects.py` fans out per-repo, where an isolated single-repo failure is expected and must stay isolated — so it tallies `_events_ok` vs `_events_err` and only bails on the **systemic** case (zero successes, ≥1 error), which is what a dead `TLDR_FETCH_TOKEN` produces (a bad token 401s every request). Regression tests: `tests/test_whoop.py::TestWhoopApiErrorSkipsHeartbeat`, `tests/test_projects.py::TestSystemicEventFailureSkipsHeartbeat`.

- **`update-whoop.py`**: a data-endpoint 403 (WHOOP's exact analog to Spotify) is swallowed to `{"records": []}`, `build_html(None, None, None)` renders em-dash placeholders, and both heartbeat calls (`:278`, `:283`) fire with no `error=`. Same silent-outage risk.
- **`update-projects.py`**: `fetch_repo_events` swallows `HTTPError`/`URLError` to `[]` (`:156`). A persistent 403 — e.g. an **expired `TLDR_FETCH_TOKEN`** — makes every project render "no recent activity" while `record_heartbeat("projects")` (`:556`/`:561`) keeps `last_success_utc` fresh. Ironically, `check-feed-health.py`'s own guidance for the `projects` slug blames an expired `TLDR_FETCH_TOKEN` — the very failure this script currently can't surface.

The scripts that got it **right** (`update-plex.py`, `update-public-feeds.py`, `update-project-docs.py`) all follow the same correct idiom: on an HTTP/network error they return a **sentinel distinct from empty** (`None` vs `[]`) and pass `error=` to `record_heartbeat` (or return before the success heartbeat), which **preserves** the old `last_success_utc` so the feed ages into staleness.

## Prevention strategies

1. **A heartbeat must mean "upstream really succeeded," never "the script didn't crash."** The no-op / "nothing changed" path is *not* proof of upstream health — it's reachable whenever fetches return empty, including on swallowed errors. Only record a success heartbeat on a path you can prove was reached with good data.
2. **Never collapse "API error" and "empty result" into the same value.** If a fetch helper returns `[]`/`None`/`{}` on both a 403 and a legitimately-empty response, the caller has lost the only bit that matters for alerting. Return a distinct error sentinel (or set a flag), the way `update-plex.py` returns `None`-means-error vs `[]`-means-empty.
3. **On a swallowed fetch error, skip the success heartbeat (or pass `error=`) — don't fail the workflow.** Route persistent failures to the 48h staleness monitor (one issue, actionable guidance) rather than to per-run red builds (noise every N minutes).
4. **403 ≠ 401.** A successful token refresh followed by 403s on data endpoints is an authorization/scope problem, not an expired token. Don't assume "the OAuth flow is fine" means "the API calls will work."
5. **Consider a canary independent of the data path** (see the OAuth token-rotation doc): a tiny health probe that verifies the credential can actually read data, so breakage surfaces even when the data happens to render as "empty."
6. **When adding a new cron feed, add the heartbeat-correctness check to review:** does any path that records a success heartbeat run when the upstream fetch errored? If yes, it's this bug.

## Follow-up (resolved 2026-07-10)

`update-whoop.py` and `update-projects.py` carried the same pattern and were fixed in the same pass — see the blast-radius table above. All three vulnerable feeds now route a persistent upstream failure to the staleness monitor instead of hiding it behind a fresh heartbeat.

## See also

- [`relative-time-html-defeats-content-changed-cache.md`](./relative-time-html-defeats-content-changed-cache.md) — the exact no-op content-cache path (`content_changed()` + `.spotify-state.json` hash) that the heartbeat was wrongly recorded on.
- [`per-project-adapters-for-heterogeneous-roadmap-sources.md`](./per-project-adapters-for-heterogeneous-roadmap-sources.md) — "bootstrap-aware heartbeat gating"; the *inverse* correctness concern (don't record an *error* heartbeat for a feed that never succeeded). Together these two docs define the full heartbeat-correctness picture.
- [`marker-boundary-content-staleness.md`](./marker-boundary-content-staleness.md) — the staleness monitor's other blind spot (orphan `feed-stale` issues for retired slugs); same `check-feed-health.py` machinery.
- [`oauth2-refresh-token-rotation-encrypted-committed-file.md`](./oauth2-refresh-token-rotation-encrypted-committed-file.md) — its debugging checklist on 403 vs 401/429 and the "add a canary independent of the data sync" recommendation.
- [`silent-fetch-failure-csp-graceful-fail-debugging.md`](./silent-fetch-failure-csp-graceful-fail-debugging.md) — same failure family: a graceful-fail path masking a real upstream error.
