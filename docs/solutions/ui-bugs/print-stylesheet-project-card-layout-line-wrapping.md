---
name: print-stylesheet-project-card-flexbox
title: "CSS Print Layout: Force Project Names and Descriptions to Stay on Single Line"
description: "Fix for project card layout breaking to separate lines in PDF print output using CSS flexbox and specificity matching"
category: ui-bugs
problem_type: css-specificity, print-media-override, layout-regression
components:
  - notebook.css
  - index.html
  - script.js
symptoms:
  - Project name on one line, description on next line in PDF (should be inline)
  - "Aleph Co. — \n Compliance SaaS for..." instead of "Aleph Co. — Compliance SaaS for..."
root_cause: "Block-level HTML elements (h3, p) not staying inline despite display: inline declarations; flexbox needed to enforce layout"
tags:
  - print-stylesheet
  - css
  - media-query
  - flex-layout
  - typography
  - pdf-formatting
resolved: "2026-06-23"
---

## Problem Summary

In the resume PDF, project names and descriptions were breaking to separate lines instead of staying inline:

```
Aleph Co. —
Compliance SaaS for US importers covering FDA, CPSIA, Prop 65, PFAS.
```

Should render as:

```
Aleph Co. — Compliance SaaS for US importers covering FDA, CPSIA, Prop 65, PFAS.
```

## Root Cause

The HTML structure uses separate block elements:

```html
<h3 class="nb-card-name">Aleph Co.</h3>
<p class="nb-card-body">Compliance SaaS...</p>
```

Even with `display: inline` in print CSS, the `<h3>` and `<p>` tags respect their default block behavior, causing line breaks between name and description.

Three previous approaches failed:
1. **`display: inline` alone** — didn't work; block elements still respected their inherent flow
2. **`white-space: nowrap`** — text still wrapped despite no-wrap declaration
3. **Specificity matching without flexbox** — children still rendered as blocks

## Working Solution

Use CSS flexbox with `flex-wrap: nowrap` on the card container to force children onto a single line.

### Implementation

**In `notebook.css` inside `@media print { }` block (around line 1897):**

```css
.nb-card.compact {
  padding: 0 !important;
  margin-bottom: 0.08rem;
  page-break-inside: avoid;
  display: flex !important;
  flex-wrap: nowrap !important;
  align-items: baseline !important;
}

.nb-card-name,
.nb-card.compact .nb-card-name {
  font-size: 10.5pt !important;
  font-weight: 700 !important;
  letter-spacing: normal !important;
  margin: 0 !important;
  padding: 0 !important;
  color: #000;
  display: inline !important;
  flex-shrink: 0 !important;
}

.nb-card-name::after { 
  content: " — "; 
}

.nb-card-url { 
  display: none; 
}

.nb-card-body {
  font-size: 10pt !important;
  line-height: 1.3 !important;
  color: #000;
  margin: 0 !important;
  padding: 0 !important;
  display: inline !important;
  flex-shrink: 1 !important;
}

.nb-card-meta { 
  display: none; 
}
```

### Key CSS Properties

| Property | Value | Purpose |
|----------|-------|---------|
| `display: flex` | On `.nb-card.compact` | Creates flex container for children |
| `flex-wrap: nowrap` | On `.nb-card.compact` | Prevents children from wrapping to new lines |
| `align-items: baseline` | On `.nb-card.compact` | Aligns name and description on their baselines |
| `flex-shrink: 0` | On `.nb-card-name` | Prevents project name from shrinking/wrapping |
| `flex-shrink: 1` | On `.nb-card-body` | Allows description to shrink if needed but prevents wrapping |
| `display: inline` | On both name and body | Overrides screen `display: block` declarations |
| `!important` | Throughout | Ensures print rules win over higher-specificity screen rules |

## How to Verify It Works

### Visual Check
1. Generate resume.pdf locally:
   ```bash
   python3 -m http.server 8787 &
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
     --headless --disable-gpu --no-pdf-header-footer \
     --print-to-pdf=resume.pdf http://127.0.0.1:8787/
   ```

