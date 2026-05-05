# CLAUDE.md

Operational notes for Claude Code (and any other agent) working on this repo. For human-facing workflow see `README.md`; for design/positioning history see `PLAN.md`; for past solved problems see `docs/solutions/`.

## Stack

- **Plain static HTML/CSS/JS.** No build step. No framework. No `package.json`.
- **Hosting:** GitHub Pages on custom apex domain `jameschang.co` via A/AAAA records + `CNAME`.
- **Python 3 is the only tooling dependency** (local server + WHOOP sync script + résumé PDF generation).

## Repo layout

```
/                       Homepage (index.html + notebook.css + script.js) — Claude Design notebook direction
/now/                   Derek Sivers-style /now page (reads notebook.css)
/projects/              Deep-dive project pages (Aleph, Fantastic Leagues, Judge Tool) — each has sub-pages + dashboard prompt showcase. Loads notebook.css + projects/projects.css.
/privacy/               Privacy policy (required by WHOOP app registration). Loads notebook.css.
/whoop/callback/        OAuth2 redirect target (static page that reads ?code= from URL). Inline-styled utility page, no shared CSS.
/spotify/callback/      OAuth2 redirect target for the Spotify auth flow. Same shape as /whoop/callback/.
/assets/                Images (AVIF/WebP responsive pairs), favicons, OG image, apple-touch-icon
/assets/fonts/          Self-hosted WOFF2 (Geist Mono + Space Grotesk, latin subset) — loaded by notebook.css site-wide
/bin/                   Sync + auth scripts: _shared.py, update-{whoop,spotify,plex,trakt,public-feeds,projects}.py, check-feed-health.py, {whoop,spotify,trakt}-{auth,encrypt}.sh, projects-config.json
/.github/workflows/     GitHub Actions (WHOOP, Spotify, Plex, public feeds, projects, staleness check; trakt-sync.yml.disabled is dormant)
/docs/solutions/        Internal knowledge base — past solved problems (see /ce:compound)
/todos/                 Code-review findings (see /ce:review)
/resume.pdf             Generated from the homepage print stylesheet (notebook.css @media print)
.whoop-token.enc        AES-encrypted WHOOP refresh token (committed, decrypted at runtime)
.trakt-token.enc        AES-encrypted Trakt refresh token (preserved while the Trakt sync is disabled)
.feeds-heartbeat.json   Timestamped heartbeats per feed (committed by sync workflows)
```

**One design system, two stylesheets.** The Claude Design "notebook" direction was cut over site-wide on 2026-04-27. Every content page (`/`, `/now/`, `/projects/*`, `/privacy/`) loads `/notebook.css` and shares the same design language: forest-green/clay accent, hard-shadow cards, graph-paper grid, Geist Mono + Space Grotesk fonts.

The `/projects/*` deep-dives additionally load `/projects/projects.css` for component-specific classes (`.release`, `.module`, `.snapshot-banner`, `.terminal`, `.lightbox`, `.arch-block`, `.scorecard`, `.feature-list`, `.comp-table`, etc.) — but `work.css` was **retokenized** to consume notebook design tokens (`var(--ink)`, `var(--surface)`, `var(--display)`, etc.) so visually the work sub-pages render in the same notebook aesthetic. Eventually `work.css` could be merged into `notebook.css`; it stays separate for now to avoid bloating the site-wide stylesheet with classes used only on 14 deep-dive pages.

## CSS token system

`notebook.css` is the single source of truth for design tokens. `work.css` references the same tokens — there's only one design language now.

| Token | Purpose |
|-------|---------|
| `--bg`, `--surface`, `--surface-2` | Page background + card surfaces |
| `--ink`, `--dim` | Primary and secondary text |
| `--accent`, `--accent-ink` | Forest green (light) / warm coral (dark), and the readable text on accent surfaces |
| `--rule`, `--tag` | Dividers + tag chips |
| `--grid` | Graph-paper grid color (very low alpha) |
| `--pos`, `--warn`, `--danger` | Status colors (used by `.nb-stat .v` and elsewhere) |
| `--mono`, `--display` | Geist Mono + Space Grotesk WOFF2 (with system fallbacks) |
| `--measure`, `--grid-size`, `--shadow-offset`, `--border-w` | Layout tokens (1100px / 24px / 3px / 1.5px) |

