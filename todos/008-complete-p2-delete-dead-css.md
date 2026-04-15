---
status: pending
priority: p2
issue_id: 008
tags: [code-review, simplicity, css]
dependencies: []
---

# Delete ~50 lines of dead CSS (`.display`, `.community`, `.proof*`, dead print selector)

## Problem Statement

Several CSS rules remain in `styles.css` from earlier iterations that no HTML markup references. Dead code accrues interest (confuses future-you scrolling for the right selector).

## Findings

From code-simplicity-reviewer agent + performance-oracle agent (both flagged same items):

1. **`.display` bare selector** (`styles.css:190`, and print `.display` block at `:594-600`) — only `.display-tagline` is used. Old hero headline class that was renamed.
2. **`.community`** (`styles.css:541`) — zero HTML references. Ghost of an earlier footer iteration.
3. **`.proof` / `.proof-item` / `.proof-number` / `.proof-label`** (`styles.css:258-284` web + `:643-650` print) — the hero proof strip was removed; CSS left behind.
4. **`.hero-ctas + * a[href^="http"]::after`** (`styles.css:722`) — dead selector in print block; `.hero-ctas` itself is `display:none` in print, so any descendant is moot.
5. **`.timeline .t-body { }`** (`work/work.css:399`) — empty rule declaration.

## Proposed Solutions

### Option A (Recommended): Delete all 5
- Single PR/commit; no visual change, no behavior change
- ~50 LOC removed, ~1 KB raw / ~250 B gzipped saved
- **Effort:** Small (~10 min)
- **Risk:** Near-zero (grep confirmed no HTML references)

### Option B: Leave until migration
- CSS bloat is small; no active harm
- **Effort:** None • **Cons:** compound interest on cruft

## Technical Details

Target files:
- `/Users/jameschang/Projects/jameschang.co/styles.css`
- `/Users/jameschang/Projects/jameschang.co/work/work.css`

Verification before deletion:
```bash
grep -r 'class="[^"]*display[^-]' --include="*.html" .  # confirm zero matches for bare .display
grep -r 'class="[^"]*community' --include="*.html" .    # zero matches expected
grep -r 'class="[^"]*proof' --include="*.html" .        # zero matches expected
```

## Acceptance Criteria

- [ ] `.display` removed from combined selectors and standalone print rules
- [ ] `.community` deleted
- [ ] All `.proof*` blocks deleted (web + print)
- [ ] `.hero-ctas + *` half of print selector removed (keep footer half)
- [ ] `.t-body { }` empty rule deleted
- [ ] Site renders identically before/after (visual spot check)
- [ ] Lighthouse score unchanged or improved

## Work Log

_(blank)_

## Resources

- Simplicity review output (P1.1–P1.4, P3.1)
- Performance review output (P2 finding on dead CSS)
