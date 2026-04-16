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
/work/                  Deep-dive case-study pages (Aleph, Fantastic Leagues, Judge Tool)
/privacy/               Privacy policy (required by WHOOP app registration)
/whoop/callback/        OAuth2 redirect target (static page that reads ?code= from URL)
/assets/                Images (AVIF/WebP/PNG responsive triples), favicons, OG image
/bin/                   Maintenance scripts (whoop-auth.sh, whoop-encrypt.sh, update-whoop.py, update-spotify.py, update-public-feeds.py, spotify-auth.sh)
/.github/workflows/     GitHub Actions (daily WHOOP sync)
/docs/solutions/        Internal knowledge base — past solved problems (see /ce:compound)
/todos/                 Code-review findings (see /ce:review)
/resume.pdf             Generated from the homepage print stylesheet
.whoop-token.enc        AES-encrypted WHOOP refresh token (committed, decrypted at runtime)
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

Each project-with-a-deep-dive has its own folder under `/work/[slug]/` with sub-pages (how-it-works, tech, roadmap, changelog). They share `/work/work.css`. Navigation within a project uses `.project-nav`; back to home uses `.crumbs`.

## Data feeds on /now

The `/now` page is assembled from several independent sync scripts that each write into an HTML block delimited by `<!-- FEED-START -->` / `<!-- FEED-END -->` markers in `now/index.html` (e.g. `<!-- WHOOP-START -->`, `<!-- SPOTIFY-START -->`, etc.). **Don't remove the markers** — they are the replacement targets for the sync scripts.

- **WHOOP** — daily via `.github/workflows/whoop-sync.yml`. Refresh token stored **encrypted in the repo** (`.whoop-token.enc`), decrypted at runtime with a GitHub Secret passphrase (`WHOOP_TOKEN_KEY`), re-encrypted + committed each run. This avoids needing a PAT for `secrets: write`. Full write-up in `docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md`. **Required GitHub Secrets:** `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, `WHOOP_TOKEN_KEY`.
- **Spotify** — every 4 hours via `.github/workflows/spotify-sync.yml`. Refresh token stored in plain text as a GitHub Secret (`SPOTIFY_REFRESH_TOKEN`); the script writes `.spotify-state.json` to remember the last-seen podcast episode so the now-playing block doesn't flap when playback pauses. **Required GitHub Secrets:** `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`.
- **Public feeds** (GitHub events, MLB Stats API / Dodgers, Letterboxd RSS, The Fantastic Leagues / FBST standings) — every 6 hours via `.github/workflows/public-feeds-sync.yml`. All four are unauthenticated; no secrets needed. Handled by `bin/update-public-feeds.py`.

### Adding a new data feed

1. Add a new `<section class="work-section">` to `now/index.html` with `FEED-START` / `FEED-END` markers.
2. Add CSS for the feed's presentation in `work/work.css` (use existing CSS tokens).
3. Write a Python function that fetches + returns the HTML block; add to `bin/update-public-feeds.py` (for unauth) or a new `bin/update-{feed}.py` (for OAuth).
4. Add the fetch to the `main()` of the sync script; use `replace_marker()` to insert.
5. If OAuth: add a callback page at `/{service}/callback/`, auth script at `bin/{service}-auth.sh`, workflow at `.github/workflows/{service}-sync.yml`.

## Third-party fetches on /now/

The Places-I-want-to-try section fetches `https://thirstypig.com/places-wishlist.json` client-side. CORS is locked to `https://jameschang.co`, so the section won't render on `localhost` (expected). Graceful-fail pattern: on fetch error or empty list, the `<section id="wishlist-section">` is `.remove()`'d — no empty shell visible.

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

## Known outstanding items

See `todos/*-pending-*.md` for the active code-review findings queue.

## Commit/push workflow

Direct push to `main` — this repo uses no PR gate (one contributor). GitHub Pages redeploys within ~1 minute. Pre-commit:

1. Screenshot the change if it's CSS/layout.
2. Regenerate `resume.pdf` if the homepage was edited.
3. Update this file if a new convention emerges.
