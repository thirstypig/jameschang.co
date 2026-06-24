# CLAUDE.md

<!-- now-tldr -->
The personal site at jameschang.co — homepage, project deep-dives, and a Derek Sivers-style /now page that auto-updates from eight cron-synced feeds (WHOOP, Spotify, Plex, MLB stats, fantasy standings, Google Calendar, and two Goodreads shelves — currently-reading + read) plus per-project TLDRs synced daily from each repo's CLAUDE.md. **Recently shipped**: a public bucket list, a feed staleness monitor that opens a GitHub issue when anything goes quiet, Google Calendar integration for upcoming events, and a cron-driven /now project hub that classifies each project as active or back-burner based on real GitHub activity. Plain HTML/CSS/JS on GitHub Pages — no build step, ~78 KB page weight, Lighthouse 100/100/100/100.
<!-- /now-tldr -->

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
/bin/                   Sync + auth scripts: _shared.py, update-{whoop,spotify,plex,trakt,public-feeds,projects,project-docs}.py, check-feed-health.py, {whoop,spotify,trakt}-{auth,encrypt}.sh, projects-config.json
/.github/workflows/     GitHub Actions (WHOOP, Spotify, Plex, public feeds, projects, project-docs, staleness check; trakt-sync.yml.disabled is dormant)
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

**Cron-script markup.** All /now feed-sync scripts (`update-whoop.py`, `update-spotify.py`, `update-plex.py`, `update-public-feeds.py`, `update-projects.py`) emit notebook-design markup directly — bare `<ul>` / `<li>` / `<span class="when">` styled by the parent `.nb-feed` cascade, plus helper class `.nb-feed-podcast` (Spotify lead-in). WHOOP emits `.nb-grid-4` + `.nb-stat` tiles. The only generic cron-only classes used by every feed are `.feed-empty` and `.feed-updated`. `update-projects.py` additionally emits `.nb-card-footer` (footer strip with surface-2 background, bleeds to card edges) and `.nb-card-shipped` (monospace shipping line inside the footer). Legacy per-feed classes (`.spotify-list`, `.trakt-when`, `.nb-feed-divider`, `.whoop-green`, etc.) were removed when Trakt disabled (2026-04-28) and final cleanup (2026-06-22).

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

See `docs/guides/adding-deep-dive.md` for the full checklist (8 steps covering structure, nav, markers, and tests). The process covers sub-pages, CSP + JSON-LD templates, cross-project nav updates, and test assertions.

**Headshot rotation** — the About section cycles through 7 photos using JS-driven crossfade (5s interval, `script.js`). Images need `object-position` tuning per photo. Respects `prefers-reduced-motion` (freezes on first image). New photos need AVIF + WebP variants and a `.headshot-*` class for positioning.

## Project doc sync (changelog + roadmap)

`bin/update-project-docs.py` runs daily at 6:15 AM PT (13:15 UTC) via `.github/workflows/project-docs-sync.yml`. Each (slug, doctype) sync is driven by a **per-project adapter** — a small callable `(token) → (parsed, error)` that knows how to fetch + parse one project's source-of-truth format. The rendered HTML is then spliced between `<!-- {CHANGELOG|ROADMAP}-START -->` / `<!-- ...END -->` markers on the destination page.

The adapter pattern lets us sync from heterogeneous sources (plain markdown, custom-shape markdown, TypeScript data structures) without forcing every source repo to author a single shared convention. Adapters today:

| Adapter | Source | Doctype | Notes |
|---|---|---|---|
| `parse_changelog` | `docs/changelog.md` | changelog | heading-line convention (see spec below); used by all 3 changelog entries |
| `parse_aleph_roadmap` | `docs/plans/roadmap.md` | roadmap | `### Module` H3s, `**Workflow:**` + `**Features:**` bold markers, percent from `## Project Health` table |
| `parse_jt_roadmap` | `docs/PRODUCTION_ROADMAP.md` | roadmap | `## PHASE N: Name` H2s, task-list body, no per-phase percent (renderer omits the badge) |
| `parse_fl_roadmap` | `client/src/pages/Roadmap.tsx` | roadmap | extracts `productRoadmap` TypeScript data array via brace-counted slicing; phases → modules, items → features |

