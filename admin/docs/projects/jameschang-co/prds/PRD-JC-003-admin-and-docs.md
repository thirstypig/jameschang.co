---
id: PRD-JC-003
type: prd
project: jameschang-co
status: active
stage: shipped
owner: james
tags: [ui-ux, ai]
links: [PRD-JC-001]
updated: 2026-07-24
---

# jameschang.co — internal admin area + docs hub

## 1. Problem statement
[inferred] Managing 11 projects, James had no single private place to see portfolio
status or hold PRDs/roadmaps/decisions — and the sensitive parts can't be public.

## 2. Strategic rationale
[intended] A private-ish operator layer on the public site: a portfolio board (the
operator's read) + a docs hub (PRDs/roadmaps per project) — turning the portfolio site
into a place he can actually run the portfolio from.

## 3. User story
[inferred] As the operator, I want a gated view of every project's status + docs so I can
review the whole portfolio in one place.

## 4. Hypothesis / assumptions
- [intended] Public-safe content only behind a curtain; secrets stay in the private/local track.
- [intended] Same no-build-step stack (Python generates data, thin JS displays it).

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] whether the operator actually uses it weekly.
- (b) TODAY: n/a — internal tool, pre-habit.

## 6. Technical notes
[inferred] Footer login curtain (SHA-256, not real auth) → gated /admin/ portfolio board
+ /admin/docs/ viewer; a Python indexer builds the docs manifest the viewer reads.

## 7. AI implementation notes
[intended] Built entirely AI-assisted; the docs' retroactive PRDs were reconstructed
with honest [intended]/[inferred]/[unknown] tagging.

## 8. Testing plan
[inferred] Login/gate, portfolio schema, and the docs indexer are unit + E2E tested.

## 9. Deferred / what we'd do differently
[inferred] Content is honest scaffolding; the archaeology (filling real PRDs) and the PM
review cockpit are the next steps (PRD-JC-004).
