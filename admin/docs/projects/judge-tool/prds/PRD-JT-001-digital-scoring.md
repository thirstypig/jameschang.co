---
id: PRD-JT-001
type: prd
project: judge-tool
status: active
owner: james
tags: [ui-ux]
links: []
updated: 2026-07-23
---
<!-- Retroactive, PUBLIC-SAFE. Security/internal detail is deliberately excluded —
     see the private repo. [inferred]/[unknown]/[intended] tags throughout. -->

# The Judge Tool — digital competition scoring

## 1. Problem statement
[inferred] KCBS BBQ competitions score on paper — clipboards and carbon copies — which
is slow, error-prone, and hard to tabulate live. Judges and organizers want something
that just works at the table.

## 2. Strategic rationale
[intended] The bet (portfolio board): *"replace clipboards and carbon copies with
something judges actually prefer."* A narrow, real, underserved workflow.

## 3. User story
[inferred] As a judge, I want to enter scores on a device at the table so that results
tabulate instantly and correctly, without paper.

## 4. Hypothesis / assumptions
- [intended] Organizers will adopt if it's clearly better than paper at a live event.
- [unknown] The real blocker to adoption — trust, hardware, connectivity? **← confirm.**

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] competitions run on it, judge error rate vs. paper,
  time-to-final-results.
- (b) TODAY: [unknown] — instrumented? Product is pre-validation. **← confirm.**

## 6. Technical notes
[inferred] A web app judges use at the table; results tabulate server-side. Security
posture, routes, and stack are in the **private** repo — NOT reproduced here (that
detail is exactly what the public roadmap-filtering work kept off the public site).

## 7. AI implementation notes
n/a — [inferred] no AI in the core scoring flow.

## 8. Testing plan
[unknown] Coverage of the scoring/tabulation flows — private.

## 9. Deferred / what we'd do differently
[intended] Blocked on external validation, not code (portfolio "next up": stakeholder
testing). The honest next move is organizer time, not more features. Public roadmap:
[/projects/judge-tool/roadmap/](/projects/judge-tool/roadmap/).