Dark mode is triggered via `@media (prefers-color-scheme: dark)` + an explicit `[data-theme="dark"]` override driven by `script.js` theme toggle (persisted in `localStorage`).

**Cron-script markup.** All /now feed-sync scripts (`update-whoop.py`, `update-spotify.py`, `update-trakt.py`, `update-plex.py`, `update-public-feeds.py`, `update-projects.py`) emit notebook-design markup directly — bare `<ul>` / `<li>` / `<span class="when">` styled by the parent `.nb-feed` cascade, plus two helper classes `.nb-feed-podcast` (Spotify lead-in) and `.nb-feed-divider` (dashed top border that separates Plex's list from Trakt's above it inside their shared `.nb-feed`). WHOOP emits `.nb-grid-4` + `.nb-stat` tiles. The only generic cron-only classes left in `notebook.css` are `.feed-empty` and `.feed-updated` (used by every feed for the empty state and the trailing "Auto-updated …" line). Legacy per-feed classes (`.spotify-list`, `.trakt-when`, `.whoop-green`, etc.) were removed on 2026-04-27.

**`<time data-rel>` ↔ `content_changed()` invariant.** Sync scripts skip the `git commit && push` step when the rendered HTML matches the existing HTML modulo time-volatile substrings. `_shared.strip_volatile()` strips both the `Auto-updated …` eyebrow AND the visible text inside `<time data-rel>…</time>` elements (the latter reformats every minute via `now/now.js`). **If you add a new server-rendered relative-time string**, extend `_VOLATILE_REL_TIME_RE` (or add a new pattern) — otherwise every cron run will see a fake "diff" and produce timestamp-only commits across all sync scripts. Full write-up: `docs/solutions/integration-issues/relative-time-html-defeats-content-changed-cache.md`.

## Print stylesheet

`notebook.css` has a `@media print` block (~190 lines) that reorders + restyles the homepage into a résumé PDF. **When adding a new section**, also add an `order` value in the print flex layout, or add `display: none` if the section shouldn't print. Case studies and testimonials are hidden in print (60 lines of prose confuses ATS parsers).

Current print order values (in `notebook.css`):
```
.nb-hero: 0, #about: 1, #experience: 2, #education: 3, #skills: 4, #work: 5, #memberships: 6, #contact: 7, .nb-footer: 8
#testimonials: hidden, #case-studies: hidden
```

The print stylesheet forces ATS-friendly system fonts for all elements that use `var(--mono)` on screen (dates, skill labels, role tags) — Geist Mono / Space Grotesk WOFF2 don't reliably embed in print PDFs. Notebook ornamentation (graph paper, hard shadows, /01–/08 section numbers, terminal block) is fully suppressed.

Regenerate the PDF with:
```bash
python3 -m http.server 8787 &
SERVER_PID=$!
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=resume.pdf http://127.0.0.1:8787/
kill "$SERVER_PID"
```

## /projects/ deep-dive pages (labeled "Projects" in nav)

Each project-with-a-deep-dive has its own folder under `/projects/[slug]/` with sub-pages (how-it-works, tech, roadmap, changelog, dashboard). They share `/projects/projects.css`. Navigation within a project uses `.project-nav`; back to home uses `.crumbs`. The URL path is `/projects/` but all user-facing text reads "Projects" (nav links, breadcrumbs, headings).

**Dashboard prompt pages** (`/projects/[slug]/dashboard/`) showcase the AI-assisted engineering process — the prompt(s) that built the admin dashboard, displayed in terminal-style UI (`.terminal` component in `work.css`). Screenshots use a clickable lightbox (`<dialog>` element). When adding a new dashboard page, ensure the Dashboard tab is added to `.project-nav` in **all** sibling pages.

### Adding a new project deep-dive

