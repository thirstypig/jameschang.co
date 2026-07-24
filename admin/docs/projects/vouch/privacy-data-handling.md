---
id: DOC-VOUCH-PRIVACY
type: privacy
project: vouch
status: draft
owner: james
tags: [compliance]
links: [PRD-VOUCH-001]
updated: 2026-07-24
---

# Vouch — privacy & data handling

> **⚠️ Load-bearing, not boilerplate.** Vouch handles data about **minors**. This is the
> most important doc in the hub. Treat every unresolved item as a **launch blocker**.

**Public / private boundary (public repo):** this doc records public-facing *commitments*
(what we promise users) — those are safe to publish. It must NOT record internal security
*specifics* — where minor data physically lives, exact access-control implementation,
credentials. Those are an attack map and stay in the private repo / local notes.

`[inferred]` = read from the product's stated intent (PRD-VOUCH-001) ·
`[DECIDE]` = a decision required before launch (James) · `[private]` = kept off this page.

## Who's on the platform
- **Students** — [inferred] minors (under 18); the protected class this whole doc exists for.
- **Mentors** — [inferred] adults who vouch for students.
- **Supporters** — [inferred] adults who back students financially.

## What data we collect
- Students: [DECIDE] name, age/DOB, school, the goal/change they share, photos?, contact?
  Collect the **minimum** needed; every extra field on a minor is added risk.
- Mentors / supporters: [DECIDE] identity + (for supporters) payment details.

## Parental consent
- [confirmed 2026-07-24] **A verified parent/guardian must consent before a minor can
  create a live profile** — no live student profile exists without it. (Portfolio "next
  up" already includes wiring real parent accounts.) Effectively table stakes for a
  minor-facing product (COPPA/analogous norms).

## Visibility — who can see a student
- [inferred] "safety-first, moderated by default."
- [confirmed 2026-07-24] **Default: private until approved.** A student's profile is not
  visible to anyone until reviewed/approved; visibility is opened deliberately, never by
  default. The most protective option — matches the safety-first stance.

## Money & minors
- [inferred] supporters back students; donations currently in Stripe test mode.
- [confirmed 2026-07-24] **Funds route through a verified parent/guardian — never directly
  to the minor.** Removes the money-directly-to-a-child risk (a compounded-risk combination).

## Retention & deletion
- [DECIDE] How long is student data kept? Deleted on request? On account close? On aging out?
- [DECIDE] Right-to-be-forgotten flow for a minor (and a parent acting for them).

## Moderation & safety
- [inferred] moderated by default.
- [DECIDE] What's moderated (profiles, messages, media), by whom (human/automated/both),
  and the response time / escalation path for a safety report.

## Access control
- [private] Who internally can access student data, and how it's protected — kept OFF this
  public page. Record in the private repo.

## Decisions required before launch (the gate)
- [x] Parental consent — **yes, verified, before any live profile** (2026-07-24)
- [x] Default student-profile visibility — **private until approved** (2026-07-24)
- [x] Money flow re: minors — **through a verified parent/guardian** (2026-07-24)
- [ ] Data retention + deletion policy
- [ ] Moderation model + safety-report SLA
- [ ] Minimum-data audit (drop every field not strictly needed on a minor)
