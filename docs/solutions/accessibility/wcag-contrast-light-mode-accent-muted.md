---
title: "Sub-agent misreported dark-mode contrast as failing; actual failures were light-mode accent and muted colors"
slug: wcag-contrast-light-mode-accent-muted
category: accessibility
tags: [css, wcag, contrast-ratio, dark-mode, light-mode, color-tokens, sub-agent-verification]
severity: moderate
component: "styles.css (CSS token system: --accent, --muted)"
symptom: "Sub-agent reported dark-mode accent colors failing WCAG contrast at ~1:1 ratio; light-mode contrast failures went undetected"
root_cause: "Incorrect sRGB linearization in sub-agent contrast calculation; proper calculation showed dark mode passed AAA (7.6:1). Real failures were light-mode --accent (#b44a3e at 3.4:1) and --muted (#576376 at 3.9:1), both below AA 4.5:1 threshold."
date_solved: 2026-04-16
---

# Sub-agent contrast miscalculation — verify automated WCAG findings

## Problem

During a site performance audit, a sub-agent analyzed color contrast ratios and reported dark-mode accent `#ff8b6d` on `#0f1a2e` as approximately 1:1 — functionally invisible. This triggered a fix for the wrong theme.

## Investigation

Ran the precise WCAG 2.x relative luminance formula in Python to verify:

```python
def srgb_to_linear(c):
    c = c / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4

def luminance(r, g, b):
    return (0.2126 * srgb_to_linear(r) +
            0.7152 * srgb_to_linear(g) +
            0.0722 * srgb_to_linear(b))

def contrast(l1, l2):
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)
```

Results:
- Dark mode `#ff8b6d` on `#0f1a2e`: **7.6:1** (passes AAA) — sub-agent was wrong
- Light mode `#b44a3e` on `#c6cfdd`: **3.4:1** (fails AA) — the real problem
- Light mode `#576376` on `#c6cfdd`: **3.9:1** (fails AA) — also a real problem

## Root cause

Sub-agents and LLMs can hallucinate WCAG ratios because they either skip the sRGB linearization step (treating gamma-encoded values as linear) or estimate ratios from hex-code proximity. Warm colors like `#ff8b6d` have high red channels but moderate luminance — the eye perceives them as bright, but the math disagrees with a naive calculation.

## Solution

Fixed light-mode tokens:
- `--accent`: `#b44a3e` (3.4:1) → `#993524` (4.6:1)
- `--muted`: `#576376` (3.9:1) → `#4a5568` (4.8:1)

Also verified against composited card backgrounds (`rgba(255,255,255,0.55)` over `#c6cfdd`):

```python
def composite(fg, bg, alpha):
    return int(fg * alpha + bg * (1 - alpha))
```

Both new tokens pass AA on both `--bg` and `--card-bg` surfaces.

## Prevention

1. **Never trust automated contrast findings at face value.** Always re-derive with the three-function formula above when a ratio looks suspicious.
2. **Check both themes.** Dark mode getting the attention doesn't mean light mode is fine.
3. **Check composited backgrounds.** `rgba()` card surfaces produce effective backgrounds different from either the foreground or parent alone.
4. **Document the baseline.** CLAUDE.md now records the verified contrast ratios and the formula for re-checking.