1. Create `/projects/[slug]/` with sub-pages (e.g. `tech/index.html`, `roadmap/index.html`, `changelog/index.html`). Copy an existing project's page as the template — match the CSP meta tag, JSON-LD, breadcrumbs, `.cross-project-nav`, `.project-nav`, `.snapshot-banner`, `.work-hero`, footer, and script tag.
2. Set `aria-current="page"` on the active tab in `.project-nav` for each sub-page, and on the matching chip in `.cross-project-nav`.
3. Add the project to `/projects/index.html` (the work landing page).
4. Add a project card to the `#work` section grid in `index.html`.
5. Add all new URLs to `sitemap.xml`.
6. Add the Dashboard tab to `.project-nav` in **all** sibling sub-pages if adding a dashboard page.
7. **Cross-project nav update** (added 2026-04-28): add the new project as a chip in the `.cross-project-nav` block on **every existing deep-dive sub-page** (currently 12 across Aleph + Fantastic Leagues + Judge Tool). The chip's `href` should point at the new project's canonical entry-point sub-page (e.g., `/projects/{new-slug}/{tech-or-default}/`).
8. Update `tests/test_site_e2e.py::TestCrossProjectNav.EXPECTED_LINKS` to include the new slug, and bump the `len(self.DEEP_DIVES)` assertion to match the new total. The e2e suite enforces presence + canonical hrefs + aria-current; without the test update, CI will flag the mismatch immediately.

**Headshot rotation** — the About section cycles through 7 photos using JS-driven crossfade (5s interval, `script.js`). Images need `object-position` tuning per photo. Respects `prefers-reduced-motion` (freezes on first image). New photos need AVIF + WebP variants and a `.headshot-*` class for positioning.

## Data feeds on /now

The `/now` page is assembled from several independent sync scripts that each write into an HTML block delimited by `<!-- FEED-START -->` / `<!-- FEED-END -->` markers in `now/index.html` (e.g. `<!-- WHOOP-START -->`, `<!-- SPOTIFY-START -->`, etc.). **Don't remove the markers** — they are the replacement targets for the sync scripts.

**Top-of-page "Updated" eyebrow** — the `<!-- PAGE-UPDATED-START -->...<!-- PAGE-UPDATED-END -->` marker inside `.eyebrow` gets refreshed automatically every time *any* feed script calls `write_now_html()` in `_shared.py`. Single source of truth: whatever feed most recently synced sets the top-of-page timestamp. No separate sync script needed.