**Currently wired (6 (slug, doctype) entries)** — see `PROJECT_DOCS` in the script:

| Slug | Doctype | Source | Destination |
|------|---------|--------|-------------|
| `aleph` | changelog | `thirstypig/alephco.io-app:docs/changelog.md` | `/projects/aleph/changelog/` |
| `aleph` | roadmap | `thirstypig/alephco.io-app:docs/plans/roadmap.md` | `/projects/aleph/roadmap/` |
| `fantastic-leagues` | changelog | `thirstypig/TheFantasticLeagues:docs/changelog.md` | `/projects/fantastic-leagues/changelog/` |
| `fantastic-leagues` | roadmap | `thirstypig/TheFantasticLeagues:client/src/pages/Roadmap.tsx` | `/projects/fantastic-leagues/roadmap/` |
| `judge-tool` | changelog | `thirstypig/thejudgetool:docs/changelog.md` | `/projects/judge-tool/changelog/` |
| `judge-tool` | roadmap | `thirstypig/thejudgetool:docs/PRODUCTION_ROADMAP.md` | `/projects/judge-tool/roadmap/` |

**Changelogs are deferred** — no source `docs/changelog.md` exists in any of the 3 repos today; sync gracefully skips. The in-app changelog is currently the source of truth. Author a `docs/changelog.md` in a source repo (using the heading-line convention below) to opt that project's changelog into sync.

**JT roadmap markers replaced the Done/Planned buckets** — `/projects/judge-tool/roadmap/` previously had hand-curated "Done" and "Planned" `.module` blocks under a "Short-term roadmap" section. Those were replaced with a "Production readiness" section containing markers that the sync overwrites with the live phases from `docs/PRODUCTION_ROADMAP.md`. The Health scorecard, Medium & long term, Risk register, and Findings history sections on the same page stay hand-curated.

**FL roadmap was promoted from external link to internal sub-page** — early scope had an external `Roadmap ↗` link in `.project-nav` pointing at `app.thefantasticleagues.com/roadmap`. After the FL adapter was built, that link became an internal `/projects/fantastic-leagues/roadmap/` link. The external URL still appears INSIDE the FL roadmap page as "View live ↗" — not in nav. Test guard: `tests/test_site_e2e.py::TestFLRoadmapInternalNav::test_external_app_url_not_in_fl_navs` catches any nav regression to the old external href.

**Markers.** Each destination page must contain a `<!-- CHANGELOG-START -->` / `<!-- CHANGELOG-END -->` pair (or `ROADMAP-START`/`-END` for roadmaps). The sync ONLY rewrites content between markers — surrounding `.stats-grid`, `.work-hero`, "Recent releases" headings, etc. stay hand-edited. Same bootstrap rule as `/now`: a missing marker pair makes the cron silently skip that page forever. `tests/test_site_e2e.py::TestProjectDocSyncMarkers` is the CI guard.

**Fail-safe behavior** — per-doc, never crashes the whole script:
- Source file missing → skip + log; no heartbeat written if the feed has never succeeded (prevents day-1 false-positive issues from the staleness monitor). Once a feed has succeeded once, future source-missing errors record `last_error` while preserving `last_success_utc`.
- Markdown parses to zero entries → skip (treated like missing source).
- Markers missing in destination → error + heartbeat (if known).
- Network/PAT failures → handled by `urllib` exception catch in `fetch_file()`; returns None.

**Heartbeat slugs.** `project-docs` aggregate, plus `project-docs:{slug}-{doctype}` per doc (e.g. `project-docs:aleph-changelog`). The staleness monitor's `GUIDANCE` has a `project-docs` entry; per-doc slugs fall through via `_fallback_guidance()` prefix match.

### Adding a project to the sync

See `docs/guides/adding-new-project.md` for the full guide (5 steps + markdown conventions for both changelog and roadmap formats). The conventions are strict but machine-parseable — heading-line metadata, task-list states, and per-project adapter patterns documented with examples.

## Data feeds on /now

The `/now` page is assembled from several independent sync scripts that each write into an HTML block delimited by `<!-- FEED-START -->` / `<!-- FEED-END -->` markers in `now/index.html` (e.g. `<!-- WHOOP-START -->`, `<!-- SPOTIFY-START -->`, etc.). **Don't remove the markers** — they are the replacement targets for the sync scripts.

