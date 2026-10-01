---
title: "Publishing a personal Google OAuth app (Gmail scopes) needed an app-purpose page, not the résumé homepage — and Gmail reads still need a Workspace-only preview"
category: integration-issues
tags: [google-cloud, oauth, consent-screen, brand-verification, gmail, mcp, privacy-policy, terms, limited-use, legal-pages]
symptom: "the Gmail MCP connector failed with 'Access blocked: jameschang.co has not completed the Google verification process'; after adding privacy + terms, brand review rejected the app: 'not compliant with the Google APIs Terms of Service … update your home page to clearly outline your application's purpose and ensure it does not use Google APIs for AI NCII'"
root_cause: "three separate gates. (1) An OAuth client in Testing only admits listed test users, and Testing-mode Gmail refresh tokens expire after ~7 days. (2) Moving to Production triggers brand review of the consent screen's App homepage, privacy and terms URLs — the résumé homepage said nothing about what the app does, and nothing ruled out AI-generated NCII. (3) Even with branding verified, the gmailmcp endpoint refuses reads unless the Cloud project is enrolled in the Workspace Developer Preview, whose form rejects @gmail.com addresses."
module: site legal pages (index.html footer, /app/, /privacy/, /terms/) + the owner's Google Cloud OAuth client
date_solved: 2026-09-30
severity: low
---

# Publishing a personal Google OAuth app needed an app-purpose page

## Context

The owner connects his own Gmail to Claude Code through an OAuth client he created in his own
Google Cloud project; its consent screen is named "jameschang.co". Three different Google gates
stood between "connector configured" and "Claude can read my bills". They fail with different
messages and are easy to mistake for one problem.

## Gate 1 — Testing mode

**Symptom:** `Access blocked: jameschang.co has not completed the Google verification process`.

**Cause:** the client was in **Testing** and the account wasn't a listed test user. Testing also
expires Gmail-scope refresh tokens after about a week.

**Fix:** add the account under *Google Auth Platform → Audience → Test users* (immediate), then
publish to Production to stop the weekly re-login. Full verification of restricted Gmail scopes
needs a paid security assessment — not needed for a single-owner app; publishing unverified shows a
one-time "unverified app" interstitial and nothing else.

## Gate 2 — Brand review on publish

**Symptom:** after adding privacy + terms links to the homepage footer, review came back:
*"update your home page to clearly outline your application's purpose and ensure it does not use
Google APIs for AI NCII (AI-generated Non-Consensual Intimate Imagery)."*

**Cause:** the consent screen's **App homepage** pointed at the résumé homepage. A reviewer landing
there can't tell what the app does, and nothing addressed NCII. Privacy and terms alone were not
enough.

**Fix (commits `cdfaeeca`, `bb85eb80`):**
- **`/app/`** — a dedicated page set as the App homepage. Plain sections: what it is (a personal
  tool connecting the owner's Gmail to Claude in Claude Code), what it does (search/read, draft for
  review, label/spam/trash — owner-initiated only), who can use it (owner only, no sign-up), how
  Google data is handled, and **what it never does: no image or video generation, never AI NCII or
  sexual content**. It names Anthropic's Claude as where email content goes — transparency is the
  point of the page.
- **`/privacy/`** gained a "google account access" section with Google's **Limited Use** sentence
  ("…will adhere to the Google API Services User Data Policy, including the Limited Use requirements").
- **`/terms/`** — short generic terms; integrations are personal tools, not a public service.
- Homepage footer links `app · privacy · terms` (footer is print-hidden; résumé PDF unchanged —
  verified by regenerating and diffing the PDF text).

Branding verified the same day after the App homepage was switched to `/app/`.

**Guards:** `tests/test_site_e2e.py::TestLegalLinks` pins the footer links, the `/terms/` page, the
`/app/` purpose + NCII statement, and `TestPrivacyPolicy::test_discloses_google_limited_use` pins
the Limited Use sentence. **Don't reword those lines away** — they are what the reviewer checked.

## Gate 3 — Gmail reads need the Workspace Developer Preview

**Symptom:** with branding verified and the connector authenticated, every Gmail call returned
*"requires that your Google Cloud project … is enrolled in the Google Workspace Developer Preview Program."*

**Cause:** the hosted Gmail MCP endpoint is a preview product. Its enrollment form states
**"Gmail addresses, Service Accounts, and Google Groups will not be accepted"** — a personal
@gmail.com account cannot enroll.

**Status:** unresolved by design. Options: enroll with a Google **Workspace** address if one exists
(unclear whether it must also own the Cloud project), or don't read mail at all — the `/admin/`
money ledger takes manual entry, which for ~10–15 bills a month is about as fast.

## Lessons

1. **Three gates, three messages.** "Access blocked" (Testing), a brand-review rejection (publish),
   and a preview-enrollment error (reads). Fixing one surfaces the next; none implies the others.
2. **The App homepage is reviewed as a description of the app**, not as the owner's site. A personal
   app still needs a page that says what it does and what it won't do.
3. **Check product eligibility before building around a connector.** The Workspace-only preview
   restriction was knowable from the enrollment form; it ended the "read bills from Gmail" plan
   after the legal pages were already shipped (they stay useful — WHOOP and Spotify point at the
   same privacy policy).
