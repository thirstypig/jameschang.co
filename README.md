# jameschang.co

Personal site for James Chang — founder of Aleph Co. and senior product manager. Plain HTML/CSS/JS, deployed from this repo via GitHub Pages to the custom domain `jameschang.co`.

> **For agents:** See `CLAUDE.md` for the authoritative reference — conventions, CSS tokens, feed architecture, and operational notes. This README is the human-facing summary.

## Structure

| Path | Purpose |
|------|---------|
| `index.html` | Homepage — hero, about, experience, education, skills, projects, case studies, testimonials |
| `notebook.css` | Site-wide design system (CSS custom properties, notebook aesthetic) + `@media print` résumé stylesheet |
| `script.js` | Theme toggle (light/dark, persisted in localStorage) |
| `now/index.html` | Derek Sivers-style /now page with 8 automated data feeds + 7 per-project TLDR/shipping blocks |
| `projects/` | Deep-dive project pages (Aleph, Fantastic Leagues, Judge Tool) |
| `projects/projects.css` | Component styles for the 14 deep-dive sub-pages (consumes notebook design tokens) |
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
- 8 automated data feeds on /now (WHOOP, Spotify, Plex, MLB Dodgers, FBST standings, Goodreads currently-reading, Goodreads read, Thirsty Pig hitlist) + per-project TLDRs and shipping activity pulled from each project's CLAUDE.md and GitHub events
- 174 tests (pytest) with pre-commit hook and CI
- Google Analytics 4 + Google Search Console

## License

Content (c) James Chang. Code available under MIT if anyone wants to fork the structure.
