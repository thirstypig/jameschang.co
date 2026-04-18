# CLAUDE.md

Operational notes for Claude Code (and any other agent) working on this repo. For human-facing workflow see `README.md`; for design/positioning history see `PLAN.md`; for past solved problems see `docs/solutions/`.

## Stack

- **Plain static HTML/CSS/JS.** No build step. No framework. No `package.json`.
- **Hosting:** GitHub Pages on custom apex domain `jameschang.co` via A/AAAA records + `CNAME`.
- **Python 3 is the only tooling dependency** (local server + WHOOP sync script + résumé PDF generation).

## Repo layout

```
/                       Homepage (index.html + styles.css + script.js)
/now/                   Derek Sivers-style /now page (reads work/work.css)
/work/                  Deep-dive project pages (Aleph, Fantastic Leagues, Judge Tool) — each has sub-pages + dashboard prompt showcase
/privacy/               Privacy policy (required by WHOOP app registration)
/whoop/callback/        OAuth2 redirect target (static page that reads ?code= from URL)
/assets/                Images (AVIF/WebP/PNG responsive triples), favicons, OG image
/bin/                   Maintenance scripts (whoop-auth.sh, whoop-encrypt.sh, update-whoop.py, update-spotify.py, update-public-feeds.py, spotify-auth.sh)
/.github/workflows/     GitHub Actions (WHOOP, Spotify, public feeds sync + staleness check)
/docs/solutions/        Internal knowledge base — past solved problems (see /ce:compound)
/todos/                 Code-review findings (see /ce:review)
/resume.pdf             Generated from the homepage print stylesheet
.whoop-token.enc        AES-encrypted WHOOP refresh token (committed, decrypted at runtime)
.feeds-heartbeat.json   Timestamped heartbeats per feed (committed by sync workflows)
```

## CSS token system

All color/type/spacing in `styles.css` uses CSS variables. **Never hardcode colors.** Tokens:

| Token | Purpose |
|-------|---------|
| `--bg`, `--bg-from`, `--bg-to` | Page background + gradient endpoints (light/dark) |
| `--text`, `--muted` | Primary and secondary text |
| `--accent`, `--accent-hover` | Oxide-red (light) / warm coral (dark) |
| `--rule`, `--card-bg`, `--card-border`, `--card-shadow` | Surface + dividers |
| `--glass-blur` | `backdrop-filter` value for glass cards |
| `--serif`, `--sans`, `--mono` | Font stacks (pure system, no `@font-face`) |
| `--measure`, `--measure-wide` | Reading widths (640px / 960px) |

Dark mode is triggered via `@media (prefers-color-scheme: dark)` + an explicit `[data-theme="dark"]` override driven by `script.js` theme toggle (persisted in `localStorage`).

## Print stylesheet

`styles.css` has a substantial `@media print` block that reorders + restyles the homepage into a résumé PDF. **When adding a new section**, also add an `order` value in the print flex layout, or add `display: none` if the section shouldn't print. Testimonials and `.booking-cta`-style call-to-actions are hidden in print.

Regenerate the PDF with:
```bash
python3 -m http.server 8787 &
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=resume.pdf http://127.0.0.1:8787/
```

## /work/ deep-dive pages

Each project-with-a-deep-dive has its own folder under `/work/[slug]/` with sub-pages (how-it-works, tech, roadmap, changelog, dashboard). They share `/work/work.css`. Navigation within a project uses `.project-nav`; back to home uses `.crumbs`.

**Dashboard prompt pages** (`/work/[slug]/dashboard/`) showcase the AI-assisted engineering process — the prompt(s) that built the admin dashboard, displayed in terminal-style UI (`.terminal` component in `work.css`). Screenshots use a clickable lightbox (`<dialog>` element). When adding a new dashboard page, ensure the Dashboard tab is added to `.project-nav` in **all** sibling pages.

**Headshot rotation** — the About section cycles through 7 photos using JS-driven crossfade (5s interval, `script.js`). Images need `object-position` tuning per photo. Respects `prefers-reduced-motion` (freezes on first image). New photos need AVIF + WebP variants and a `.headshot-*` class for positioning.

## Data feeds on /now

The `/now` page is assembled from several independent sync scripts that each write into an HTML block delimited by `<!-- FEED-START -->` / `<!-- FEED-END -->` markers in `now/index.html` (e.g. `<!-- WHOOP-START -->`, `<!-- SPOTIFY-START -->`, etc.). **Don't remove the markers** — they are the replacement targets for the sync scripts.

