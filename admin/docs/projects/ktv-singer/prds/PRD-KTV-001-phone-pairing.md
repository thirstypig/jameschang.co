---
id: PRD-KTV-001
type: prd
project: ktv-singer
status: active
owner: james
tags: [ui-ux, mobile]
links: []
updated: 2026-07-23
---
<!-- Retroactive, PUBLIC-SAFE. [inferred]/[unknown]/[intended]. No private internals. -->

# KTV Singer — phone-as-remote pairing + queue

## 1. Problem statement
[inferred] Home karaoke is clunky — picking songs and managing a queue on a TV is
awkward, and everyone wants to add songs from their own phone without fuss.

## 2. Strategic rationale
[intended] The bet (portfolio board): *"home karaoke that just works — phones as
remotes, no fuss."* The whole product lives or dies on the pairing being effortless.

## 3. User story
[inferred] As a guest, I want to add and control songs from my phone on the shared TV
so that everyone participates without passing a remote around.

## 4. Hypothesis / assumptions
- [intended] Effortless phone→TV pairing is the make-or-break; song features are secondary.
- [unknown] The specific failure modes that break "effortless" today. **← confirm.**

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] successful pairings without help, songs queued per session,
  drop-offs during setup.
- (b) TODAY: [unknown] — pre-reliability. **← confirm.**

## 6. Technical notes
[inferred] Phones pair with an Apple TV app; the song list is YouTube-backed (public:
real-time pairing over Socket.IO). App/server internals are in the **private** repos —
not reproduced here.

## 7. AI implementation notes
[inferred] "AI-assisted" per the portfolio; [unknown] where AI actually appears — private.

## 8. Testing plan
[unknown] What proves pairing is friend-proof? — private.

## 9. Deferred / what we'd do differently
[intended] BLOCKED on reliability (portfolio note): pairing has to be friend-proof
before showing anyone. Nail the connection before adding song-search features
(portfolio "next up").
