---
id: PRD-JC-MVP
type: prd
project: jameschang-co
status: active
stage: mvp
owner: james
tags: [ui-ux]
links: [PRD-JC-001]
updated: 2026-07-24
---
<!-- MVP reconstruction. This is the public repo, so claims are [inferred] from the
     code + git history and can be concrete. [intended] where a deliberate call. -->

# jameschang.co — static portfolio site (the MVP)

## 1. Problem statement
[inferred] The old builder-based site (Wix/Weebly-style) was dated and high-maintenance.
The minimum needed: a fast, hand-owned single-page portfolio + résumé on free hosting.

## 2. Strategic rationale
[intended] Own the stack (plain HTML/CSS/JS on GitHub Pages, no build step) so it's
cheap, fast, and fully under control — and let the *craft* of it be part of the pitch.

## 3. User story
[inferred] As a visitor (recruiter/partner), I want a fast, credible one-page view of
who James is and his work so that I can size him up in a minute.

## 4. Hypothesis / assumptions
- [intended] A hand-rolled site signals more than a template ever could.
- [intended] Plain HTML is enough — no framework needed for one page of content.

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] résumé downloads, contact clicks.
- (b) TODAY: [inferred] GA4 installed; specific funnels [unknown].

## 6. Technical notes
[inferred] Single-page: hero → experience → education → skills → projects → contact;
résumé.pdf generated from the print stylesheet; dark/light theme toggle. No build step.

## 7. AI implementation notes
[intended] Built AI-assisted (Claude Code et al.); no runtime AI.

## 8. Testing plan
[inferred] Grew from zero to the current E2E + unit suite as the site expanded.

## 9. Deferred / what we'd do differently
[inferred] The MVP was intentionally minimal; everything below (feeds, deep-dives,
admin, docs hub) is a POST-MVP addition — see the shipped PRDs.
