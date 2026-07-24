---
id: PRD-JC-004
type: prd
project: jameschang-co
status: draft
stage: planned
owner: james
tags: [ui-ux]
links: [PRD-JC-003]
updated: 2026-07-24
---

# jameschang.co — PM review cockpit

## 1. Problem statement
[inferred] The docs hub is a library — you read one doc at a time. There's no view that
answers the PM's actual question: *"across all my projects, what needs my decision?"*
Open questions, launch blockers, and risks are scattered and invisible.

## 2. Strategic rationale
[intended] Turn the docs from storage into a cockpit: one generated rollup — a "PM
conference" view — showing every project's MVP→shipped→planned features, open decisions,
blockers, risks, and PRD maturity.

## 3. User story
[inferred] As the operator, I want one page that surfaces every open decision and blocker
across the portfolio so I run reviews from it instead of opening 38 docs.

## 4. Hypothesis / assumptions
- [intended] Aggregating the signals already in the docs ([unknown], unchecked [ ],
  RISK-###, stage, status) is enough — no new data entry.

## 5. Impact & KPIs
- (a) SHOULD measure: does it become the weekly-review starting point?
- (b) TODAY: being built now.

## 6. Technical notes
[intended] refresh-docs.py generates a pm-review doc from a scan of all docs; the docs
board shows it as the landing view.

## 7. AI implementation notes
n/a.

## 8. Testing plan
[intended] Unit-test the rollup extraction (unknown counts, blockers, stage grouping).

## 9. Deferred / what we'd do differently
[intended] Start read-only (generated). A future version could let you resolve a decision
inline. Once shipped, this PRD flips stage planned → shipped.
