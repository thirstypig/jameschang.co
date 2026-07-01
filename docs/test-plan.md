# Test Plan — jameschang.co

Testing strategy, inventory, and execution cadence for the site and its automation scripts.

## Test Types

### Unit Tests (10 files)

**What they test:** Individual Python functions in isolation — the pure logic that transforms data, escapes HTML, formats time, and replaces content markers.

**Tool:** `pytest` (Python 3, no external dependencies)

**Run locally:**
```bash
python3 -m pytest tests/ -v
```

**Execution cadence:** On every commit (via GitHub Actions CI) and locally before pushing.

| Test file | Type | Count | What it covers |
|-----------|------|-------|---|
| `tests/test_shared.py` | Unit | 48 | `_shared.py`: escape_html, relative_time, **relative_time_html** (live-relative progressive enhancement), replace_marker, content_changed, sanitize_error, record_heartbeat (incl. corrupt JSON recovery), page-updated marker refresh |
| `tests/test_feeds.py` | Unit | 11 | `update-whoop.py`: recovery_color; `update-public-feeds.py`: ordinal |
| `tests/test_trakt.py` | Unit | 10 | `update-trakt.py`: build_html rendering, HTML escaping, deduplication by show, 5-show limit, regression assertions that legacy `trakt-*` classes are no longer emitted |
| `tests/test_feed_builders.py` | Unit | 20 | Feed builders for mlb, letterboxd, goodreads (reading + read), fbst, plex — mocked network, tested HTML output; plex fetch failure returns None vs []; regression assertions that legacy `plex-*` classes are no longer emitted; **idempotency tests** (plex, mlb, goodreads, fbst determinism) |
| `tests/test_spotify.py` | Unit | 18 | `update-spotify.py`: build_html (asserts `nb-feed-podcast` + bare `<ul>`), state load/save, fetch_recent_tracks, fetch_current_podcast; **idempotency tests** (tracks, podcast, empty data determinism) |
| `tests/test_whoop.py` | Unit | 20 | `update-whoop.py`: fetch_latest_recovery/sleep/cycle, build_html with all recovery colors; **idempotency tests** (full data, none data, partial data determinism) |
| `tests/test_feed_health.py` | Unit | 5 | `check-feed-health.py`: transient 5xx/timeout errors exit cleanly (code 0) while non-transient errors (auth failures) still propagate and fail the workflow |
| `tests/test_projects.py` | Unit | 68 | `update-projects.py`: TLDR extraction (dead code, kept for test compat), config schema (**10 projects**; all must have `maturity` + `desc` + `next_up` with valid enum values), PR-event filtering, render_shipping_list, render_block, **classify_projects** (active/back-burner threshold = 7 days; project with no events → back-burner; edge case at exactly threshold pinned), **render_badge** (icon selection: code/globe/lock/clock; maturity label; XSS sanitization), **render_activity_box** (filled vs empty state; data-rel timestamp), **render_card** (activity-first order asserted; badge with maturity; desc + next_up + **roadmap_items from config**; URL safety incl. **blank-url project → href="#" fallback + no dangling domain span**, the Vouch shape); **idempotency tests** (deterministic render, config-drives-output) |
| `tests/test_gcal.py` | Unit | 32 | `update-gcal.py`: VEVENT parsing (line continuations, escapes, TZID + UTC + all-day), filter past events + sort by full PT datetime (same-day-time-of-day ordering pinned), `_first_n_words_key` + `group_consecutive_by_prefix` (the first-3-words rule + consecutive constraint), `merge_group` (title trim + date span union), `build_html` (URL anchor only on http/https, multi-line LOCATION whitespace collapse, no per-card source tag, multi-day all-day range rendering, MAX_UPCOMING cap exercised); **idempotency tests** (event rendering, empty events determinism) |
| `tests/test_project_docs.py` | Unit | 63 | `update-project-docs.py`: convention changelog parser (heading-line: version + date + tags; date trailing suffix preserved; ASCII fallback; bullet continuation lines), convention roadmap parser (H2 module + percent; H3 Workflow/Features; task-list states `[x]`/`[ ]`/`[~]`), **Aleph adapter** (percent from Project Health table; bounded to Compliance Module Roadmaps section), **JT adapter** (`## PHASE N:` extraction; non-task-list bullets ignored), **FL Tsx adapter** (`productRoadmap` array extraction via brace-counted slicing; nested-brace handling in descriptions; `in-progress` → `planned` lossy mapping), HTML renderers (escape-then-bold/code; unknown tags get sanitized class; `percent=None` omits progress badge; optional blocks omitted when empty), **adapter factory** (`make_adapter` closure pattern; source-missing / unparseable error contracts), **sync_one fail-safe** (source-missing → skipped, no heartbeat on bootstrap; source-missing + known feed → error recorded while preserving prior last_success_utc; unknown doctype + missing destination → error), **PROJECT_DOCS invariants** (6 entries pinned; every adapter callable; wired destinations have matching marker pair); **idempotency tests** (changelog, roadmap, empty render determinism) |

### E2E Tests (`tests/test_site_e2e.py`)

**What they test:** The full site from a user's perspective — pages load, links resolve, meta tags are present, CSP headers exist, theme toggle works, accessibility attributes are correct, images load.