2. Open in Preview.app and verify:
   - All 5 projects display with name and description on the same line
   - Font size is 10-11pt (not 20px)
   - Line spacing is tight and professional

### Text Extraction Test
```bash
pdftotext resume.pdf - | grep -A 10 "PROJECTS"
```

Expected output (all on one line in text extraction):
```
Aleph Co. —Compliance SaaS for US importers covering FDA, CPSIA, Prop 65, PFAS.
The Fantastic Leagues —AI fantasy baseball with live auctions, 26 modules, 730+ tests, hybrid scoring.
```

### ATS Verification
- Open resume.pdf in PDF reader
- Select all (Cmd+A) → copy → paste into plain text editor
- Verify readable and project information flows naturally (no awkward line breaks)

## Prevention Strategies

### When Adding Print CSS Rules

**Checklist:**
1. Identify all screen-mode rules affecting the element (grep the class name)
2. Calculate specificity of each screen rule
3. Compare against print rule specificity
4. If print specificity < screen specificity, either:
   - Match the selector (e.g., `.nb-card.compact .nb-card-name { ... }`)
   - Add `!important` (last resort)

**Testing:**
- Always generate resume.pdf locally before pushing
- Verify in Preview.app or PDF reader
- Check both light and dark OS themes
- Ensure no huge white-space gaps between sections

### Best Practices for Display Properties in Print

1. **Match specificity** instead of using `!important`:
   ```css
   /* Better: match screen specificity */
   .nb-card.compact .nb-card-name { font-size: 10.5pt; }
   
   /* Avoid: relies on !important */
   .nb-card-name { font-size: 10.5pt !important; }
   ```

2. **Use flexbox surgically** for inline forcing:
   - Only when you need child elements forced to single line
   - Use `flex-shrink: 0` for content that must not wrap
   - Use `flex-shrink: 1` for content that can shrink/wrap

3. **Override theme colors in print**:
   ```css
   @media print {
     :root, [data-theme="dark"] {
       --bg: #fff;
       --ink: #000;
       /* ... reset all colors ... */
     }
   }
   ```

4. **Use system fonts in print**:
   ```css
   @media print {
     body {
       font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif !important;
     }
   }
   ```

5. **Use `page-break-inside: avoid` only on atomic blocks**:
   - ✓ Individual cards, rows, details
   - ✗ Whole sections (causes huge gaps)

## Related Issues

- **CSS specificity parity**: Similar pattern in `docs/solutions/ui-bugs/css-dark-mode-dual-selector-consistency.md` — media queries don't grant extra specificity; must match selector parity or use `!important`
- **Print-only identity blocks**: See `docs/solutions/tooling/resume-pdf-from-static-html-headless-chrome-pipeline.md` for print-only content architecture
- **`<details>` in print**: Requires `beforeprint` event listener in `script.js` to call `.setAttribute("open", "")` — CSS alone cannot unfold collapsed details

## Testing

Five e2e tests guard against regressions:
- `test_print_card_name_font_size` — Verifies 10.5pt (not 20px)
- `test_print_card_single_line` — Confirms name + description on one line
- `test_print_no_wrapping_mid_project_name` — Project name doesn't wrap mid-word
- `test_print_flex_properties_present` — Flexbox properties in stylesheet
- `test_resume_pdf_project_section_visual` — Visual regression test (SSIM > 0.98)

See: `tests/test_site_e2e.py::TestPrintStylesheet`

## Files Modified

- `/Users/jameschang/Projects/jameschang.co/notebook.css` (lines 1897–1926)
- `/Users/jameschang/Projects/jameschang.co/resume.pdf` (regenerated 2026-06-23)

## Timeline

| Date | Status |
|------|--------|
| 2026-06-23 11:01 | Initial CSS `display: inline` attempt — failed |
| 2026-06-23 13:00 | Tried `white-space: nowrap` — failed |
| 2026-06-23 13:10 | Flexbox approach implemented — **working** ✓ |
| 2026-06-23 13:21 | Verified live at https://jameschang.co/resume.pdf |
