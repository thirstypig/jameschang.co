---
id: PRD-TM-001
type: prd
project: tastemakers
status: active
owner: james
tags: [mobile, integration]
links: []
updated: 2026-07-23
---
<!-- Retroactive, PUBLIC-SAFE. [inferred]/[unknown]/[intended]. No private internals. -->

# Tastemakers — trust-based dining discovery

## 1. Problem statement
[inferred] Star-rating apps average away taste — you don't know *whose* opinion a
rating reflects. People trust specific friends' picks more than an aggregate score.

## 2. Strategic rationale
[intended] The bet (portfolio board): *"a social layer on dining discovery — who you
trust, not just star ratings."* Differentiates from Yelp/Google on the social graph.

## 3. User story
[inferred] As a diner, I want recommendations from people whose taste I trust so that
I find places I'll actually like, not just popular ones.

## 4. Hypothesis / assumptions
- [intended] Trust-weighted recommendations beat aggregate ratings for real decisions.
- [unknown] Whether the social graph reaches critical mass to be useful. **← confirm.**

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] recommendations acted on, social connections per user,
  retention.
- (b) TODAY: [unknown] — backend is live but clients are paused, so likely not measured
  actively. **← confirm.**

## 6. Technical notes
[inferred] A server backend (public: Laravel on Railway) with iOS/Android clients that
are currently paused. Internals live in the **private** repos — not reproduced here.

## 7. AI implementation notes
[unknown] Any recommendation model? — private, if present.

## 8. Testing plan
[unknown] — private.

## 9. Deferred / what we'd do differently
[intended] Effectively STALLED (portfolio note): backend up, apps paused. The real
decision isn't a feature — it's whether to reignite the clients or let it rest (portfolio
"next up" is a DB migration, i.e. keeping the lights on). Don't leave it half-lit.
