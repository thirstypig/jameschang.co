---
id: PRD-TIP-001
type: prd
project: tip
status: draft
owner: james
tags: [ai, voice]
links: [DOC-TIP-ROADMAP]
updated: 2026-08-04
---
<!-- Retroactive, PUBLIC-SAFE, PRE-LAUNCH. [inferred]/[unknown]/[intended]. -->

# TIP — voice rehearsal + coached debrief

> **Renamed.** Shipped as **Spar** through July 2026, now **TIP**. This doc was
> `PRD-SPAR-001`; that ID is retired, not reused.

## 1. Problem statement
[inferred] People face hard conversations (feedback, conflict, bad news) with no safe
way to practice. Reading about it doesn't build the muscle; you only get one live shot,
on a real person, with real consequences.

## 2. Strategic rationale
[intended] The bet (portfolio board): people will rehearse a dreaded conversation out
loud against an AI that pushes back — and the *scored debrief afterward*, not the
conversation itself, is what brings them back.

## 3. User story
[inferred] As someone dreading a specific conversation, I want to rehearse it out loud
against an AI counterpart and then be told which moves worked, so that I go into the
real one prepared.

## 4. Hypothesis / assumptions
- [intended] Voice rehearsal + a coached debrief changes real-world behavior more than
  reading advice.
- ~~[unknown] Whether the voice experience feels real enough to matter.~~ **Resolved
  2026-08 [inferred]:** the live voice session, the scored debrief, and a persona
  builder all shipped, and the roadmap moved on to accounts — so this gate was cleared
  in practice. Whether it holds up with users outside the author is still [unknown].
- [unknown] Whether a score people can watch move is the retention mechanic it's
  designed to be. **← confirm post-launch.**

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] completed rehearsals, debrief engagement, repeat use
  before real conversations, and score movement across sessions.
- (b) TODAY: [unknown] — pre-launch, deployed behind a gate. **← confirm.**

## 6. Technical notes
[inferred] A voice app (public: tip.bahtzang.com; uses a hosted voice platform).
Model/prompt/voice-pipeline internals live in the **private** `thirstypig/TIP` repo and
are not reproduced here.

## 7. AI implementation notes
[inferred] LLM-driven counterpart + coaching, with the debrief graded against a named
four-move framework rather than free-form feedback. [unknown] models, prompt strategy,
and per-session cost — private. (Voice + LLM per session is likely the main cost driver.)

## 8. Testing plan
[unknown] How the coaching score is validated against real outcomes — private.

## 9. Deferred / what we'd do differently
[intended] The sequencing held: prove the core voice loop, then the debrief, then
personas — all before building surrounding UI. The current risk is different in kind —
the launch cluster (accounts → saved sessions → score trend → pattern insights) is a
strict dependency chain, so the failure mode is starting those out of order rather than
building the wrong thing.
