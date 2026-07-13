---
name: project-card-styling-consistency
description: Reorder project card sections and apply consistent "upcoming roadmap features" label styling across all /now projects
category: ui-bugs
components_affected:
  - now/index.html
  - notebook.css
  - tests/test_site_e2e.py
symptoms:
  - Inconsistent section ordering within project cards (description vs next-up placement)
  - Missing or mismatched "upcoming roadmap features" label styling across projects
  - Test assertions referencing outdated card structure
root_cause:
  - Label styling not defined as reusable CSS class (.nb-proj-roadmap-label)
  - Card template structure varied between projects due to incremental manual updates
  - Test assertions hardcoded old card layouts without accounting for label changes
tags:
  - css
  - styling
  - consistency
  - test-maintenance
  - layout
resolved: "2026-06-23"
---

> **Audit note (2026-07-13):** this doc records the 2026-06-23 rollout to the then-**9** projects, when the suite had **347** tests. Current state: **11** projects (added `vouch` 2026-07-01, `spar` 2026-07-10) and **381** tests. The "all nine" narrative and the `347` counts below are historical to that date and left as-is; the styling pattern still applies to all cards.

## Problem Summary

The `/now` page's project cards had inconsistent structure across 9 projects. The new "next up → roadmap features" layout was applied to The Fantastic Leagues first, but then needed distribution across the remaining 8 projects (Aleph, Judge Tool, Tastemakers, Bahtzang Trader, jameschang.co, Thirsty Pig, KTV Singer, TableDrop).

Additionally, the `.nb-proj-roadmap-label` CSS styling was initially created with custom properties that didn't match the adjacent "next up" label, causing visual inconsistency despite identical semantic intent.

### Symptoms Observed

1. Only The Fantastic Leagues displayed the full structure: description → next up → roadmap features
2. Other projects still had the old structure (description → roadmap → next up), if they had roadmaps at all
3. The roadmap label appeared subtly different from the "next up" label (different font weight, letter-spacing, color)
4. Test assertions expected old card counts and membership structures

## Root Cause Analysis

### Why `replace_all: true` Failed

Using `replace_all: true` on Edit operations only matches the exact string being replaced. For structural HTML changes where each project has slightly different content, unique strings appear in only one project (The Fantastic Leagues), so the operation was effective there but left 8 projects unchanged.

The challenge: each project card has unique text (project name, description, next_up value, roadmap items), making their HTML unique. A blanket find-and-replace doesn't work for structure changes across multiple similar blocks.

### CSS Specificity Drift

The initial `.nb-proj-roadmap-label` styling used:
- `font-weight: 700` (vs. `.nb-proj-next-label` at 600)
- `letter-spacing: 0.08em` (vs. 0.5px on next-up)
- `color: var(--dim)` (vs. `var(--ink)` on next-up)

Even though both are uppercase, 10px monospace, the visual weight differs noticeably.

### Test Assertion Stagnation

Print stylesheet tests expected:
- Print name: `"James Chang"` (but now `"James Chang, MBA"` after resume update)
- Minor memberships: 3 items (but now 6 after marking USC Alumni and Aquarium as "former")

These assertions weren't updated when the intentional changes were made to `index.html`, causing E2E test failures.

## Working Solution

### HTML Structure (in `/now/index.html`)

All 9 project cards were updated to follow this consistent structure:

```html
<article class="nb-proj-card">
  <div class="nb-proj-head">
    <div class="nb-proj-title">
      <h3 class="nb-proj-name"><a href="...">Project Name</a></h3>
      <span class="nb-proj-domain">domain.com &#8599;</span>
    </div>
    <span class="nb-proj-badge nb-proj-badge--shipping">
      Shipping &middot; Beta
    </span>
  </div>
  <!-- TLDR-{slug}-START -->
  <div class="nb-proj-activity">
    <span class="nb-proj-activity-label">&#8593; shipped</span>
    <div class="nb-proj-activity-body">
      <a href="...">Last commit message</a>
      &middot; <time datetime="..." data-rel>Xd ago</time>
    </div>
  </div>
  <p class="nb-proj-desc">One-sentence project overview.</p>
  <p class="nb-proj-next">
    <span class="nb-proj-next-label">next up</span>
    Editorial priority from projects-config.json
  </p>
  <div class="nb-proj-roadmap">
    <p class="nb-proj-roadmap-label">upcoming roadmap features</p>
    <ul>
      <li>Roadmap item 1</li>
      <li>Roadmap item 2</li>
      <li>Roadmap item 3</li>
    </ul>
  </div>
  <p class="feed-updated">Auto-updated ... via GitHub events.</p>
  <!-- TLDR-{slug}-END -->
</article>
```

