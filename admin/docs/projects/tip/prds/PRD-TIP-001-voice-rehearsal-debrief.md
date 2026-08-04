---
id: PRD-SPAR-001
type: prd
project: spar
status: draft
owner: james
tags: [ai, voice]
links: []
updated: 2026-07-23
---
<!-- Retroactive, PUBLIC-SAFE, PRE-LAUNCH. [inferred]/[unknown]/[intended]. -->

# Spar — voice rehearsal + coached debrief

## 1. Problem statement
[inferred] Leaders face hard conversations (feedback, conflict, bad news) with no safe
way to practice. Reading about it doesn't build the muscle; you only get one live shot.

## 2. Strategic rationale
[intended] The bet (portfolio board): *"rehearse difficult conversations against an AI
counterpart, then get a coached debrief on how you handled it."* The real product is
the debrief, not the chat.

## 3. User story
[inferred] As a leader, I want to rehearse a specific hard conversation out loud against
an AI counterpart and then get coached feedback so that I go into the real one prepared.

## 4. Hypothesis / assumptions
- [intended] Voice rehearsal + a coached debrief changes real-world behavior more than
  reading advice.
- [unknown] Whether the voice experience feels real enough to matter — the gating
  question (portfolio "next up"). **← confirm.**

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] completed rehearsals, debrief engagement, self-reported
  readiness, repeat use before real conversations.
- (b) TODAY: [unknown] — pre-launch. **← confirm.**

## 6. Technical notes
[inferred] A voice app (public: staging at spar.bahtzang.com; uses a voice platform —
Retell). Model/prompt/voice-pipeline internals are in the **private** `thirstypig/spar`
repo — not reproduced here.

## 7. AI implementation notes
[inferred] LLM-driven counterpart + coaching; [unknown] models, prompt strategy, and
per-session cost — private. (Voice + LLM per session is likely the main cost driver.)

## 8. Testing plan
[unknown] How is "feels real" evaluated? — private.

## 9. Deferred / what we'd do differently
[intended] Right sequencing: prove the core voice experience feels real BEFORE building
UI around it (portfolio "next up"). The coaching debrief — the actual product — comes
after the conversation loop lands.