**Hitlist** (Places I want to eat at) — client-side fetch of `thirstypig.com/places-hitlist.json`. The JSON carries its own `lastUpdated` ISO field; the inline JS in `now/index.html` reads it and renders an `Auto-updated` line. Server-side sync not applicable (CORS locks the fetch to `https://jameschang.co`; won't render on localhost).

**Bucket list** — `bucketlist.json` lives at the repo root and is rendered client-side in two places: top 5 todos on `/now/` (rendered by `now/now.js`) and the full list at `/bucketlist/` (rendered by `bucketlist/bucketlist.js`). Order in `items[]` is the priority order. Edited via `thirstypig.com/admin/` (writes via the GitHub Contents API). No top-nav link — only path in is the "see the full list →" link from the /now teaser. Spec for the admin: `docs/bucketlist-admin-spec.md`.

**Project TLDRs + per-project shipping** (Active / Back-burner sections) — each project's content is wrapped in `<!-- TLDR-{slug}-START -->...<!-- TLDR-{slug}-END -->`. `bin/update-projects.py` runs daily at 7 AM PT (14:00 UTC) via `.github/workflows/projects-sync.yml` and splices a three-part block into each marker: (1) the TLDR paragraph from the repo's CLAUDE.md `<!-- now-tldr -->...<!-- /now-tldr -->` block, (2) a `<p class="nb-card-shipped">` listing the single most recent GitHub event (PushEvent / PullRequestEvent / ReleaseEvent) — capped by `EVENTS_PER_PROJECT=1`, (3) a `<p class="feed-updated">` with the sync timestamp. Config at `bin/projects-config.json` — `{slug, repo, file, shipping_repos[]}` per project; `shipping_repos` is the list of repos whose events attribute to this project (e.g., Aleph pulls from both `alephco.io-app` and `alephco.io-www`). **Required GitHub Secret:** `TLDR_FETCH_TOKEN` (fine-grained PAT with Contents:Read on every repo listed in `bin/projects-config.json`'s `shipping_repos` for any private project — currently Aleph, Judge Tool, TableDrop, Tastemakers x5). Fail-safe: on 404 / missing marker / events-API failure, existing HTML fallback is preserved — no empty blocks.

**Markdown contract for `<!-- now-tldr -->` blocks** (added 2026-04-28): the TLDR text is rendered through a tiny inline-only renderer (`_render_markdown_inline` in `bin/update-projects.py`). Supported tokens: **`**bold**`** → `<strong>`, **`` `code` ``** → `<code>`. HTML entities are escaped first, so author-written angle brackets like `<VenueChips>` render as text, not as a real tag. Anything else — `_italic_`, `[links](…)`, lists, headings — renders as literal markdown text on the page. Authors of downstream-repo CLAUDE.md TLDRs should keep prose plain; reach for `<strong>`/`<code>` directly if more emphasis is needed.

**Feed staleness monitor** — `bin/check-feed-health.py` runs every 6 hours via `.github/workflows/feeds-staleness-check.yml`. Opens a GitHub issue (labeled `feed-stale`) when a feed's `last_success_utc` is older than 48h, adds a comment if the issue is already open, and auto-closes when the feed recovers. Issue body includes feed-specific actionable guidance (e.g. "run `./bin/whoop-auth.sh`" for WHOOP). GitHub emails you on issue creation via repo subscription.

- **WHOOP** — daily via `.github/workflows/whoop-sync.yml`. Refresh token stored **encrypted in the repo** (`.whoop-token.enc`), decrypted at runtime with a GitHub Secret passphrase (`WHOOP_TOKEN_KEY`), re-encrypted + committed each run. This avoids needing a PAT for `secrets: write`. Full write-up in `docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md`. **Required GitHub Secrets:** `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, `WHOOP_TOKEN_KEY`.
- **Spotify** — every 30 minutes via `.github/workflows/spotify-sync.yml`. Refresh token stored in plain text as a GitHub Secret (`SPOTIFY_REFRESH_TOKEN`); the script writes `.spotify-state.json` to remember the last-seen podcast episode so the now-playing block doesn't flap when playback pauses. The 30-min cadence is tuned to maximize podcast capture rate — Spotify's `recently-played` endpoint is tracks-only in practice, so the only reliable way to catch a podcast is to poll `currently-playing` often enough to snapshot it mid-listen. Content-hash cache makes no-op runs free. **Required GitHub Secrets:** `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`.
- **Trakt** — **disabled 2026-04-28**. Workflow renamed to `.github/workflows/trakt-sync.yml.disabled` (preserved for re-enable; rename back to `.yml` to resume). Trakt was dropped from /now along with Letterboxd because the noise-to-signal ratio wasn't paying for itself. The `update-trakt.py` script and tests are kept in place. Token (`.trakt-token.enc`) and Secrets (`TRAKT_CLIENT_ID`, `TRAKT_CLIENT_SECRET`, `TRAKT_TOKEN_KEY`) are still in the repo / GitHub.
- **Plex** — every 6 hours via `.github/workflows/plex-sync.yml`. Static token (no rotation). Connects via Plex relay URL. **Required GitHub Secrets:** `PLEX_URL`, `PLEX_TOKEN`.
- **Public feeds** (MLB Stats API / Dodgers, Goodreads RSS currently-reading + read, The Fantastic Leagues / FBST standings) — every 6 hours via `.github/workflows/public-feeds-sync.yml`. All unauthenticated; no secrets needed. Handled by `bin/update-public-feeds.py`. GitHub events moved into `bin/update-projects.py` as per-project shipping lists. **Letterboxd was dropped 2026-04-28** along with Trakt — the `letterboxd_block()` function is preserved in the script in case it's revived, but the marker pair was removed from `now/index.html` and the entry in `feeds[]` was trimmed.

### Adding a new data feed

1. Add a new `<section class="work-section">` to `now/index.html` with `FEED-START` / `FEED-END` markers.
2. Add CSS for the feed's presentation in `projects/projects.css` (use existing CSS tokens). Follow the naming convention: `.{feed}-module`, `.{feed}-heading`, `.{feed}-list`, `.{feed}-when`, `.{feed}-updated`.
3. Write a Python function that fetches + returns the HTML block; add to `bin/update-public-feeds.py` (for unauth) or a new `bin/update-{feed}.py` (for OAuth). In `update-public-feeds.py`, add a tuple to the `feeds` list: `("MARKER_NAME", builder_function, 'fallback_html')`.
4. Add the fetch to the `main()` of the sync script; use `replace_marker()` to insert.
5. If OAuth: add a callback page at `/{service}/callback/`, auth script at `bin/{service}-auth.sh`, workflow at `.github/workflows/{service}-sync.yml`.
6. Call `record_heartbeat("feed_name")` from `_shared.py` in the sync script's `main()` — both on success and on early-return (no-change) paths. The 6-hour staleness check (`bin/check-feed-health.py` run by `.github/workflows/feeds-staleness-check.yml`) opens a GitHub issue (labeled `feed-stale`) if any feed's `last_success_utc` is >48h old, comments on existing open issues instead of duplicating, and auto-closes them when the feed recovers. Note: the 48h threshold may not suit feeds that update less frequently (e.g. weekly).
7. If the new feed fetches from an external domain client-side, add the domain to the CSP `connect-src` directive in `now/index.html`.
8. Sync scripts must be invoked as `python3 bin/update-{feed}.py` from the repo root (not imported as modules).

## Third-party fetches on /now/

The Places-I-want-to-try section fetches `https://thirstypig.com/places-hitlist.json` client-side. CORS is locked to `https://jameschang.co`, so the section won't render on `localhost` (expected). Graceful-fail pattern: on fetch error or empty list, the `<section id="wishlist-section">` is `.remove()`'d — no empty shell visible.

## Agent-native conventions

- **Never commit without the user's "go" / equivalent intent.** The user drives cadence.
- **Never touch `.whoop-token.enc` manually** unless running `bin/whoop-encrypt.sh`. The GitHub Action is the sole writer.
- **Never delete files in `docs/solutions/` or `todos/` during review** — those are institutional knowledge, protected artifacts.
- **When modifying HTML structure**, also audit the print stylesheet and any JSON-LD/meta tag that references specific claims (meta description, OG description).
- **When changing CSS tokens**, screenshot both light and dark mode headlessly (see `/tmp/jc-shots/` pattern).

## Local preview

```bash
python3 -m http.server 8787
# open http://localhost:8787/
```

For screenshotting with a forced theme, temporarily write `index.html` with `<html data-theme="light">` or `data-theme="dark">` baked in (OS preference otherwise leaks through to headless Chrome).

**Running feeds locally:** copy `bin/.env.example` to `.env` (or set the vars in your shell) and run `python3 bin/update-{whoop,spotify,plex,projects,public-feeds}.py`. For `bin/check-feed-health.py` use `DRY_RUN=1` so it doesn't open / close real GitHub issues.

## Analytics

**Google Analytics 4** is installed on all pages (measurement ID `G-B3HW5VBDB3`, added 2026-04-20). CSP headers include `googletagmanager.com` (script-src + **img-src**, the latter added 2026-04-28 after browser-testing surfaced silently-blocked GA4 measurement pixels), `google-analytics.com` (img-src), and `*.google-analytics.com *.analytics.google.com` (connect-src). The GA4 snippet is placed before `</head>` in every HTML file including callback pages.

## WCAG contrast compliance

The original WCAG AA audit (2026-04-16) was done against `styles.css`'s `--accent: #993524` and `--muted: #4a5568` — those tokens were retired with the 2026-04-27 notebook cut-over. Current notebook.css tokens (`--accent: #2f5d3a` forest-green light / `#d88a54` coral dark, `--dim: #6a6352` light / `#8a8a76` dark) ship with the design and inherit the audit framework. See `docs/solutions/accessibility/wcag-contrast-light-mode-accent-muted.md` for the original audit history and the contrast formula.

**When changing color tokens**, re-run the WCAG contrast check on both `--bg` and `--surface` composited surfaces. Both light and dark variants must clear AA (4.5:1).

## CSP notes

CSP is delivered via `<meta http-equiv="Content-Security-Policy">` in all HTML files. **Do not add `frame-ancestors`** — it's ignored in meta tags (only works via HTTP headers) and logs a console error. GitHub Pages does not support custom HTTP response headers, so `frame-ancestors` protection is not available on this host.

## Lighthouse baseline (2026-04-16)

Performance: 100 | Accessibility: 100 | Best Practices: 100 | SEO: 100. Total page weight: 78 KB. Zero layout shift, zero blocking time. Cache lifetime scores are capped by GitHub Pages' `max-age=600` — this is a platform constraint, not a code issue.

## Known outstanding items

All code-review findings from three reviews (initial, 2026-04-18 full-repo audit, 2026-04-29 whole-repo audit) have been resolved. See `todos/*` for the full history (120 files: 118 complete, 2 discarded, 0 pending). The 2026-04-29 sweep is captured in `todos/089-120` and the matching solution doc `docs/solutions/integration-issues/relative-time-html-defeats-content-changed-cache.md`.

## Testing

183 tests across 8 files. Run with `python3 -m pytest tests/ -v` (requires `pytest`).

| File | Type | Tests | What it covers |
|------|------|-------|---------------|
| `tests/test_shared.py` | Unit | 46 | `_shared.py`: escape_html, relative_time, **relative_time_html** (live-relative progressive enhancement), replace_marker, content_changed, sanitize_error, record_heartbeat (incl. corrupt JSON recovery), page-updated marker refresh |
| `tests/test_feeds.py` | Unit | 11 | `update-whoop.py`: recovery_color; `update-public-feeds.py`: ordinal |
| `tests/test_trakt.py` | Unit | 10 | `update-trakt.py`: build_html rendering, HTML escaping, deduplication by show, 5-show limit, regression assertions that legacy `trakt-*` classes are no longer emitted |
| `tests/test_feed_builders.py` | Unit | 14 | Feed builders for mlb, letterboxd, goodreads (reading + read), fbst, plex — mocked network, tested HTML output; plex fetch failure returns None vs []; regression assertions that legacy `plex-*` classes are no longer emitted |
| `tests/test_spotify.py` | Unit | 15 | `update-spotify.py`: build_html (asserts `nb-feed-podcast` + bare `<ul>`), state load/save, fetch_recent_tracks, fetch_current_podcast |
| `tests/test_whoop.py` | Unit | 14 | `update-whoop.py`: fetch_latest_recovery/sleep/cycle, build_html with all recovery colors |
| `tests/test_site_e2e.py` | E2E | 50 | All HTML pages: meta tags, CSP, aria-pressed, JSON-LD, images, internal links, feed markers (incl. PAGE-UPDATED), @media print + @page rule on notebook.css, OpenSSL parity, dark mode parity, GA4, privacy policy, symlink detection, sitemap consistency, OG image, **top-nav consistency** (brand text, no [about], [/now] slash prefix, experience→projects→now order across all 16 pages), **cross-project nav** (presence + canonical entry-point hrefs + aria-current on 12 deep-dive pages), **/now section structure** (sequential /01–/08 numbering + /07 watching/listening/reading sub-feeds, no Trakt/Letterboxd), **resume print pipeline** (print-name-block presence on homepage only + screen-hidden + canonical contact URLs; script.js beforeprint listener that opens `<details>` so the 8 additional certifications expand in resume.pdf; `.nb-card-name` print rule overrides screen sizing), **bucket list** (`bucketlist.json` schema + unique ids + status/completed-date invariants, /now render-target + hitlist title rename + link to /bucketlist/, public page loads + renderer script resolves + render targets present, no top-nav link to /bucketlist/) |
| `tests/test_projects.py` | Unit | 23 | `update-projects.py`: TLDR extraction, config schema, PR-event filtering, render_shipping_list (uses `nb-card-shipped` + bare `<time>`, drops legacy `shipping-recent`/`gh-when`), render_block |

CI runs on push to `main` via `.github/workflows/ci-tests.yml`. See `docs/test-plan.md` for the full testing strategy.

## Commit/push workflow

Direct push to `main` — this repo uses no PR gate (one contributor). GitHub Pages redeploys within ~1 minute. Pre-commit:

1. Screenshot the change if it's CSS/layout.
2. Regenerate `resume.pdf` if the homepage was edited.
3. Update this file if a new convention emerges.
