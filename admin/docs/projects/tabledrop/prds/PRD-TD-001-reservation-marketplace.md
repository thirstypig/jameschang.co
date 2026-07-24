---
id: PRD-TD-001
type: prd
project: tabledrop
status: active
owner: james
tags: [payments]
links: []
updated: 2026-07-23
---
<!-- Retroactive, PUBLIC-SAFE. [inferred]/[unknown]/[intended]. No private internals. -->

# TableDrop — reservation marketplace

## 1. Problem statement
[inferred] Some Taipei restaurants are effectively impossible to book — demand far
exceeds a fair way to get a table. A marketplace could match scarce reservations to
people willing to pay for them.

## 2. Strategic rationale
[intended] The bet (portfolio board): *"hard-to-get Taipei reservations, turned into a
marketplace with a real storefront."* A concrete scarcity + a real payment loop.

## 3. User story
[inferred] As a diner, I want to buy a confirmed reservation at a hard-to-book Taipei
restaurant so that I can get a table I otherwise couldn't.

## 4. Hypothesis / assumptions
- [intended] There's willingness-to-pay for scarce reservations, and supply can be sourced.
- [unknown] The supply side — how reservations are legitimately obtained/fulfilled, and
  whether that's durable. **← confirm; this is the crux.**

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] completed listing→purchase flows, fill rate, GMV.
- (b) TODAY: [unknown] — pre-first-working-loop. **← confirm.**

## 6. Technical notes
[inferred] A storefront with payments (public: Stripe) plus a sourcing/scraper layer.
Internals are in the **private** repo — not reproduced here.

## 7. AI implementation notes
[unknown] Any AI in sourcing/matching? — private, if present.

## 8. Testing plan
[unknown] End-to-end booking/payment coverage — private.

## 9. Deferred / what we'd do differently
[intended] Furthest from a working loop (portfolio note). The honest next step is ONE
listing→purchase flow end to end (portfolio "next up") before any breadth.