### CSS Implementation (in `/notebook.css`)

The `.nb-proj-roadmap-label` class was corrected to **exactly match** `.nb-proj-next-label` styling:

```css
.nb-proj-next-label {
  font-family: var(--mono);
  font-weight: 600;
  color: var(--ink);
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.5px;
}

.nb-proj-roadmap-label {
  font-family: var(--mono);
  font-weight: 600;
  color: var(--ink);
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.5px;
  margin: 0 0 6px 0;
  display: block;
}
```

**Key CSS properties and rationale:**

| Property | Value | Purpose |
|----------|-------|---------|
| `font-family` | `var(--mono)` | Geist Mono for small-caps labels; consistent with all UI labels |
| `font-weight` | 600 | Bold emphasis without too-heavy appearance |
| `color` | `var(--ink)` | Primary text color; inherits light/dark mode automatically |
| `font-size` | 10px | Same size as "next up" label for visual parity |
| `letter-spacing` | 0.5px | **Critical detail**: exact 0.5px spacing (not 0.08em) to match next-up label |
| `text-transform` | uppercase | Uppercase rendering for scannable labels |
| `margin` | 0 0 6px 0 | Space above and below label |
| `display` | block | Separate from list; prevents inline wrapping |

The roadmap list styling (unchanged):

```css
.nb-proj-roadmap ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nb-proj-roadmap li {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--dim);
  padding-left: 12px;
  position: relative;
}

.nb-proj-roadmap li:before {
  content: '·';
  position: absolute;
  left: 0;
  color: var(--accent);
}
```

### Data Source & Architecture

**Roadmaps are hand-curated**, not fetched from config or generated by cron:

- The **activity block** (shipped commit) is generated live by `bin/update-projects.py` from GitHub events
- The **description** and **next_up** come from `bin/projects-config.json`
- The **roadmap items** are manually edited directly in `/now/index.html` between `<!-- TLDR-{slug}-START -->` markers

This split allows editorial control without requiring a new config field or sync logic. The `next_up` field was already stored in config; roadmaps just needed to be added to all 9 projects' HTML sections.

### Test Updates (in `tests/test_site_e2e.py`)

Two assertions were updated to match intentional changes:

**Before:**
```python
assert '<h1 class="print-name">James Chang</h1>' in body
assert count == 3, "expected 3 nb-membership--minor articles"
assert minor_count == 3, "expected all 3 minor cards inside .nb-grid-3"
```

**After:**
```python
assert '<h1 class="print-name">James Chang, MBA</h1>' in body
assert count == 6, "expected 6 nb-membership--minor articles (incl. former memberships)"
assert minor_count == 6, "expected all 6 minor cards inside .nb-grid-3"
```

The print name was updated to include ", MBA" for the resume PDF. The membership count increased from 3 to 6 because USC Alumni Club of Shanghai and Aquarium of the Pacific were marked as "former memberships" (still visible on the page, but with `nb-membership--minor` class applied).

## Implementation Steps

1. **Updated each of 8 projects individually** (Judge Tool, Aleph, Tastemakers, Bahtzang Trader, jameschang.co, Thirsty Pig, KTV Singer, TableDrop) by moving the roadmap `<div>` before the `<p class="nb-proj-next">` block

2. **Added the `.nb-proj-roadmap-label` class** to the HTML with text "upcoming roadmap features"

3. **Created CSS for `.nb-proj-roadmap-label`** (initial version with custom styling)

4. **Discovered letter-spacing mismatch** during visual inspection and corrected it to match "next up" label exactly

5. **Updated test assertions** in `test_site_e2e.py` to expect new counts and print name format

6. **Regenerated `resume.pdf`** to confirm print stylesheet changes

7. **All 347 tests pass** after corrections

## How to Verify It Works

### Visual Inspection
```bash
python3 -m http.server 8787 &
# Open http://localhost:8787/now/
# Verify each of 9 projects displays:
# - Activity block
# - Description
# - "Next up" label + text
# - "upcoming roadmap features" label + 3-item list
```

### Light & Dark Mode
1. Toggle theme button (☾/☀ in top-right nav)
2. Verify labels maintain the same letter-spacing
3. Verify color tokens update correctly

