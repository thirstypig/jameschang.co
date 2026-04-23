# jameschang.co

Personal site for James Chang — founder of Aleph Co. and senior product manager. Plain HTML/CSS/JS, deployed from this repo via GitHub Pages to the custom domain `jameschang.co`.

> **For agents:** See `CLAUDE.md` for the authoritative reference — conventions, CSS tokens, feed architecture, and operational notes. This README is the human-facing summary.

## Structure

| Path | Purpose |
|------|---------|
| `index.html` | Homepage — hero, about, experience, education, skills, projects, case studies, testimonials |
| `styles.css` | Design system (CSS custom properties) + `@media print` resume stylesheet |
| `script.js` | Theme toggle (light/dark) + headshot rotation (crossfade, respects reduced-motion) |
| `now/index.html` | Derek Sivers-style /now page with 11 automated data feeds |
| `work/` | Deep-dive project pages (Aleph, Fantastic Leagues, Judge Tool) |
| `work/work.css` | Shared styles for /work and /now pages |
| `privacy/` | Privacy policy (required by WHOOP/Spotify app registrations) |
| `bin/` | Python sync scripts (WHOOP, Spotify, Trakt, Plex, public feeds) |
| `.github/workflows/` | GitHub Actions for automated feed updates + staleness monitoring |

## Local preview

```bash
python3 -m http.server 8787
# open http://localhost:8787/
```

## Regenerating the resume PDF

```bash
python3 -m http.server 8787 &
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=resume.pdf http://127.0.0.1:8787/
```

## Stack

- HTML5, CSS3, vanilla JS (~60 lines). Zero dependencies. No build step.
- System font stacks (no web fonts)
- Dark mode via `prefers-color-scheme` + manual toggle (persisted in localStorage)
- WCAG 2.2 AA compliant. Lighthouse 100/100/100/100.
- 10 automated data feeds on /now (WHOOP, Spotify, Trakt, Plex, MLB, Letterboxd, Goodreads currently-reading, Goodreads read, FBST, Thirsty Pig hitlist) + per-project TLDRs and shipping activity pulled from each project's CLAUDE.md and GitHub events
- 160 tests (pytest) with pre-commit hook and CI
- Google Analytics 4 + Google Search Console

## License

Content (c) James Chang. Code available under MIT if anyone wants to fork the structure.
