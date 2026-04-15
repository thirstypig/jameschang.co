---
status: pending
priority: p1
issue_id: 005
tags: [code-review, security, privacy, screenshots]
dependencies: []
---

# Scrub screenshots for personal email, password length hints, and possible real user/customer data

## Problem Statement

Several screenshots committed to the public repo may be exposing personally identifiable or customer-confidential content:

1. **`02-signup-dark.png` / `03-login-dark.png`** (Fantastic Leagues) — signup and login forms with `jimmychang316@gmail.com` pre-filled and an 8-char masked password. The password length leaks useful information to a targeted attacker.
2. **Judge Tool screenshots** — display specific names ("Patricia Brown", "Sarah Mitchell", "Lisa Chen", "Bob Thompson"). These are almost certainly fixtures, but need verification.
3. **`aleph/products.png`** — shows ~10 SKU rows with product names and manufacturer columns. If seed data, fine; if early customer catalogs, that's a confidentiality issue.
4. **`aleph/changelog.png` + `roadmap.png`** — logo reads "FSVP Pro" (pre-rebrand). Not a security issue, but paired with current Aleph branding it's an inconsistency.

## Findings

From security-sentinel agent (P2-3, P2-4, P2-5, P2-6).

## Proposed Solutions

### Option A: Redact via blur / crop, retake where needed
- Blur email/password fields in signup/login shots with Preview.app or `sips`
- Verify Judge Tool fixture names (cross-check against FBST seed data)
- Verify Aleph products.png is seed data (check against repo seeds)
- Retake FSVP Pro screenshots with current Aleph branding
- **Effort:** Medium (~30 min)

### Option B: Replace with fresh captures
- Log into each app as a test user with obvious-fake data (`demo@example.com` / seeded rows)
- Retake all 35 screenshots cleanly
- **Effort:** Large (~2 hours)

### Option C: Minimum viable — scrub only the email/password shots + verify others
- Blur email + password dots in `02-signup-dark.png` and `03-login-dark.png` only (5 min)
- Run a check on other shots, fix any discovered real-user leaks
- Accept stale FSVP Pro branding as a separate todo (todo #007)
- **Effort:** Small to medium (~15–30 min)
- **Recommended — targeted fix**

## Technical Details

Files to review:
- `/Users/jameschang/Projects/jameschang.co/assets/work/fantastic-leagues/02-signup-dark.png` (redact)
- `/Users/jameschang/Projects/jameschang.co/assets/work/fantastic-leagues/03-login-dark.png` (redact)
- `/Users/jameschang/Projects/jameschang.co/assets/work/judge-tool/judge-*.png` (verify fixture)
- `/Users/jameschang/Projects/jameschang.co/assets/work/judge-tool/organizer-*.png` (verify fixture)
- `/Users/jameschang/Projects/jameschang.co/assets/work/judge-tool/captain-dashboard.png` (verify fixture)
- `/Users/jameschang/Projects/jameschang.co/assets/work/aleph/products.png` (verify seed data)

Quick blur via Preview:
1. Open image, Tools → Redact → drag over email/password fields
2. Save; commit

## Acceptance Criteria

- [ ] No personal email visible in any /assets/work/ screenshot
- [ ] No password field (even masked) visible where it could reveal length
- [ ] Every name/SKU in screenshots confirmed as seed/fixture data
- [ ] No customer-confidential product catalogs visible

## Work Log

_(blank)_

## Resources

- Security audit output
- FBST seed data in `~/projects/fbst/server/src/scripts/` (to verify)
