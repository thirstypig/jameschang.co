---
id: PRD-VOUCH-001
type: prd
project: vouch
status: draft
owner: james
tags: [compliance, payments]
links: []
updated: 2026-07-23
---
<!-- Retroactive, PUBLIC-SAFE, and PRE-LAUNCH — more [unknown] than most, which is
     correct. Handles MINORS → privacy is load-bearing (see the privacy doc when built). -->

# Vouch — the trust loop (students · mentors · supporters)

## 1. Problem statement
[inferred] Young people with a change they want to make lack both credible backing and a
safe way to be seen and supported by adults who aren't already in their circle.

## 2. Strategic rationale
[intended] The bet (portfolio board): *"students share the change they want to make,
mentors vouch, supporters back them — trust and safety first, built for minors."* The
differentiator and the hardest part are the same thing: safety.

## 3. User story
[inferred] As a student, I want to share my goal and have a mentor vouch for me so that
supporters can back me — inside a moderated, safe space.

## 4. Hypothesis / assumptions
- [intended] A trust chain (mentor vouch) unlocks support that raw crowdfunding can't.
- [unknown] Whether the safety model can satisfy the bar for a minor-facing product AND
  stay usable. **← this is the whole game; confirm.**

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] verified vouches, safe interactions, funds routed to
  students, and above all safety-incident rate (target: zero).
- (b) TODAY: [unknown] — pre-launch, not yet live. **← confirm.**

## 6. Technical notes
[inferred] Pre-launch; moderated-by-default, safety-first for minors. Payments via
Stripe (currently test mode per portfolio "next up"). Internals in the **private**
`thirstypig/vouch` repo — not reproduced here.

## 7. AI implementation notes
[unknown] Any AI in moderation/safety? — private, if present. (If used for minor-safety,
this deserves its own careful review.)

## 8. Testing plan
[unknown] Safety/moderation coverage is the critical test surface — private.

## 9. Deferred / what we'd do differently
[intended] Earliest stage, most values-driven. Gating work is trust, safety, and real
payments — NOT features (portfolio "next up": parent accounts + live Stripe). Move
carefully given the audience. **Privacy/data-handling for minors is the single most
important doc to write here.**
