# jameschang.co

Personal site for James Chang — founder of Aleph Co. and senior product manager. Plain HTML/CSS/JS, deployed from this repo via GitHub Pages to the custom domain `jameschang.co`.

> **For agents:** See `CLAUDE.md` for the authoritative reference — conventions, CSS tokens, feed architecture, and operational notes. This README is the human-facing summary.

## Structure

| Path | Purpose |
|------|---------|
| `index.html` | Homepage — hero, about, experience, education, skills, projects, case studies, testimonials |
| `notebook.css` | Site-wide design system (CSS custom properties, notebook aesthetic) + `@media print` résumé stylesheet |
| `script.js` | Theme toggle (light/dark, persisted in localStorage) |
| `now/index.html` | Derek Sivers-style /now page with 8 cron-synced data feeds (incl. Google Calendar) + 9 cron-classified per-project TLDR/shipping cards + client-rendered sections (hitlist, bucket list, quotes) |
| `projects/` | Deep-dive project pages (Aleph, Fantastic Leagues, Judge Tool) |
| `projects/projects.css` | Component styles for the 13 deep-dive sub-pages (consumes notebook design tokens) |
| `privacy/` | Privacy policy (required by WHOOP/Spotify app registrations) |
| `bin/` | Python sync scripts (WHOOP, Spotify, Plex, public feeds, per-project TLDRs) |
| `.github/workflows/` | GitHub Actions for automated feed updates + staleness monitoring |

## Local preview

```bash
python3 -m http.server 8787
# open http://localhost:8787/
```

## Regenerating the resume PDF

```bash
python3 -m http.server 8787 &
SERVER_PID=$!
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=resume.pdf http://127.0.0.1:8787/
kill "$SERVER_PID"
```

## Stack

- HTML5, CSS3, vanilla JS (~60 lines). Zero dependencies. No build step.
- Self-hosted Geist Mono + Space Grotesk WOFF2 (homepage + /now); system font stacks elsewhere
- Dark mode via `prefers-color-scheme` + manual toggle (persisted in localStorage)
- WCAG 2.2 AA compliant. Lighthouse 100/100/100/100.
- 8 cron-synced data feeds on /now (WHOOP, Spotify, Plex, MLB Dodgers, FBST standings, Goodreads currently-reading, Goodreads read, Google Calendar) — each with a staleness heartbeat — plus client-rendered sections (Thirsty Pig hitlist, bucket list, quotes) that fetch JSON at runtime with no cron + per-project TLDRs and shipping activity pulled from each project's CLAUDE.md and GitHub events + per-project roadmap content synced from each source repo's native format (Aleph markdown, JT markdown, FL TypeScript) via per-project adapters
- 307 tests (pytest, across 10 files) with pre-commit hook and CI
- Google Analytics 4 + Google Search Console

## License

Content (c) James Chang. Code available under MIT if anyone wants to fork the structure.
