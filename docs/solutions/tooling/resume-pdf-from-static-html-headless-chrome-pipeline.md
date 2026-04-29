---
title: "Generating an ATS-friendly résumé PDF from static HTML via headless Chrome `--print-to-pdf`"
slug: resume-pdf-from-static-html-headless-chrome-pipeline
category: tooling
tags: [print-stylesheet, headless-chrome, print-to-pdf, ats, resume, css-specificity, details-element, beforeprint, typography]
severity: moderate
component: "notebook.css (@media print), index.html (.print-name-block), script.js (beforeprint listener), resume.pdf"
symptom: "Generated résumé PDF rendered as a design-portfolio document instead of an ATS-friendly CV — no candidate name on page 1, mixed serif body + sans headings, six different font sizes, hidden certifications collapsed behind a <details> element, and project names blowing up to display size in the print output"
root_cause: "Three stacked problems behind a single 'the PDF doesn't look right' user report: (1) the homepage hero serves a brand voice ('A career of product instinct') with no candidate name — fine for the website, missing for ATS pipelines; (2) Chrome's <details> element is open-attribute-driven, not CSS-driven, so the CSS-only @media print stylesheet could not unfold the closed certifications collapse; (3) screen-mode CSS rules with higher specificity (e.g., `.nb-card.compact .nb-card-name`) silently win over print-mode rules (e.g., `.nb-card-name` inside @media print) because @media print doesn't grant extra specificity by itself"
date_solved: 2026-04-29
---

# Generating an ATS-friendly résumé PDF from static HTML via headless Chrome `--print-to-pdf`

## The Problem

`jameschang.co` is a static HTML/CSS/JS portfolio. The résumé PDF (`resume.pdf`) is produced by running headless Chrome against the homepage with the print stylesheet active:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=resume.pdf \
  http://127.0.0.1:8787/
