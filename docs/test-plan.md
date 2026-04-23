# Test Plan — jameschang.co

Testing strategy, inventory, and execution cadence for the site and its automation scripts.

## Test Types

### Unit Tests (7 files)

**What they test:** Individual Python functions in isolation — the pure logic that transforms data, escapes HTML, formats time, and replaces content markers.

**Tool:** `pytest` (Python 3, no external dependencies)

**Run locally:**
```bash
python3 -m pytest tests/ -v
```

**Execution cadence:** On every commit (via GitHub Actions CI) and locally before pushing.

| Test file | Covers | Functions tested |
|-----------|--------|-----------------|
| `tests/test_shared.py` | `bin/_shared.py` | `escape_html`, `relative_time`, `replace_marker`, `content_changed`, `sanitize_error`, `record_heartbeat` (incl. corrupt JSON recovery), `_refresh_page_updated_marker` |
| `tests/test_feeds.py` | `bin/update-whoop.py`, `bin/update-public-feeds.py` | `recovery_color`, `ordinal` |
| `tests/test_trakt.py` | `bin/update-trakt.py` | `build_html` (rendering, escaping, empty state), `fetch_recent_shows` (deduplication, 5-show limit) |
| `tests/test_feed_builders.py` | All feed builders | `mlb_block`, `letterboxd_block`, `goodreads_reading_block`, `goodreads_block`, `fbst_block`, `plex build_html` + `plex fetch_history` failure path — mocked network |
| `tests/test_spotify.py` | `bin/update-spotify.py` | `build_html`, `load_state`/`save_state`, `fetch_recent_tracks`, `fetch_current_podcast` |
| `tests/test_whoop.py` | `bin/update-whoop.py` | `fetch_latest_recovery`/`sleep`/`cycle`, `build_html` with all recovery color thresholds |
| `tests/test_projects.py` | `bin/update-projects.py` | `extract_tldr` (marker extraction, edge cases), `load_config` (schema, repo paths) |

### E2E Tests (`tests/test_site_e2e.py`)

**What they test:** The full site from a user's perspective — pages load, links resolve, meta tags are present, CSP headers exist, theme toggle works, accessibility attributes are correct, images load.

**Tool:** Python + `http.server` + `urllib` (no external dependencies — validates HTML structure and HTTP responses, not visual rendering)

**Run locally:**
```bash
python3 -m pytest tests/test_site_e2e.py -v
```

**Execution cadence:** On every push to `main` (via GitHub Actions CI) and locally before deploying CSS/HTML changes.

| Test | What it checks |
|------|---------------|
| Page loads | Every HTML page returns 200 |
| CSP headers | All pages have Content-Security-Policy meta tag |
| Meta tags | All pages have viewport, color-scheme, referrer, title, description |
| aria-pressed | Theme toggle has `aria-pressed="false"` on all pages |
| object-src | CSP includes `object-src 'none'` on all pages |
| Internal links | All `href` values pointing to local paths resolve to real files |
| Image references | All `<img src>` and `<source srcset>` files exist |
| JSON-LD | Structured data is valid JSON on all pages |
| Feed markers | `now/index.html` has paired START/END markers for all feeds + `PAGE-UPDATED` eyebrow marker |
| Print stylesheet | Key print-only elements exist in `index.html` |
| OpenSSL parity | All `openssl enc` calls use matching `-iter 600000` |
| Dark mode parity | `@media (prefers-color-scheme: dark)` count matches `[data-theme="dark"]` count in CSS |
| GA4 presence | GA4 snippet (G-B3HW5VBDB3) present on all pages |
| GA4 CSP | CSP allows googletagmanager.com on all pages |
| Privacy feeds | Privacy policy lists all 6 feed data sources |
| Privacy GA4 | Privacy policy discloses GA4 measurement ID |

## Execution Cadence Summary

| When | What runs | How |
|------|-----------|-----|
| **Every commit** | Unit tests | `python3 -m pytest tests/ -v` |
| **Push to main** | Unit + E2E tests | GitHub Actions (`ci-tests.yml`) |
| **Before deploy** | Full suite + manual visual check | Local pytest + screenshot |
| **Every 6 hours** | Feed staleness check | `feeds-staleness-check.yml` runs `bin/check-feed-health.py` — opens / comments / auto-closes GitHub issues labeled `feed-stale` when any feed's last_success_utc is >48h old |
| **Daily 7 AM PT** | Project TLDR + shipping sync | `projects-sync.yml` runs `bin/update-projects.py` — pulls TLDR blocks from each repo's CLAUDE.md and per-project GitHub events |

## Adding a New Test

1. **For a new Python function:** Add test cases to the appropriate file in `tests/`. Follow the existing pattern: test happy path, edge cases, and error conditions.
2. **For a new HTML page:** The E2E tests auto-discover all HTML files via glob, so new pages are automatically tested for meta tags, CSP, and link validity.
3. **For a new data feed:** Add the marker name to the `EXPECTED_MARKERS` list in `test_site_e2e.py`.

## Test Results

Tests run in CI via `.github/workflows/ci-tests.yml`. Results are visible in the GitHub Actions tab. Failures block nothing (this is a single-contributor repo with direct push), but they surface regressions early.

Last updated: 2026-04-23
