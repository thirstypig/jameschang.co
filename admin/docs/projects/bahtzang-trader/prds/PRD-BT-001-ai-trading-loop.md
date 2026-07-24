---
id: PRD-BT-001
type: prd
project: bahtzang-trader
status: active
owner: james
tags: [ai]
links: []
updated: 2026-07-23
---
<!-- Retroactive, PUBLIC-SAFE. [inferred]=public sources · [unknown]=ask James ·
     [intended]=plausibly deliberate. No private internals. -->

# Bahtzang Trader — AI trading decision loop

## 1. Problem statement
[inferred] Can an LLM make disciplined, repeatable trading calls under real market
conditions? There's no safe, honest way to find out without risking money — so this
builds a guard-railed harness to test it on paper first.

## 2. Strategic rationale
[intended] The bet (portfolio board): *"a learning experiment with real guardrails,
not a product yet."* The value is the discipline and the harness, not the P&L.

## 3. User story
[inferred] As the operator, I want Claude to issue buy/sell/hold calls against a
paper account under fixed rules so that I can evaluate the strategy before any real
capital is at stake.

## 4. Hypothesis / assumptions
- [intended] An LLM + explicit guardrails can trade with discipline a human might lack.
- [unknown] The actual gate criteria that would justify going live. **← confirm.**

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] paper P&L vs. a benchmark, rule adherence, drawdown.
- (b) TODAY: [unknown] — what's tracked across the paper trades? **← confirm.**

## 6. Technical notes
[inferred] Executes against a paper-trading brokerage account (public: Alpaca). The
decision logic, prompts, and risk rules live in the **private** repo — not reproduced here.

## 7. AI implementation notes
[inferred] Claude drives the calls. [unknown] prompt/decision framework, cost per run — private.

## 8. Testing plan
[unknown] What proves a call obeyed the rules before it's placed? — private.

## 9. Deferred / what we'd do differently
[intended] Live trading is explicitly deferred — gated behind completing the paper
run (portfolio "next up": ~6 more trades) and meeting the (to-be-confirmed) criteria.
This is a PROHIBITED-until-proven boundary, deliberately.