**What counts as a "feed" (the canonical 8).** A *feed* is a cron-synced block with a staleness heartbeat in `.feeds-heartbeat.json`. There are exactly **8**: `whoop`, `spotify`, `plex`, `gcal`, `mlb`, `fbst`, `goodreads-reading`, `goodreads`. The `projects` / `project-docs*` heartbeats are the per-project TLDR/doc syncs, not data feeds. The **hitlist, bucket list, and quotes** are **client-rendered sections** (runtime JSON fetch, no cron, no heartbeat) — count them as sections, not feeds. Use "8 cron-synced feeds" consistently in README + this file.

**Marker boundaries.** `replace_marker()` only writes between `<!-- {FEED}-START -->` and `<!-- {FEED}-END -->`. Date strings, status indicators, or eyebrow lines OUTSIDE markers are never updated by the sync — they freeze on their last hand-edit. Same trap applies to `bin/check-feed-health.py`'s heartbeat-iteration: a retired feed slug's GitHub issue won't auto-close because the slug isn't in the heartbeat dict. See `docs/solutions/integration-issues/marker-boundary-content-staleness.md`.

**Top-of-page "Updated" eyebrow** — the `<!-- PAGE-UPDATED-START -->...<!-- PAGE-UPDATED-END -->` marker inside `.eyebrow` gets refreshed automatically every time *any* feed script calls `write_now_html()` in `_shared.py`. Single source of truth: whatever feed most recently synced sets the top-of-page timestamp. No separate sync script needed.