```

That single command is the entire build chain. It works because `notebook.css` carries an `@media print` block (~190 lines) that reorders, restyles, and prunes the screen design into a one-page-ish CV.

The chain *worked* in the sense that it produced a PDF. It produced the *wrong PDF* in three independent ways:

1. **No name on page 1.** The screen hero is a brand statement (*"A career of product instinct. Shipping now at AI speed."*). The print stylesheet preserved that header verbatim — but a recruiter's ATS pipeline scans the top 1/4 of page 1 for the candidate's name + email + phone. There was no name block anywhere in the printed output.

2. **8 of 10 certifications missing.** The on-screen certifications use `<details>`/`<summary>` to collapse 8 LinkedIn Learning / Toggl / Jasper / HubSpot / Google Analytics certs behind a "+ 8 additional certifications" expander. The print stylesheet had `details > *:not(summary) { display: revert; }` to attempt to expose them — but the PDF still rendered with only the 2 default-visible certs. The 8 collapsed certs simply weren't there.

3. **Project names rendering at 20px in print.** The screen rule `.nb-card.compact .nb-card-name { font-size: 20px }` (2 classes specificity) was silently winning over the print rule `.nb-card-name { font-size: 10.5pt }` (1 class). Project headings in resume.pdf were the size of section headers, eating an extra page of vertical space.

User-visible report was a single sentence: *"the resume PDF doesn't look right — fonts and spacing inconsistent, no name at top."* All three causes were behind that one report.

## Root cause #1 — print-only identity block has no obvious home

A static-site-as-portfolio has two distinct identities:

- **Brand voice on screen** — the hero, the tagline, the design language.
- **Candidate identity in print** — name, email, LinkedIn, GitHub, location, in a format an ATS tool can parse.

A single HTML page can't usefully serve both at the top of the document. The screen wants poetry; the PDF wants vCard. There's no shared element that satisfies both contexts because the *purpose* of the top-of-page content is different.

Naïve fixes that don't work:
- Add the name to the screen hero — turns the website into a generic résumé site.
- Use CSS `content: "James Chang"` on a `::before` — works visually but ATS pipelines often ignore generated content (and parsing semantics are fragile).
- Render two `<h1>` blocks and hide the screen one in print — splits the document head and confuses screen readers about which is the page's primary heading.

The right answer is a **print-only `<header>` element**: present in the DOM, hidden by default on screen via `display: none`, revealed via `@media print { ... display: block }`. It carries the candidate's name, tagline, and contact line as real semantic HTML — ATS-parseable, recruiter-readable, screen-invisible.

## Root cause #2 — `<details>` is open-attribute-driven, not CSS-driven

Chrome (and Safari, and Firefox) implement `<details>` collapse/expand via the `open` attribute. CSS *cannot* unfold a closed `<details>` no matter how creatively you target the children:

```css
/* All of these LOOK right and DO NOTHING. */
@media print {
  details { display: block; }
  details > summary { display: none; }
  details > *:not(summary) { display: revert; }      /* ❌ */
  details > *:not(summary) { display: block; }       /* ❌ */
  details > *:not(summary) { display: block !important; }  /* ❌ */
}
```

The browser's user-agent stylesheet has higher-priority rules tied to the *element's open state*. When `<details>` is closed, child content is suppressed at the layout level, before stylesheets get to express opinions about it.

The actual fix has to flip the `open` attribute on the element itself. JavaScript that runs before the print rasterizer is the cleanest path:

```javascript
window.addEventListener("beforeprint", () => {
  document.querySelectorAll("details").forEach(d => d.setAttribute("open", ""));
});
```

`beforeprint` fires reliably on `--print-to-pdf` runs (verified in this project — the 8 hidden certs went from invisible to fully rendered after adding the listener). Optional: add a corresponding `afterprint` listener that removes `open` if you don't want the on-screen state to drift after a user prints from the browser.

## Root cause #3 — `@media print` doesn't grant extra specificity

This is the rule most people guess wrong: **`@media print` rules do not have higher specificity than non-print rules.** They only override when:
- The media context matches (i.e., during print rendering), AND
- The selector specificity is at least equal, AND
- They appear later in source order OR carry `!important`.

Practical consequence: a screen rule like `.nb-card.compact .nb-card-name { font-size: 20px }` (specificity 0,2,1) beats `.nb-card-name { font-size: 10.5pt }` (specificity 0,1,1) inside `@media print` *every time* — even though the print rule "should" be more specific by virtue of the media query.

Two fixes work, both should be in the toolkit:

1. **Match specificity in print.** Mirror the screen selector path:
   ```css
   @media print {
     .nb-card.compact .nb-card-name { font-size: 10.5pt; }
   }
   ```

2. **Use `!important`.** The nuclear option. Reserve for properties where you've verified the screen rule has higher specificity than you can match without ugly selector chains:
   ```css
   @media print {
     .nb-card-name { font-size: 10.5pt !important; }
   }
   ```

The mistake to avoid: assuming `@media print` "wins by default" and writing thin print rules that get steamrolled by the cascade.

## Working solution

### Step 1 — Add the print-only identity block

In `index.html`, immediately after `<body>`:

```html
<!-- Print-only header: ATS-parseable name + contact block. Hidden on screen
     (handled by .print-name-block { display: none } in notebook.css) and
     shown via @media print. This is the resume.pdf identity block. -->
<header class="print-name-block">
  <h1 class="print-name">James Chang</h1>
  <p class="print-tagline">Senior Product Manager &middot; AI-Assisted Builder &middot; Los Angeles, CA</p>
  <p class="print-contact">
    <a href="mailto:jimmychang316@gmail.com">jimmychang316@gmail.com</a>
    <span class="sep">&middot;</span>
    <a href="https://www.linkedin.com/in/jimmychang316">linkedin.com/in/jimmychang316</a>
    <span class="sep">&middot;</span>
    <a href="https://github.com/thirstypig">github.com/thirstypig</a>
    <span class="sep">&middot;</span>
    <a href="https://jameschang.co">jameschang.co</a>
  </p>