**Tool:** Python + `http.server` + `urllib` (no external dependencies — validates HTML structure and HTTP responses, not visual rendering)

**Run locally:**
```bash
python3 -m pytest tests/test_site_e2e.py -v
```

**Execution cadence:** On every push to `main` (via GitHub Actions CI) and locally before deploying CSS/HTML changes.

**80 E2E tests** covering:

All HTML pages: meta tags, CSP, aria-pressed, JSON-LD, images, internal links, feed markers (incl. PAGE-UPDATED), @media print + @page rule on notebook.css, OpenSSL parity, dark mode parity, GA4, privacy policy, symlink detection, sitemap consistency, OG image, **top-nav consistency** (brand text, no [about], [/now] slash prefix, experience→projects→now order across all pages), **cross-project nav** (presence + canonical hrefs + aria-current on 13 deep-dive pages), **/now section structure** (sequential /01–/09 numbering + /07 watching/listening/reading sub-feeds, no Trakt/Letterboxd), **resume print pipeline** (print-name-block presence on homepage only + screen-hidden + canonical contact URLs; script.js beforeprint listener that opens `<details>` so the 8 additional certifications expand in resume.pdf; `.nb-card-name` print rule overrides screen sizing), **bucket list** (`bucketlist.json` schema + unique ids + status/completed-date invariants, /now render-target + hitlist title rename + link to /bucketlist/, public page loads + renderer script resolves + render targets present, no top-nav link to /bucketlist/), **project doc sync markers** (6 destination pages have matching CHANGELOG/ROADMAP marker pairs — bootstrap guard for `bin/update-project-docs.py`), **project card roadmaps** (all active projects have `.nb-proj-roadmap` divs, each with non-empty list items and label — guards against roadmap_items being deleted by cron), **FL Roadmap internal nav** (5 FL deep-dive pages link to `/projects/fantastic-leagues/roadmap/` in `.project-nav`; pre-promotion external href is asserted absent from any FL nav), **quotes** (`quotes.json` schema + unique ids + every-quote-has-a-source discipline + collection/poem `entries[]` + `link` http(s) validation + Bruce Lee box excludes verified misattributions / Goethe line is its own correctly-attributed card, `#quotes-section` render target + `#quote-modal` dialog present, `now.js` fetches `/quotes.json`), **detail cards** (people i follow `/09` + off-the-clock `/06` top list render as `.nb-detail-card`s — 14 total, 7+7 — each with a trigger + `<template>`; `#detail-modal` dialog present; `now.js` wires `.nb-detail-trigger` → clone template, not innerHTML).

## Execution Cadence Summary

| When | What runs | How |
|------|-----------|-----|
| **Every commit** | Unit tests | `python3 -m pytest tests/ -v` |
| **Push to main** | Unit + E2E tests | GitHub Actions (`ci-tests.yml`) |
| **Before deploy** | Full suite + manual visual check | Local pytest + screenshot |
| **Every 6 hours** | Feed staleness check | `feeds-staleness-check.yml` runs `bin/check-feed-health.py` — opens / comments / auto-closes GitHub issues labeled `feed-stale` when any feed's last_success_utc is >48h old |
| **Daily 7 AM PT** | Project TLDR + shipping sync | `projects-sync.yml` runs `bin/update-projects.py` — pulls TLDR blocks from each repo's CLAUDE.md and per-project GitHub events |
| **Daily 7:15 AM PT** | Project changelog/roadmap sync | `project-docs-sync.yml` runs `bin/update-project-docs.py` — per-project adapters fetch source-of-truth from each repo's native format (Aleph `docs/plans/roadmap.md`, JT `docs/PRODUCTION_ROADMAP.md`, FL `client/src/pages/Roadmap.tsx`) and render into the deep-dive pages. 15-min offset from `projects-sync.yml` to avoid concurrency races. See `docs/solutions/integration-issues/per-project-adapters-for-heterogeneous-roadmap-sources.md`. |

## Adding a New Test

1. **For a new Python function:** Add test cases to the appropriate file in `tests/`. Follow the existing pattern: test happy path, edge cases, and error conditions.
2. **For a new HTML page:** The E2E tests auto-discover all HTML files via glob, so new pages are automatically tested for meta tags, CSP, and link validity.
3. **For a new data feed:** Add the marker name to the `EXPECTED_MARKERS` list in `test_site_e2e.py`.

## Test Results

Tests run in CI via `.github/workflows/ci-tests.yml`. Results are visible in the GitHub Actions tab. Failures block nothing (this is a single-contributor repo with direct push), but they surface regressions early.

**375 tests total:** 295 unit tests + 80 E2E tests.

**Idempotency testing** (new pattern as of 2026-06-25): All major cron scripts now have determinism tests to guard against the trap where re-rendering unexpectedly changes output, causing false diffs. Pattern: same input → identical output (verified across 2+ calls). Coverage:
- projects (2 tests): render_card determinism, config-drives-output
- whoop (3 tests): full/partial/no-data determinism
- spotify (3 tests): tracks, podcast, empty determinism
- gcal (2 tests): events, empty determinism
- feed-builders (6 tests): plex, mlb, goodreads, fbst determinism
- project-docs (4 tests): changelog/roadmap/empty determinism
**Total: 20 idempotency tests** across all sync scripts

See `CLAUDE.md` for the full testing inventory and refer to the tables above for what each test file covers.
