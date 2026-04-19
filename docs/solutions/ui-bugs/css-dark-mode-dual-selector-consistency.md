---
category: ui-bugs
title: Dark mode styles missing [data-theme="dark"] selector, breaking manual toggle
problem_type: incomplete-implementation
components:
  - work/work.css
  - styles.css
  - script.js
symptoms:
  - Components on /work/ pages retain light-mode colors when user manually toggles dark mode
  - Works correctly when OS is set to dark mode (media query fires)
  - Affected components: release tags, architecture blocks, comparison table checkmarks, feature list done markers
root_cause: >
  The site uses two dark-mode triggers: @media (prefers-color-scheme: dark) for
  OS preference and [data-theme="dark"] for the manual JS toggle. Several component
  rulesets in work.css only had the @media query and omitted the [data-theme] selector.
  When a user on a light-mode OS toggles dark mode manually, the media query doesn't
  match, leaving those components with light-mode values.
fix_summary: >
  Added matching [data-theme="dark"] selectors for every @media dark-mode override
  in work.css that was missing one, following the pattern already established by
  .terminal, .prompt-excerpt pre, and .whoop-* colors in the same file.
tags:
  - css
  - dark-mode
  - prefers-color-scheme
  - data-theme
  - selector-parity
  - manual-toggle
  - visual-regression
resolved: 2026-04-18
---

# Dark mode styles missing [data-theme="dark"] selector

## Symptoms

Components on `/work/*` pages (release tags, architecture blocks, comparison table checkmarks, feature list done markers) render with light-mode colors when the user has manually toggled dark mode via the theme switch. The same components display correctly when the OS is set to dark mode.

## Investigation

1. Reviewed the dark mode architecture: two selectors work in tandem:
   - `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { ... } }` — respects OS preference unless user chose light
   - `:root[data-theme="dark"] { ... }` — applies when user manually selects dark regardless of OS
2. Confirmed `styles.css` consistently provides both selectors for every token override — the correct pattern.
3. Audited `work/work.css` and found components with only the `@media` query:
   - `.release-tag.security`, `.feature`, `.improvement`, `.fix` (lines 163-168)
   - `.arch-block` (lines 353-355)
   - `.comp-table .yes` (line 299) — hardcoded `#3a7a4a`, no dark mode at all
   - `.feature-list li.done::before` (line 245) — same hardcoded green
4. Other components in the same file (`.terminal`, `.prompt-excerpt pre`, `.whoop-*`) correctly used both selectors.
5. Reproduced: set OS to light mode, toggle site to dark. Affected components keep light-mode colors.

## Root cause

When component styles were added to `work/work.css`, only the `@media (prefers-color-scheme: dark)` query was included. This passed visual testing because the developer's OS was in dark mode, which triggers the `@media` rule. The manual toggle path (`[data-theme="dark"]`) was never exercised.

The two selectors serve different user journeys:
- **`@media` query**: User's OS is dark, user has NOT explicitly set `data-theme="light"` (automatic path)
- **`[data-theme="dark"]`**: User's OS is light, but user clicked the toggle to force dark (manual override path)

Both must exist for every dark mode override.

## Fix

For every component that had only the `@media` dark-mode block, add a matching `[data-theme="dark"]` rule with identical declarations:

```css
/* Already existed — OS-driven dark mode */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .release-tag.security { background: #4a2820; color: #f0b8a3; }
}
/* Added — manual toggle dark mode */
:root[data-theme="dark"] .release-tag.security { background: #4a2820; color: #f0b8a3; }
```

For components with hardcoded colors and no dark mode at all (`.comp-table .yes`, `.feature-list li.done::before`), added both selector forms with an appropriate dark-mode green (`#5cc06a`).

## Key insight

In a dual-selector dark mode system, every dark mode override must be written twice. Testing dark mode only with the OS preference set to dark misses the manual toggle path entirely. A reliable guard is to grep for `prefers-color-scheme: dark` and verify each match has a corresponding `[data-theme="dark"]` sibling rule.

## Prevention

1. **Template in CLAUDE.md.** Every dark-mode override should follow the dual-selector pattern:
   ```css
   @media (prefers-color-scheme: dark) {
     :root:not([data-theme="light"]) .my-component { /* dark values */ }
   }
   :root[data-theme="dark"] .my-component { /* identical dark values */ }
   ```

2. **Prefer CSS custom properties.** Components using only `var(--accent)`, `var(--card-bg)`, etc. need zero additional dark-mode CSS — the tokens already switch. The dual-selector problem only arises for values outside the token system.

3. **Test both dark paths.** After CSS changes, verify dark mode works via both:
   - OS dark mode ON (no `data-theme` attribute)
   - OS light mode + manual toggle (`data-theme="dark"`)

4. **Quick parity check:**
   ```bash
   for f in styles.css work/work.css; do
     echo "$f: @media=$(grep -c 'prefers-color-scheme: dark' $f) [data-theme]=$(grep -c 'data-theme=\"dark\"' $f)"
   done
   ```
   A large imbalance between the two counts signals missing selector pairs.

## Related

- `docs/solutions/accessibility/wcag-contrast-light-mode-accent-muted.md` — WCAG contrast baseline for the token values used in both theme modes