</header>
```

In `notebook.css`, **outside any media query** (so it applies on screen):

```css
.print-name-block { display: none; }
```

Inside `@media print`:

```css
.print-name-block {
  display: block;
  text-align: center;
  margin: 0 0 0.55rem;
  padding-bottom: 0.4rem;
  border-bottom: 1pt solid #000;
}
.print-name {
  font-size: 18pt;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin: 0 0 0.2rem;
}
.print-tagline { font-size: 10.5pt; font-style: italic; margin: 0 0 0.2rem; }
.print-contact { font-size: 9.5pt; margin: 0; }
.print-contact a { color: #000; text-decoration: underline; }
.print-contact .sep { margin: 0 0.4em; color: #666; }
```

### Step 2 — Expand `<details>` before print rendering

Add to `script.js` at top level (outside any IIFE so it runs immediately):

```javascript
window.addEventListener("beforeprint", () => {
  document.querySelectorAll("details").forEach(d => d.setAttribute("open", ""));
});
```

This works for `window.print()` from the browser AND `chrome --print-to-pdf` from the command line.

### Step 3 — Pin print typography with single sans-serif + 4 sizes

Inside `@media print`, override the screen body font with `!important` to defeat any inherited screen rules that would specify font-family:

```css
@media print {
  body, h1, h2, h3, h4, p, li, dt, dd, span, a {
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue",
                 Helvetica, Arial, sans-serif !important;
  }
  body { font-size: 10pt; line-height: 1.35; }

  /* Four sizes: 18pt name, 11pt section headings, 10.5pt institutions/companies,
     10pt body, 9.5pt italic dates/roles. Don't add a 6th size. */
}
```

### Step 4 — Match screen specificity in print rules

For every screen rule with multi-class specificity that controls something visual in print, mirror the selector inside `@media print`:

```css
@media print {
  /* Screen: .nb-card.compact .nb-card-name { font-size: 20px }
     Print:  match the specificity OR use !important. */
  .nb-card-name,
  .nb-card.compact .nb-card-name {
    font-size: 10.5pt !important;
    font-weight: 700 !important;
    letter-spacing: normal !important;
  }
}
```

### Step 5 — Defeat letter-spacing + text-transform from the screen design language

Screen-mode mono labels often use `letter-spacing: 1px` + `text-transform: uppercase`. In print these read as awkward (`AI` becomes `Ai`, labels crawl wide). Override aggressively:

```css
@media print {
  .nb-skill-row dt,
  .nb-membership-role,
  .nb-membership-meta,
  .nb-card-meta,
  .nb-section-eyebrow {
    letter-spacing: normal !important;
    text-transform: none !important;
  }
}
```

### Step 6 — Strip footer noise + screen hero from print

Anything that's brand voice, design ornament, or footer attribution belongs hidden in print:

```css
@media print {
  .nb-nav,
  .nb-hero,
  .nb-terminal,
  .skip-link,
  .theme-toggle,
  .nb-section-num,
  .nb-section-rule,
  .nb-headshot,
  .nb-footer,
  .nb-footer-contact { display: none !important; }
}
```

### Step 7 — Allow sections to break naturally

Avoid `break-inside: avoid` on whole sections — it produces giant white-space gaps when a section is just slightly too tall to fit. Apply it only to the smaller atomic blocks:

```css
@media print {
  .nb-section { break-inside: auto; }
  .nb-exp-row, .nb-card, .nb-membership, .nb-degree {
    break-inside: avoid;
    page-break-inside: avoid;
  }
}
```

### Step 8 — Regenerate

```bash
python3 -m http.server 8787 &
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=resume.pdf \
  http://127.0.0.1:8787/
```

Verify with `pdftotext resume.pdf - | head -30` — the candidate name should appear on the first line of extracted text. Open the PDF visually to confirm typography.

## Investigation steps that didn't apply

- **Generated content (`::before { content: 'James Chang' }`)**: works visually but ATS parsers often ignore it. Don't rely on it for any text that needs to be machine-readable.

- **Two `<h1>` elements (one screen, one print)**: splits the page's primary heading into two competing semantic anchors. Bad for screen readers, bad for SEO, fragile in print. Use a single `<h1>` per context with proper display toggling.

- **Nonce-based or hash-based CSP for inline `<style>` blocks**: irrelevant — print stylesheets live inside the same `notebook.css` and don't introduce new inline content. (See `docs/solutions/security-issues/csp-unsafe-inline-removal-via-script-externalization.md` for the related CSP work.)

- **Custom Chrome flags to force `<details>` open**: there isn't one. The browser's `<details>` rendering is open-attribute-driven by spec.

- **`page-break-inside: avoid` on every section**: causes more problems than it solves on multi-page résumés. Apply only to atomic blocks.

## Prevention strategies

### Tests added the same day

Five e2e tests in `tests/test_site_e2e.py::TestPrintStylesheet`:

1. `test_print_name_block_only_on_homepage` — the `<header class="print-name-block">` exists on `index.html` only. Catches accidental deletion (PDF nameless on page 1) AND accidental copy-paste to other pages (duplicate name blocks).

2. `test_print_name_block_hidden_on_screen` — `notebook.css` carries a top-level `.print-name-block { display: none }` rule outside `@media print`. Guards against the hide rule being removed and the print-only block bleeding onto the homepage.

3. `test_print_name_block_contact_canonical_urls` — the four canonical contact channels (email, LinkedIn handle, GitHub handle, jameschang.co) all appear inside the print-name-block region. Catches typos when contact info changes.

4. `test_script_js_expands_details_on_print` — `script.js` carries a `beforeprint` listener that calls `setAttribute("open", "")` on every `<details>` element. Without this, Chrome's `<details>` stays collapsed in `--print-to-pdf` and the 8 additional certifications drop out of `resume.pdf`. **This is the highest-leverage test of the five** — the regression it prevents is invisible until someone prints.

5. `test_print_card_name_overrides_screen_size` — the print rule for `.nb-card-name` either matches the screen specificity (`.nb-card.compact .nb-card-name`) or uses `!important`. Catches the exact specificity-leak regression that was fixed in this work.

### Documentation

Add to `CLAUDE.md`'s "Print stylesheet" section:

> **`<details>` expansion**: Chrome's `<details>` is open-attribute-driven, not CSS-driven. `script.js` carries a `beforeprint` listener that opens every `<details>` before print so the additional-certifications collapse renders fully in `resume.pdf`. Don't rely on CSS-only solutions for `<details>` in print.
>
> **CSS specificity**: `@media print` does not grant extra specificity. When overriding a screen rule with multi-class specificity (e.g., `.nb-card.compact .nb-card-name`), the print rule must match the specificity OR use `!important`. The `TestPrintStylesheet::test_print_card_name_overrides_screen_size` test guards this.

### Workflow

After any non-trivial edit to `index.html` headers, `script.js`, or the print stylesheet:

```bash
# Regenerate + visually inspect
python3 -m http.server 8787 &
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=resume.pdf http://127.0.0.1:8787/
pdftotext resume.pdf - | head -30
```

If the first line of extracted text isn't the candidate's name, something broke.

## Related docs

- **`docs/solutions/integration-issues/silent-fetch-failure-csp-graceful-fail-debugging.md`** (2026-04-16) — Covers the same headless-Chrome-with-stderr-logging debug technique that's useful for diagnosing print-pipeline issues. Not directly related, but the debug-tooling overlap is real.

- **`docs/solutions/security-issues/csp-unsafe-inline-removal-via-script-externalization.md`** (2026-04-28) — Sibling CSP-hardening work. Notes that JSON-LD `<script type="application/ld+json">` blocks aren't subject to `script-src` because they're data, not code; the same is *not* true of inline scripts that need to run for print prep — those need to live in an external `.js` file (which is why the `beforeprint` listener went in `script.js`, not inline in `<head>`).

## Lessons

1. **A static site that generates a PDF has two top-of-page identities, not one.** Brand voice on screen, candidate identity in print. The print-only `<header class="print-name-block">` pattern is the cleanest separation: real semantic HTML, screen-hidden by default, ATS-parseable in print.

2. **Chrome's `<details>` print expansion needs JavaScript.** No amount of CSS will unfold a closed `<details>` for print. Stash a `beforeprint` listener that flips `open` on every `<details>`. This is the single most "silent-regression-prone" piece of the chain — invisible until someone prints, easy to delete in a refactor.

3. **`@media print` is not a specificity bonus.** Print rules don't get extra weight just because they're in a print context. Mirror the screen selector specificity OR reach for `!important`. The day someone removes your `!important` in a "let's clean this up" pass is the day project names blow up to 20px in the PDF.

4. **Test the print pipeline statically when you can.** Five string-matching assertions in `test_site_e2e.py` cost nothing to maintain and catch every regression class above. A real headless-Chrome-rasterize-and-inspect E2E test would be more thorough but requires Playwright as a hard dependency. Static asserts give you 80% of the safety with 0% of the dependency cost.

5. **The friction to do this right was tedium, not technique.** A single `print-name-block` element + 8 lines of script.js + 30 lines of print CSS overrides + 5 tests was the entire fix. When a hardening or polish task keeps not getting done, ask whether the obstacle is structural (no place for the change to live) — and if it is, build the place. The pattern compounds the next time anyone needs to ship a CV from a static site.
