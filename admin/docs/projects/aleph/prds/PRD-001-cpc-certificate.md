---
id: PRD-001
type: prd
project: aleph
status: active
owner: james
tags: [compliance]
links: []
updated: 2026-07-23
phase: null
---
<!-- WORKED EXAMPLE. Reconstructed from Aleph's public roadmap
     (/projects/aleph/roadmap/, CPSIA / CPC module). Claims are tagged:
     [inferred] = read from public docs/behaviour · [unknown] = ASK JAMES,
     the code/docs can't tell us · [intended] = plausibly deliberate. -->

# Aleph — CPC certificate generation

## 1. Problem statement
[inferred] US importers of children's products (age 12 and under) must issue a
Children's Product Certificate (CPC) under CPSIA. Doing it by hand — collating lab
results, standards, and importer data into a compliant PDF — is error-prone and slow.

## 2. Strategic rationale
[unknown] Why CPC first among Aleph's modules (vs. Prop 65, PFAS, FSVP)? Likely a
beachhead choice, but the ordering rationale isn't recorded. **← James to confirm.**

## 3. User story
[inferred] As an importer, I want to generate a filing-ready CPC from my product +
lab data so that I can clear customs without hand-building the certificate.

## 4. Hypothesis / assumptions
- [inferred] Importers will trust a generated CPC enough to file it.
- [unknown] The bet on *what* makes them switch from spreadsheets/consultants. **← confirm.**

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] certificates generated, time-to-first-CPC, activation→paid.
- (b) TODAY: [unknown] — is any of this instrumented? Not visible from public docs. **← confirm.**

## 6. Technical notes
[inferred] Workflow: add product → upload lab test report → complete the 7-field CPC
form → preview → generate a formatted PDF. PDF generation via `pdf-lib`. (Details from
the public roadmap; verify against the app repo when we do the archaeology pass.)

## 7. AI implementation notes
[unknown] Does CPC use any AI (e.g. extracting fields from the lab PDF), or is it pure
form-fill? Public docs don't say. **← confirm.**

## 8. Testing plan
[unknown] What tests cover CPC generation today? Fill from the `alephco.io-app` repo.

## 9. Deferred / what we'd do differently
[unknown] Reserved for the hindsight pass — fill once we read the code.
