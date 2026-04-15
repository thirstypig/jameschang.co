---
status: pending
priority: p3
issue_id: 017
tags: [code-review, polish, agent-native, simplicity]
dependencies: []
---

# Miscellaneous small polish items from the 4-agent review

## Problem Statement

A handful of small, low-impact findings that don't justify their own todo but are worth batching into a "polish pass" commit.

## Findings

### From agent-native-reviewer:
1. **P1-C** — "seven products" (llms.txt) vs "six other products" (index.html:168,361) — all correct arithmetically (6+Aleph=7) but could confuse string-comparing agents. Fix: add parenthetical "(plus Aleph = seven total)" once, or normalize all to one number.
2. **P3-C** — sub-page `<title>` tags don't include "Senior Product Manager" — agent searching by role misses them. Could append " · James Chang" → " · Senior PM · James Chang".
3. **P3-E** — AI Insights architecture ASCII diagram is in `<div class="arch-block">` — would semantically prefer `<pre>` to preserve whitespace intent.
4. **P3-F** — `<h3 class="certs-heading">` under `<section class="education">` — minor heading-hierarchy nit. Could become `<h4>` under degree, or its own `<section>` with `<h2>`.

### From performance-oracle:
5. **P2 finding (not P1)** — inline `script.js` into `<head>` or end of `<body>` as a `<script>` block. Saves 1 RTT on cold load (~30–80 ms mobile). Tradeoff: loses cross-page cache.
6. **P3 .DS_Store note** — `.DS_Store` gitignored but on disk. Not tracked. No action needed; just watch out on future `git add -A`.

### From security-sentinel:
7. **P3-9** — add `<meta name="referrer" content="strict-origin-when-cross-origin">`. Minor hardening.

## Proposed Solutions

### Option A: Batch fix all 7 items in one polish commit
- **Effort:** Small (~30 min total)
- **Pros:** clean sweep
- **Cons:** some items (like #4, #5) arguably YAGNI for a personal site

### Option B: Cherry-pick 2–3 items
- Pick highest-signal ones (normalize product count, add referrer-policy, change arch-block to `<pre>`)
- Skip the marginal ones (heading hierarchy, script inlining)
- **Recommended**

### Option C: Leave as-is
- None of these are affecting functionality
- **Effort:** None

## Technical Details

Recommended items to actually fix:
1. **Product count normalization** — update `llms.txt` line 7 OR `index.html:168,361` to match
2. **Referrer-Policy meta** — append to every HTML `<head>` (can combine with todo #006 CSP injection)
3. **Change arch-block div → pre** in `/work/fantastic-leagues/ai-insights/` (line ~491)

Files:
- `/Users/jameschang/Projects/jameschang.co/llms.txt:7`
- `/Users/jameschang/Projects/jameschang.co/index.html:168, 361`
- `/Users/jameschang/Projects/jameschang.co/work/fantastic-leagues/ai-insights/index.html:491`
- All HTML files (referrer-policy meta — bundle with CSP work)

## Acceptance Criteria

- [ ] `llms.txt` and `index.html` use consistent phrasing for product count
- [ ] `<meta name="referrer">` present on all pages
- [ ] Architecture diagram wrapped in `<pre>` tag for semantic correctness

## Work Log

_(blank)_

## Resources

- Multi-agent review output from 2026-04-14