**Hitlist** (Places I want to eat at) — client-side fetch of `thirstypig.com/places-hitlist.json`. The JSON carries its own `lastUpdated` ISO field; the inline JS in `now/index.html` reads it and renders an `Auto-updated` line. Server-side sync not applicable (CORS locks the fetch to `https://jameschang.co`; won't render on localhost).

**Bucket list** — `bucketlist.json` lives at the repo root and is rendered client-side in two places: top 5 todos on `/now/` (rendered by `now/now.js`) and the full list at `/bucketlist/` (rendered by `bucketlist/bucketlist.js`). Order in `items[]` is the priority order. Edited via `thirstypig.com/admin/` (writes via the GitHub Contents API). No top-nav link — only path in is the "see the full list →" link from the /now teaser. Spec for the admin: `docs/bucketlist-admin-spec.md`.

**Quotes** (`/12` section) — `quotes.json` at the repo root, rendered client-side by `now/now.js` into `<section id="quotes-section">` as a grid of equal-size cards (`.nb-quote-card`). Clicking a card opens the shared native `<dialog id="quote-modal">` (`.nb-quote-modal`, seeded in `now/index.html`) populated via `textContent` (XSS-safe) with the full quote, original + translation for bilingual entries, source, and a provenance `note`. Same silent-fail pattern as bucket list/hitlist (`.remove()`s its section on fetch error/empty). The IIFE hardcodes the section number `/12` (client-rendered sections continue past the static `/01`–`/09`: hitlist `/10`, bucketlist `/11`, quotes `/12`). Item schema: `{id, text, source}` required + optional `original, lang (zh/la/fr), translation, note, category (idiom/film/literature/proverb/latin/philosophy/poem)`. **Collections + poems** — an item may carry `title` (card headline + modal heading) + `entries[]` (array of strings): one card that expands into a module listing many quotes (e.g. a "Bruce Lee" box of 18 reflections, an "Ed Catmull" box). `category:"poem"` (e.g. Kipling's "If—") renders `entries[]` as line-break-preserving stanzas (`white-space: pre-line`) instead of a numbered list; for a poem each `entries[]` string is a stanza with `\n` line breaks. `text` is the card teaser for titled items. CSS in `notebook.css` (`.nb-quote-grid`/`-card`/`-card--collection`/`-modal`/`-list`/`-poem`). All quotes are **external** with verified attributions; every quote carries a `source` (use `"Source unknown"` rather than omitting), and collection boxes exclude misattributed lines (noted in the item's `note`). Tests: `tests/test_site_e2e.py::TestQuotes`. Design spec: `docs/superpowers/specs/2026-06-02-now-quotes-section-design.md`. Reusable pattern + gotchas (section numbering, bootstrap, XSS, silent-fail): `docs/solutions/integration-issues/client-rendered-json-section-on-now.md`.

**Detail cards + shared popup** (`/09 people i follow` + `/06 off the clock` top list) — these are **server-rendered** (hand-curated, not feeds), each item a `.nb-detail-card` containing a `.nb-detail-trigger` `<button>` (name + role tag), a visible `.nb-detail-links` row, and a `<template>` holding the full detail (name + body + links). A single shared `<dialog id="detail-modal">` (reuses `.nb-quote-modal` styling) is populated by a `now/now.js` IIFE that **clones** the clicked card's template into the modal body (`tpl.content.cloneNode(true)` → `replaceChildren`) — preserves `<em>`/links, XSS-safe, no `innerHTML`. CSP forbids inline `onclick`, so the wiring must live in `now.js`. To add a card: drop a `.nb-detail-card` (trigger + links + `<template>`) into the grid — no JS change needed (the IIFE binds all `.nb-detail-trigger`s). CSS: `.nb-detail-grid`/`-card`/`-trigger`/`-name`/`-tag`/`-links` + `.nb-detail-modal-name`/`-body`/`-links`. Tests: `tests/test_site_e2e.py::TestDetailCards`.

**Activity-first project cards + active/back-burner classification** (`/01` + `/02` sections) — `bin/update-projects.py` runs daily at 6 AM PT (13:00 UTC) via `.github/workflows/projects-sync.yml` and rewrites BOTH the per-section eyebrow text and the project cards. Markers are `<!-- ACTIVE-EYEBROW-START -->` / `-END`, `<!-- ACTIVE-PROJECTS-START -->` / `-END`, and the matching `BACKBURNER-*` pair. Each card has nested `<!-- TLDR-{slug}-START -->...<!-- TLDR-{slug}-END -->` for the body content. **Classification rule:** a project is "active" if its most recent GitHub event across all `shipping_repos[]` is within `ACTIVE_THRESHOLD_DAYS = 7` (strict less-than; an event exactly 7 days old falls to back-burner). Projects with no events go to back-burner.

**Card format** (`.nb-proj-card`, added 2026-06-04): activity-first layout — the most recent shipped commit appears BEFORE the description so returning visitors see the delta without scanning prose. Each card has: (1) project name + domain, (2) status badge (`<span class="nb-proj-badge nb-proj-badge--{status}">`) with an inline Tabler SVG icon + "Status · Maturity" label (e.g. "Shipping · Beta", "Live · Private", "Blocked · Alpha"), (3) `.nb-proj-activity` inset with the most recent GitHub event link + live-relative timestamp (or `.nb-proj-activity--empty` if no recent events), (4) one-sentence description, (5) "next up" line. Badge CSS tokens: `--color-border-info` (blue/shipping), `--color-border-success` (green/live), `--color-border-warning` (amber/blocked) — all defined in `notebook.css` with light/dark variants. Active section uses `.nb-grid-1` (full-width); back-burner uses `.nb-grid-3` (3-column responsive). Grid containers carry `id="proj-active"` and `id="proj-backburner"` for the opt-in JS layer.

**Config** at `bin/projects-config.json` — `{slug, repo, name, url, url_label, status_badge, maturity, desc, next_up, shipping_repos[]}` per project. `status_badge` is a plain word (`shipping` / `live` / `blocked` / `shipped`). `maturity` is `alpha` / `beta` / `public` / `private`. `desc` and `next_up` are editorial prose written in config — **the script no longer fetches CLAUDE.md from source repos** for the /now cards (that fetch was removed 2026-06-04; `extract_tldr()` and `_render_markdown_inline()` remain in the file as dead code for test backward-compatibility). **9 projects** currently configured: aleph, fantastic-leagues, bahtzang-trader, judge-tool, tabledrop, tastemakers, thirsty-pig, ktv-singer, jameschang-co (self-classifying). **Required GitHub Secret:** `TLDR_FETCH_TOKEN` (fine-grained PAT with read access to every private `shipping_repos[]` entry — needed for per-repo events, not CLAUDE.md). **Events are fetched per-repo** via `/repos/{repo}/events`; a single repo's failure is isolated (`[]`), never fatal. Fail-safe: missing markers → heartbeat error + bail without modifying the page.

**JS data layer** — `now/project-cards.js` is a standalone opt-in file: exposes `window.__renderProjectCards()` which renders all cards from an embedded data array (no cron dependency). Auto-render is disabled by default (the `DOMContentLoaded` line is commented out) to avoid overwriting the cron's live shipped timestamps. Activate by uncommenting that line or adding `<script src="/now/project-cards.js" defer></script>` to now/index.html.

**Feed staleness monitor** — `bin/check-feed-health.py` runs every 6 hours via `.github/workflows/feeds-staleness-check.yml`. Opens a GitHub issue (labeled `feed-stale`) when a feed's `last_success_utc` is older than 48h, adds a comment if the issue is already open, and auto-closes when the feed recovers. Issue body includes feed-specific actionable guidance (e.g. "run `./bin/whoop-auth.sh`" for WHOOP). GitHub emails you on issue creation via repo subscription. **Transient GitHub API errors** (5xx, gateway timeout from `gh issue list`) are caught and result in `sys.exit(0)` — the next scheduled run catches any genuinely stale feeds. Non-transient errors (e.g. 401 auth failure) still propagate and fail the workflow.

- **WHOOP** — daily via `.github/workflows/whoop-sync.yml`. Refresh token stored **encrypted in the repo** (`.whoop-token.enc`), decrypted at runtime with a GitHub Secret passphrase (`WHOOP_TOKEN_KEY`), re-encrypted + committed each run. This avoids needing a PAT for `secrets: write`. Full write-up in `docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md`. **Required GitHub Secrets:** `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, `WHOOP_TOKEN_KEY`.
- **Spotify** — every 30 minutes via `.github/workflows/spotify-sync.yml`. Refresh token stored in plain text as a GitHub Secret (`SPOTIFY_REFRESH_TOKEN`); the script writes `.spotify-state.json` to remember the last-seen podcast episode so the now-playing block doesn't flap when playback pauses. The 30-min cadence is tuned to maximize podcast capture rate — Spotify's `recently-played` endpoint is tracks-only in practice, so the only reliable way to catch a podcast is to poll `currently-playing` often enough to snapshot it mid-listen. Content-hash cache makes no-op runs free. **Required GitHub Secrets:** `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`.
- **Trakt** — **disabled 2026-04-28**. Workflow renamed to `.github/workflows/trakt-sync.yml.disabled` (preserved for re-enable; rename back to `.yml` to resume). Trakt was dropped from /now along with Letterboxd because the noise-to-signal ratio wasn't paying for itself. The `update-trakt.py` script and tests are kept in place. Token (`.trakt-token.enc`) and Secrets (`TRAKT_CLIENT_ID`, `TRAKT_CLIENT_SECRET`, `TRAKT_TOKEN_KEY`) are still in the repo / GitHub.
- **Plex** — every 6 hours via `.github/workflows/plex-sync.yml`. Static token (no rotation). Connects via Plex relay URL. **Required GitHub Secrets:** `PLEX_URL`, `PLEX_TOKEN`.
- **Google Calendar** — hourly at `:00 UTC` via `.github/workflows/gcal-sync.yml`. Fetches a public iCal feed (the calendar's "Get a secret address in iCal format" URL — secret-by-obscurity), parses VEVENTs with a hand-rolled stdlib parser (no `icalendar` pip dep), filters to events from today forward, sorts ascending by full PT datetime (so a 3 PM event renders before a 5 PM event on the same day; all-day events sort as midnight), groups consecutive events sharing the same first 3 word-tokens (regex `\w+`, case-insensitive) into one card with a spanning date range — so MINI Takes The States' 5 separate calendar entries collapse to one "oct 2–4" card titled "Mini Takes The States" — and caps at `MAX_UPCOMING = 20` post-grouping. Renders into two markers: `<!-- GCAL-EYEBROW-START -->` / `-END` (the section subtitle "via google calendar · auto-updated … · N upcoming") and `<!-- GCAL-START -->` / `-END` (the cards themselves). Each card carries `data-cal-end="YYYY-MM-DD"` so `now/now.js` auto-prunes past events client-side as a backstop. The fetch never logs the URL on error — just the exception class. **Required GitHub Secret:** `GCAL_ICAL_URL`.
- **Public feeds** (MLB Stats API / Dodgers, Goodreads RSS currently-reading + read, The Fantastic Leagues / FBST standings) — every 6 hours via `.github/workflows/public-feeds-sync.yml`. All unauthenticated; no secrets needed. Handled by `bin/update-public-feeds.py`. GitHub events moved into `bin/update-projects.py` as per-project shipping lists. **Letterboxd was dropped 2026-04-28** along with Trakt — the `letterboxd_block()` function is preserved in the script in case it's revived, but the marker pair was removed from `now/index.html` and the entry in `feeds[]` was trimmed.

### Adding a new data feed

See `docs/guides/adding-new-feed.md` for the full checklist (8 steps covering markers, CSS, Python fetchers, OAuth setup, heartbeats, and CSP). Also documents the current 8 canonical feeds and their configurations (secrets, cadence, token storage patterns).

## Third-party fetches on /now/

The Places-I-want-to-try section fetches `https://thirstypig.com/places-hitlist.json` client-side. CORS is locked to `https://jameschang.co`, so the section won't render on `localhost` (expected). Graceful-fail pattern: on fetch error or empty list, the `<section id="wishlist-section">` is `.remove()`'d — no empty shell visible.

## Agent-native conventions

- **Never commit without the user's "go" / equivalent intent.** The user drives cadence.
- **Never touch `.whoop-token.enc` manually** unless running `bin/whoop-encrypt.sh`. The GitHub Action is the sole writer.
- **Never delete files in `docs/solutions/` or `todos/` during review** — those are institutional knowledge, protected artifacts.
- **When modifying HTML structure**, also audit the print stylesheet and any JSON-LD/meta tag that references specific claims (meta description, OG description).
- **When changing CSS tokens**, screenshot both light and dark mode headlessly (see `/tmp/jc-shots/` pattern).

### File storage conventions

- **Screenshots for docs:** → `docs/screenshots/{purpose}/` with a README explaining what they document
- **Working/draft docs:** → `docs/archive/` or ephemeral (never root level)
- **Testing artifacts:** → `.gitignore` (auto-regenerated on test runs)
- **PDFs:** Only commit current versions (e.g., `resume.pdf`). Delete dated versions (e.g., `James_Chang_resume_April2026.pdf`).
- **Root directory:** Code, config, and live assets only. No drafts, no screenshots, no stale versions.

### Folder hygiene & maintenance

**Pre-commit safeguards:**
- `.git/hooks/pre-commit` blocks accidental commits of junk files (see blocklist in hook)
- `.gitignore` covers all build artifacts, OS junk, and working documents
- Both are version-controlled; distribute to teammates via git clone

**Quarterly audit** (run every ~3 months to prevent drift):
```bash
# 1. Check file count trend
git ls-files | wc -l

# 2. Check root clutter
find . -maxdepth 1 -type f | wc -l

# 3. Scan for dated files (potential stale versions)
find . -maxdepth 1 -type f | grep -E '[0-9]{4}-[0-9]{2}'

# 4. Verify repo size hasn't exploded
du -sh .
```

**Red flags** (cleanup triggers):
- Root files > 40 (target: ~35)
- Total repo size > 100 MB
- PNG/PDF files modified today but not referenced in code
- Anything with a date in the filename (often superseded versions)

### Cross-repo PAT trade-off

**Cross-repo PAT trade-off.** The bucket list admin lives on `thirstypig.com/admin/` but writes to this repo via the GitHub Contents API. The PAT is shared across `thirstypig-blog` and `jameschang.co` (see commit `d64bdb85` on thirstypig) so one paste covers both managers. Trade-off: an XSS or supply-chain compromise in the Tina admin context now mutates BOTH repos. Mitigations: (a) PAT scope must be `Contents: Read+Write` only, never `repo`; (b) rotate every 90 days max (calendar reminder); (c) sessionStorage clears on tab close; (d) admin-side CSP and Google Maps SDK pinning are tracked in todos/129 and todos/136. The decision to share keys was a deliberate UX call — splitting back is the alternative if the trade-off ever stops feeling worth it.

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

All code-review findings from four reviews (initial, 2026-04-18 full-repo audit, 2026-04-29 whole-repo audit, 2026-05-05 cross-repo-admin sweep) have been resolved or deferred with a documented work log. See `todos/*` for the full history — **146 files: 143 complete, 2 discarded, 1 pending**. The single pending item is `todos/146` (P3 — snapshot-banner asymmetry: removed from `projects/judge-tool/tech/` because the live `/tech` URL was broken, but still present on the JT `roadmap/` and `changelog/` sub-pages). The former long-pending item (`todos/129`) — admin-side CSP for the Tina shell on thirstypig.com — was resolved via Vercel HTTP headers in `vercel.json` (CSP + X-Frame-Options on `/admin/*`), which survives `tinacms build` unlike a meta tag approach. The 2026-04-29 sweep is captured in `todos/089-120`; the 2026-05-05 sweep in `todos/121-136`. Matching solution docs: `docs/solutions/integration-issues/relative-time-html-defeats-content-changed-cache.md`, `docs/solutions/integration-issues/cross-repo-admin-via-github-contents-api.md`, `docs/solutions/integration-issues/marker-boundary-content-staleness.md`, `docs/solutions/integration-issues/per-project-adapters-for-heterogeneous-roadmap-sources.md`.

## Testing

**347 tests** across 11 files: 277 unit tests (9 files) + 70 E2E tests. Run locally with `python3 -m pytest tests/ -v` (requires `pytest`).

See `docs/test-plan.md` for the full testing strategy, inventory by file, and CI cadence. Unit tests cover individual feed sync scripts + the shared `_shared.py` utilities. E2E tests cover all pages: meta tags, CSP, feed markers, print stylesheet, sitemap, top-nav consistency, cross-project nav, detail cards, quotes section, and more.

CI runs on every push to `main` via `.github/workflows/ci-tests.yml`.

## Commit/push workflow

Direct push to `main` — this repo uses no PR gate (one contributor). GitHub Pages redeploys within ~1 minute. Pre-commit:

1. Screenshot the change if it's CSS/layout.
2. Regenerate `resume.pdf` if the homepage was edited.
3. Update this file if a new convention emerges.

## Behavioral rules for Claude (universal)

### How to answer

1. **No flattery.** Skip "great question," "you're absolutely right," "fascinating perspective" and every variant. Start with substance.
2. **Lead with the strongest counterargument before agreeing.** If I state a position, steelman the opposing view first — even if you ultimately agree.
3. **Don't capitulate under pushback.** If I push back without new evidence or better reasoning, restate your position. Caving when you were right is worse than disagreeing.
4. **State confidence on non-trivial claims: HIGH / MODERATE / LOW / UNKNOWN.** Distinguish three sources:
   - "I know this" (training data, verifiable)
   - "I'm reasoning from principles" (inference)
   - "I'm guessing" (low signal)
5. **Say "I don't know" when you don't.** Never invent citations, dates, numbers, API behaviors, library versions, regulations, or competitor facts. If unsure, flag it and tell me how to verify.
6. **Generate your own estimates before reacting to mine.** Don't anchor.
7. **Never apologize for disagreeing.** Accuracy > my approval.
8. **If my question contains a faulty premise, fix the premise first.** Don't answer a bad question well.
9. **Surface my implicit assumptions.** Call out sunk-cost reasoning when I'm defending past decisions vs. assessing fresh.
10. **Articulate tradeoffs, not preferences.** Show the chain: X because Y, given Z. "A beats B for [reason], but B wins if [condition]."
11. **Default to the simpler/cheaper/less-built option when it suffices.**
12. **Recency flag.** For anything that changes — regulations, prices, APIs, vendor specs, current events — flag it and tell me what to verify with a live source.
13. **No moral/ethical disclaimers unless asked.** Detailed is fine; padded is not.

### Memory loop

When you notice a pattern, preference, decision, or piece of context that should persist beyond this conversation, say so explicitly and offer to draft a context-doc update. Treat yourself as a co-maintainer of this project's memory, not a passive consumer of it. Flag inconsistencies between what I'm saying now and what's in project knowledge.
