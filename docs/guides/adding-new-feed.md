# Adding a new data feed

The `/now` page syncs data from several independent sources (WHOOP, Spotify, Plex, public feeds). To add a new feed:

## Steps

1. Add a new `<section class="work-section">` to `now/index.html` with `FEED-START` / `FEED-END` markers. **Bootstrap requirement:** any new marker names introduced by the script must be seeded in `now/index.html` in the **same commit** that adds the script logic — never after. The cron's fail-safe (`replace_marker()` returning `False`) will silently preserve stale content indefinitely if markers are absent. Also add the new marker name(s) to `EXPECTED_MARKERS` in `tests/test_site_e2e.py` so CI catches any future deletion.

2. Add CSS for the feed's presentation in `projects/projects.css` (use existing CSS tokens). Follow the naming convention: `.{feed}-module`, `.{feed}-heading`, `.{feed}-list`, `.{feed}-when`, `.{feed}-updated`.

3. Write a Python function that fetches + returns the HTML block; add to `bin/update-public-feeds.py` (for unauthenticated) or a new `bin/update-{feed}.py` (for OAuth). In `update-public-feeds.py`, add a tuple to the `feeds` list: `("MARKER_NAME", builder_function, 'fallback_html')`.

4. Add the fetch to the `main()` of the sync script; use `replace_marker()` to insert.

5. If OAuth: add a callback page at `/{service}/callback/`, auth script at `bin/{service}-auth.sh`, workflow at `.github/workflows/{service}-sync.yml`.

6. Call `record_heartbeat("feed_name")` from `_shared.py` in the sync script's `main()` — both on success and on early-return (no-change) paths. The 6-hour staleness check (`bin/check-feed-health.py` run by `.github/workflows/feeds-staleness-check.yml`) opens a GitHub issue (labeled `feed-stale`) if any feed's `last_success_utc` is >48h old, comments on existing open issues instead of duplicating, and auto-closes them when the feed recovers. Note: the 48h threshold may not suit feeds that update less frequently (e.g. weekly).

7. If the new feed fetches from an external domain client-side, add the domain to the CSP `connect-src` directive in `now/index.html`.

8. Sync scripts must be invoked as `python3 bin/update-{feed}.py` from the repo root (not imported as modules).

## Current feeds

**Canonical 8 feeds with staleness heartbeats** (`.feeds-heartbeat.json`):

- **WHOOP** — daily via `.github/workflows/whoop-sync.yml`. Refresh token stored encrypted in the repo (`.whoop-token.enc`), decrypted at runtime with a GitHub Secret passphrase (`WHOOP_TOKEN_KEY`), re-encrypted + committed each run. **Required Secrets:** `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, `WHOOP_TOKEN_KEY`.
- **Spotify** — every 30 minutes via `.github/workflows/spotify-sync.yml`. Refresh token stored in plain text as a GitHub Secret (`SPOTIFY_REFRESH_TOKEN`); the script writes `.spotify-state.json` to remember the last-seen podcast episode. The 30-min cadence maximizes podcast capture rate. **Required Secrets:** `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`.
- **Plex** — every 6 hours via `.github/workflows/plex-sync.yml`. Static token (no rotation). Connects via Plex relay URL. **Required Secrets:** `PLEX_URL`, `PLEX_TOKEN`.
- **Google Calendar** — hourly at `:00 UTC` via `.github/workflows/gcal-sync.yml`. Fetches a public iCal feed, parses with hand-rolled stdlib parser, filters to future events, sorts by PT datetime, groups consecutive same-prefix events, caps at 20. **Required Secret:** `GCAL_ICAL_URL`.
- **Public feeds** — every 6 hours via `.github/workflows/public-feeds-sync.yml`. MLB Stats API (Dodgers), Goodreads RSS (currently-reading + read), The Fantastic Leagues / FBST standings. All unauthenticated; no secrets needed.
- **Trakt** — **disabled 2026-04-28**. Workflow renamed to `.github/workflows/trakt-sync.yml.disabled`. Token and Secrets preserved for re-enable.

**Client-side sections** (not feeds — no heartbeat):
- **Hitlist** — `thirstypig.com/places-hitlist.json`
- **Bucket list** — `bucketlist.json`
- **Quotes** — `quotes.json`

## Feed architecture

Feeds emit `notebook.css`-compatible markup directly:
- All feeds: `.feed-empty` and `.feed-updated` classes
- WHOOP: `.nb-grid-4` + `.nb-stat` tiles
- Spotify: `.nb-feed-podcast` lead-in
- General: bare `<ul>` / `<li>` styled by `.nb-feed` cascade

**Content-hash cache** — sync scripts skip `git commit && push` when rendered HTML matches existing HTML modulo time-volatile substrings. `_shared.strip_volatile()` strips the `Auto-updated …` eyebrow AND `<time data-rel>…</time>` elements (the latter reformats every minute via `now/now.js`). **If you add a new server-rendered relative-time string**, extend `_VOLATILE_REL_TIME_RE` — otherwise every cron run produces timestamp-only commits.

**Top-of-page eyebrow refresh** — `<!-- PAGE-UPDATED-START -->...<!-- PAGE-UPDATED-END -->` refreshed automatically every time any feed script calls `write_now_html()` in `_shared.py`. Single source of truth: whatever feed most recently synced sets the timestamp.