- **WHOOP** — daily via `.github/workflows/whoop-sync.yml`. Refresh token stored **encrypted in the repo** (`.whoop-token.enc`), decrypted at runtime with a GitHub Secret passphrase (`WHOOP_TOKEN_KEY`), re-encrypted + committed each run. This avoids needing a PAT for `secrets: write`. Full write-up in `docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md`. **Required GitHub Secrets:** `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, `WHOOP_TOKEN_KEY`.
- **Spotify** — every 4 hours via `.github/workflows/spotify-sync.yml`. Refresh token stored in plain text as a GitHub Secret (`SPOTIFY_REFRESH_TOKEN`); the script writes `.spotify-state.json` to remember the last-seen podcast episode so the now-playing block doesn't flap when playback pauses. **Required GitHub Secrets:** `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`.
- **Public feeds** (GitHub events, MLB Stats API / Dodgers, Letterboxd RSS, Goodreads RSS, The Fantastic Leagues / FBST standings) — every 6 hours via `.github/workflows/public-feeds-sync.yml`. All five are unauthenticated; no secrets needed. Handled by `bin/update-public-feeds.py`.

### Adding a new data feed

1. Add a new `<section class="work-section">` to `now/index.html` with `FEED-START` / `FEED-END` markers.
2. Add CSS for the feed's presentation in `work/work.css` (use existing CSS tokens).
3. Write a Python function that fetches + returns the HTML block; add to `bin/update-public-feeds.py` (for unauth) or a new `bin/update-{feed}.py` (for OAuth).
4. Add the fetch to the `main()` of the sync script; use `replace_marker()` to insert.
5. If OAuth: add a callback page at `/{service}/callback/`, auth script at `bin/{service}-auth.sh`, workflow at `.github/workflows/{service}-sync.yml`.
6. Call `record_heartbeat("feed_name")` from `_shared.py` in the sync script's `main()` — both on success and on early-return (no-change) paths. The weekly staleness check (`.github/workflows/feeds-staleness-check.yml`) opens a GitHub issue if any feed goes >48h without a successful heartbeat.

## Third-party fetches on /now/

The Places-I-want-to-try section fetches `https://thirstypig.com/places-hitlist.json` client-side. CORS is locked to `https://jameschang.co`, so the section won't render on `localhost` (expected). Graceful-fail pattern: on fetch error or empty list, the `<section id="wishlist-section">` is `.remove()`'d — no empty shell visible.

## Agent-native conventions

- **Never commit without the user's "go" / equivalent intent.** The user drives cadence.
- **Never touch `.whoop-token.enc` manually** unless running `bin/whoop-encrypt.sh`. The GitHub Action is the sole writer.
- **Never delete files in `docs/plans/`, `docs/solutions/`, or `todos/` during review** — those are institutional knowledge, protected artifacts.
- **When modifying HTML structure**, also audit the print stylesheet and any JSON-LD/meta tag that references specific claims (meta description, OG description).
- **When changing CSS tokens**, screenshot both light and dark mode headlessly (see `/tmp/jc-shots/` pattern).

## Local preview

```bash
python3 -m http.server 8787
# open http://localhost:8787/
```

For screenshotting with a forced theme, temporarily write `index.html` with `<html data-theme="light">` or `data-theme="dark">` baked in (OS preference otherwise leaks through to headless Chrome).

## Analytics

**No analytics are installed.** The GA4 placeholder (`G-XXXXXXXXXX`) was removed on 2026-04-16. CSP headers across all HTML files were tightened to remove Google domains. If adding real analytics later, re-add the GA4 snippet and update CSP `script-src`, `img-src`, and `connect-src` in all HTML files.

## WCAG contrast compliance

All light-mode color tokens were audited and adjusted on 2026-04-16 to meet **WCAG AA (4.5:1)**:
- `--accent`: `#993524` (4.6:1 on `--bg`, 6.0:1 on `--card-bg`)
- `--muted`: `#4a5568` (4.8:1 on `--bg`, 6.2:1 on `--card-bg`)
- Dark mode tokens already passed (7.6:1 accent, 5.8:1 muted)

**When changing color tokens**, re-run the WCAG contrast check — both on `--bg` and on composited `--card-bg`. The formula is in the project memory.

## CSP notes

CSP is delivered via `<meta http-equiv="Content-Security-Policy">` in all HTML files. **Do not add `frame-ancestors`** — it's ignored in meta tags (only works via HTTP headers) and logs a console error. GitHub Pages does not support custom HTTP response headers, so `frame-ancestors` protection is not available on this host.

## Lighthouse baseline (2026-04-16)

Performance: 100 | Accessibility: 100 | Best Practices: 100 | SEO: 100. Total page weight: 78 KB. Zero layout shift, zero blocking time. Cache lifetime scores are capped by GitHub Pages' `max-age=600` — this is a platform constraint, not a code issue.

## Known outstanding items

All code-review findings from the initial review have been resolved. See `todos/*` for the full history (status: done).

## Commit/push workflow

Direct push to `main` — this repo uses no PR gate (one contributor). GitHub Pages redeploys within ~1 minute. Pre-commit:

1. Screenshot the change if it's CSS/layout.
2. Regenerate `resume.pdf` if the homepage was edited.
3. Update this file if a new convention emerges.
