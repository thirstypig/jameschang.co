---
id: PRD-FL-001
type: prd
project: fantastic-leagues
status: active
owner: james
tags: [ai, integration]
links: []
updated: 2026-07-23
---
<!-- Retroactive, PUBLIC-SAFE reconstruction from the live product + public roadmap
     (/projects/fantastic-leagues/roadmap/) + the portfolio board. Claims tagged:
     [inferred] = read from public sources · [unknown] = ASK JAMES · [intended] =
     plausibly deliberate. No private internals. -->

# Fantastic Leagues — AI-assisted analysis

## 1. Problem statement
[inferred] Serious keeper-league managers want deeper, faster analysis than the big
fantasy platforms give — projections, matchup/trade reads, in-season decisions — and
the mass-market tools optimize for casual players, not the hardcore.

## 2. Strategic rationale
[intended] The bet (portfolio board): *"serious keeper leagues are underserved by the
big platforms — go deep for the hardcore, not wide for casuals."* AI analysis is the
wedge that a two-person operation can offer that the incumbents won't bother to.

## 3. User story
[inferred] As a keeper-league manager, I want AI-assisted reads on my roster and moves
so that I make better in-season and trade decisions without doing the analysis by hand.

## 4. Hypothesis / assumptions
- [intended] Hardcore managers will pay for depth the free platforms don't offer.
- [unknown] Which specific AI outputs actually change a manager's decision (and get
  used weekly) vs. which are nice-to-look-at. **← James to confirm from usage.**

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] weekly active managers, AI-feature engagement,
  free→paid conversion, retention across a season.
- (b) TODAY: [unknown] — is any of this instrumented? **← confirm.**

## 6. Technical notes
[inferred] AI features are powered by LLMs (public: the product uses Gemini + Claude).
Detailed architecture/prompts/costs live in the **private** `TheFantasticLeagues` repo
and are intentionally NOT reproduced on this public hub.

## 7. AI implementation notes
[inferred] Multi-model (Gemini + Claude). [unknown] model routing, prompt strategy, and
per-call cost — private; fill in the product's own repo, not here.

## 8. Testing plan
[unknown] What guards the AI outputs (accuracy, hallucination, cost caps)? — private.

## 9. Deferred / what we'd do differently
[unknown] Hindsight — reserved. Public roadmap shows the forward path (FanGraphs/Statcast
data, scoring-format expansion, a pre-trade AI advisor).
