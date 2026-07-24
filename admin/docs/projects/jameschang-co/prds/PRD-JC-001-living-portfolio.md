---
id: PRD-JC-001
type: prd
project: jameschang-co
status: active
owner: james
tags: [integration, ai]
links: []
updated: 2026-07-23
---
<!-- Retroactive. This IS the public repo — so most claims are [inferred] from the
     code right here, and can be concrete. [unknown]=intent/metrics only James knows. -->

# jameschang.co — the self-updating living portfolio

## 1. Problem statement
[inferred] A static résumé site goes stale the day it ships. A portfolio meant to prove
an "AI-assisted operator" can build and ship should itself demonstrate that — by staying
current on its own.

## 2. Strategic rationale
[intended] The bet (portfolio board): *"prove the thesis by simply existing and updating
itself."* Every feature here is also a demonstration; the site is the argument.

## 3. User story
[inferred] As a visitor, I want to see what James is actually doing right now (health,
music, reading, projects shipping) so that the portfolio reads as alive, not archival.

## 4. Hypothesis / assumptions
- [intended] A self-updating /now page signals "operator who ships" better than prose.
- [unknown] Whether visitors (recruiters, partners) actually value the /now feeds vs.
  the case studies. **← confirm.**

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] which sections visitors engage with, résumé downloads.
- (b) TODAY: [inferred] GA4 is installed (measurement ID in the head); specific funnels
  [unknown]. **← confirm what you actually watch.**

## 6. Technical notes
[inferred] Plain HTML/CSS/JS on GitHub Pages, no build step; 8 cron-synced feeds +
per-project cards on /now; Python `bin/*.py` sync scripts; ~78 KB page weight,
Lighthouse 100s. (This is the public repo — full detail is in CLAUDE.md.)

## 7. AI implementation notes
[intended] The whole site is "AI-assisted engineering" — built with Claude Code et al.
No runtime AI feature; the AI is in the building, not the product.

## 8. Testing plan
[inferred] 427 tests (unit + E2E) with CI on every push — the most-tested project in
the portfolio, by far.

## 9. Deferred / what we'd do differently
[inferred] Ongoing meta-project. Recent adds: the /admin area + this docs hub. Risk is
over-building the site vs. the products it's meant to showcase — keep it current,
resist scope creep (portfolio "next up": keep shipping, keep résumé in sync).
