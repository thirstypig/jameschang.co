# Adding a new project deep-dive

Each project-with-a-deep-dive has its own folder under `/projects/[slug]/` with sub-pages (how-it-works, tech, roadmap, changelog, dashboard). They share `/projects/projects.css`.

## Steps

1. Create `/projects/[slug]/` with sub-pages (e.g. `tech/index.html`, `roadmap/index.html`, `changelog/index.html`). Copy an existing project's page as the template — match the CSP meta tag, JSON-LD, breadcrumbs, `.cross-project-nav`, `.project-nav`, `.snapshot-banner`, `.work-hero`, footer, and script tag.

2. Set `aria-current="page"` on the active tab in `.project-nav` for each sub-page, and on the matching chip in `.cross-project-nav`.

3. Add the project to `/projects/index.html` (the work landing page).

4. Add a project card to the `#work` section grid in `index.html`.

5. Add all new URLs to `sitemap.xml`.

6. Add the Dashboard tab to `.project-nav` in **all** sibling sub-pages if adding a dashboard page.

7. **Cross-project nav update** (added 2026-04-28): add the new project as a chip in the `.cross-project-nav` block on **every existing deep-dive sub-page** (currently 13 across Aleph + Fantastic Leagues + Judge Tool). The chip's `href` should point at the new project's canonical entry-point sub-page (e.g., `/projects/{new-slug}/{tech-or-default}/`).

8. Update `tests/test_site_e2e.py::TestCrossProjectNav.EXPECTED_LINKS` to include the new slug, and bump the `len(self.DEEP_DIVES)` assertion to match the new total. The e2e suite enforces presence + canonical hrefs + aria-current; without the test update, CI will flag the mismatch immediately.

## Headshot rotation

The About section cycles through 7 photos using JS-driven crossfade (5s interval, `script.js`). Images need `object-position` tuning per photo. Respects `prefers-reduced-motion` (freezes on first image). New photos need AVIF + WebP variants and a `.headshot-*` class for positioning.
