---
status: pending
priority: p2
issue_id: 007
tags: [code-review, content, branding, screenshots]
dependencies: [005]
---

# Retake two Aleph admin screenshots with current branding (not FSVP Pro)

## Problem Statement

Two screenshots in `/assets/work/aleph/` still show the pre-rebrand "FSVP Pro" logo/wordmark:
- `aleph/changelog.png`
- `aleph/roadmap.png`

Everywhere else on the site the product is called "Aleph Compliance" / "Aleph Co." The stale screenshots are the only place the old name appears visually — contradicts the Aleph Co. case study on the homepage which explicitly calls out the rebrand as "what I'd do differently."

## Findings

From security-sentinel agent (P2-6):
- PLAN.md:22, 618 resolved the rebrand to Aleph Co.
- Current homepage + /work/aleph/ all use new branding
- These two screenshots predate the rebrand

## Proposed Solutions

### Option A (Recommended): Retake with current Aleph branding
- Log into `app.alephco.io` admin
- Navigate to `/admin/changelog` and `/admin/roadmap`
- Full-page screenshots (same dimensions as originals for CSS compat)
- Replace files in repo

### Option B: Crop out the logo area
- Keeps the body content, removes the stale wordmark
- **Effort:** Small • **Cons:** loses visual context

### Option C: Leave as-is
- The case study actually *mentions* the rebrand — stale screenshots could be read as "evidence of the old name"
- **Effort:** None • **Cons:** most visitors won't read that deep

## Technical Details

Files:
- `/Users/jameschang/Projects/jameschang.co/assets/work/aleph/changelog.png`
- `/Users/jameschang/Projects/jameschang.co/assets/work/aleph/roadmap.png`

Replace in place, same filenames; no HTML changes needed.

## Acceptance Criteria

- [ ] Both screenshots show "Aleph" or "Aleph Compliance" branding
- [ ] No "FSVP Pro" wordmark visible anywhere on the live site
- [ ] Same aspect ratios as originals (to avoid CSS layout shift)

## Work Log

_(blank)_

## Resources

- Security audit (P2-6)
- PLAN.md context on rebrand timing