### Print Stylesheet
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=/tmp/verify.pdf http://127.0.0.1:8787/
# Open /tmp/verify.pdf and verify:
# - "James Chang, MBA" at top
# - All 6 education items visible
```

### Run Test Suite
```bash
python3 -m pytest tests/test_site_e2e.py -v
# All 347 tests should pass, including:
# - TestPrintStylesheet::test_print_name_block_only_on_homepage
# - TestMinorMemberships::test_exactly_three_minor_membership_articles
# - TestMinorMemberships::test_minor_cards_are_inside_grid_wrapper
```

## Prevention Strategies

### 1. Search-and-Replace Pitfalls

When updating a pattern across multiple similar blocks, `replace_all: true` only works if the string is unique. For structural changes:

```bash
# Count instances before/after
BEFORE=$(grep -c "pattern" file.html)
# Make changes
AFTER=$(grep -c "pattern" file.html)
[ "$BEFORE" -eq "$AFTER" ] || echo "Mismatch detected"
```

**Prevention:** For component-wide changes, either (a) use cron/Python to generate all instances uniformly, or (b) manually verify all N instances after editing.

### 2. CSS Consistency Checks

Find orphaned or inconsistent selectors:

```bash
# Are there CSS rules for classes that don't exist in HTML?
grep -o '\.[a-z-]*' notebook.css | sort -u | while read cls; do
  grep -q "$cls" now/index.html || echo "ORPHAN: $cls"
done

# Verify all instances use consistent CSS tokens (not hardcoded colors)
grep "\.nb-proj-roadmap-label" notebook.css | grep "color:"
```

### 3. Test Maintenance: When to Update

**Update test assertions when the change is intentional:**
- Resume PDF got a new name format? Update the assertion.
- Membership list expanded? Update the expected count.

**Investigate when tests fail unexpectedly:**
- Run the cron locally: `python3 bin/update-projects.py --dry-run`
- Check git history: `git log -p --follow -S "pattern" -- file.html`
- Compare rendered output with hand-edited HTML

### 4. Visual Regression Testing

For label/typography consistency, add a visual test:

```python
def test_next_up_and_roadmap_labels_match_visually(self):
    """Both labels should render with identical font weight, spacing, and color."""
    _, body = fetch("now/index.html")
    # Extract computed styles via headless browser (Playwright)
    # Assert both .nb-proj-next-label and .nb-proj-roadmap-label
    # have the same font-weight, letter-spacing, and color
```

### 5. Spot-Check Pattern for Future Updates

When updating all 9 projects:
1. Grep with line numbers: `grep -n "pattern" file.html`
2. Extract parent-class variants: `grep -B1 "pattern" file.html | grep "class=" | sort -u`
3. If >1 variant, investigate — one should be the canonical structure
4. Verify counts: `grep -c "nb-proj-card" now/index.html` → should be 9

## Related Documentation

- [[css-dark-mode-dual-selector-consistency]] — Dual-selector CSS patterns for light/dark mode consistency
- [[print-stylesheet-project-card-layout-line-wrapping]] — Print stylesheet specificity issues affecting project cards
- [[wcag-contrast-light-mode-accent-muted]] — WCAG AA contrast audits and token validation
- [[static-site-branding-sweep-four-pitfalls]] — Cross-site consistency patterns in CSS refactoring
- CLAUDE.md § "CSS token system" — Design token reference and naming conventions
- CLAUDE.md § "Testing" — Test file locations and E2E patterns

## Files Modified

- `/Users/jameschang/Projects/jameschang.co/now/index.html` — Reordered sections for all 9 projects
- `/Users/jameschang/Projects/jameschang.co/notebook.css` — Added `.nb-proj-roadmap-label` styling
- `/Users/jameschang/Projects/jameschang.co/tests/test_site_e2e.py` — Updated 3 assertions
- `/Users/jameschang/Projects/jameschang.co/resume.pdf` — Regenerated

## Timeline

| Date | Action |
|------|--------|
| 2026-06-23 10:15 | Identified inconsistency: only FL had new structure |
| 2026-06-23 10:30 | Attempted `replace_all: true` — only affected FL |
| 2026-06-23 10:45 | Manually updated remaining 8 projects |
| 2026-06-23 11:00 | Added `.nb-proj-roadmap-label` CSS (initial, custom styling) |
| 2026-06-23 11:15 | Discovered letter-spacing mismatch via visual inspection |
| 2026-06-23 11:20 | Corrected CSS to match `.nb-proj-next-label` exactly |
| 2026-06-23 11:30 | Updated test assertions (print name, membership counts) |
| 2026-06-23 11:45 | All 347 tests pass ✓ |
| 2026-06-23 12:00 | Documentation complete |
