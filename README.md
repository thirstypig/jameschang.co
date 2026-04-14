# jameschang.co

Personal site for James Chang — founder of Aleph Co. and senior product manager. Plain HTML/CSS/JS, deployed from this repo via GitHub Pages to the custom domain `jameschang.co`.

## Editing

Everything of substance is in `index.html`. Edit it, commit, push. That's it — no build step.

```bash
git add index.html
git commit -m "Update Aleph Compliance case study"
git push
```

The site redeploys automatically within ~1 minute of push.

## Local preview

```bash
python3 -m http.server 8000
# → open http://localhost:8000
```

## Regenerating the résumé PDF

The print stylesheet in `styles.css` (`@media print` block) renders the page as a clean, one-to-two page résumé when printed. Workflow:

1. Open `https://jameschang.co` in Chrome or Safari
2. `Cmd-P` → Destination: Save as PDF → Margins: Default → Background graphics: off
3. Save as `resume.pdf` in repo root, commit, push

The print stylesheet:
- Hides the nav, CTA buttons, and GitHub footer link
- Force-expands the collapsed "Earlier experience" `<details>` section
- Strips the hero to name + positioning + lede
- Uses serif typography + 10pt base for print density

## Missing before launch

- `/assets/headshot.jpg` — drop in a 400–800px square JPG/WebP of your professional headshot
- `/assets/og-image.png` — 1200×630 PNG for social previews (can be a crop/reuse of the headshot, with name overlay if desired)
- `/assets/favicon.svg` — SVG favicon
- `/assets/apple-touch-icon.png` — 180×180 PNG for iOS home-screen
- `/resume.pdf` — generate via the print flow above after first deploy

## File structure

| Path | Purpose |
|------|---------|
| `index.html` | The whole page — content, sections, JSON-LD |
| `styles.css` | Design system + `@media print` stylesheet |
| `script.js` | Email-reveal click handler (only JS on the site) |
| `CNAME` | Custom domain for GitHub Pages |
| `.nojekyll` | Disables Jekyll processing |
| `robots.txt` | Allows Google/Bing + LLM crawlers; blocks SEO-scrape bots |
| `sitemap.xml` | Single URL, declared in robots.txt |
| `llms.txt` | Plain-text summary for LLM crawlers |
| `assets/` | Headshot, OG image, favicons |
| `PLAN.md` | Design plan (reference; not served) |
| `CONTENT_SOURCES.md` | Working notes on content sources (reference; not served) |

## GitHub Pages setup

1. Repo → Settings → Pages → Source: **Deploy from a branch** → Branch: `main` / `/` (root)
2. Custom domain: `jameschang.co` (already configured via the `CNAME` file)
3. Enforce HTTPS: ✓ (check this after the Let's Encrypt cert provisions — usually 5–15 min after DNS resolves)

## DNS (at your registrar)

Apex (`jameschang.co`) — four A records and four AAAA records:

```
A     @    185.199.108.153
A     @    185.199.109.153
A     @    185.199.110.153
A     @    185.199.111.153
AAAA  @    2606:50c0:8000::153
AAAA  @    2606:50c0:8001::153
AAAA  @    2606:50c0:8002::153
AAAA  @    2606:50c0:8003::153
CNAME www  thirstypig.github.io
```

DNS typically propagates in 1–6h; Let's Encrypt cert provisions automatically once DNS resolves.

## Stack

- HTML5, CSS3, ~20 lines of vanilla JS
- Zero dependencies. No build step. No npm.
- System font stack + serif fallback (no Google Fonts → no GDPR issue, no round-trip cost)
- Dark mode via `prefers-color-scheme` (no toggle)
- WCAG 2.2 AA target, Core Web Vitals green
- Total page weight target: under 50KB gzipped (excluding images)

## License

Content © James Chang. Code available under MIT if anyone wants to fork the structure.
