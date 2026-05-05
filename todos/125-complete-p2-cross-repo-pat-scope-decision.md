---
status: complete
priority: p2
issue_id: 125
tags: ['code-review', 'security', 'cross-repo-admin']
dependencies: []
---

# Shared PAT widens blast radius — make the trade-off explicit

## Problem Statement
This session unified the PAT key across `HitListManager` and `BucketListManager` (commit `d64bdb85` on thirstypig). Pre-change, an XSS or token-paste mistake in the Tina admin could only mutate `thirstypig-blog`. Post-change, the same compromise mutates **both** that repo AND `jameschang.co` — which carries résumé claims, JSON-LD identity, GA4 ID, custom apex DNS, and is what every recruiter visits.

Realistic threat: a supply-chain compromise in any module the Tina admin loads (Tina's own deps, Google Maps SDK loaded dynamically at `HitListManager.tsx:33` with no SRI, the `weekly` channel of which is a moving target) reads `sessionStorage["thirstypig-admin-pat"]` and pushes commits anywhere on either repo. Pages redeploys in ~60s with no review.

**Surfaced by:** security-sentinel and architecture-strategist during /ce:review 2026-05-05.

This is a P2 not P1 because (a) thirstypig admin is gated by TinaCloud auth, (b) the operator (you) is the only realistic target, and (c) sessionStorage clears on tab close. But the trade-off was made implicitly — the unified-key commit doesn't acknowledge the widened radius.

## Proposed Solutions

### Option A — Keep shared, add deliberate guardrails (recommended)
Document in CLAUDE.md and in the admin banner that:
- The PAT is shared across both repos by design (operator convenience).
- It must be rotated **every 90 days max** (fine-grained PAT free-tier ceiling — but treat 30 days as the operating practice).
- Add a 7-day expiry reminder to the admin banner copy: "PAT expires {ISO date} — rotate before then."
- Pin Google Maps SDK to a version (drop `v=weekly`) and add `integrity="..."` SRI hash.
- Add admin-side CSP (see todo 129).

**Effort:** Medium (~1 hour total for all guardrails)
**Risk:** Low — pure tightening.

### Option B — Revert to per-manager PATs
Keep `hitlist-github-pat` and `bucketlist-github-pat` as separate keys. Each token narrowly scoped. Operator pastes both once per session. Friction trade for safety.

**Effort:** Small (~15 min revert)
**Risk:** Low. UX cost is one extra paste per session.

### Option C — Move to a backend
Out of scope; would violate the "GitHub Pages, no backend" rule.

## Recommended Action
**Option A** — the shared PAT was a deliberate UX call this session and reverting it is a step backward. But the guardrails (expiry reminder, SDK pinning, admin CSP) are owed.

## Acceptance Criteria
- [ ] CLAUDE.md gains a "Cross-repo PAT trade-off" subsection
- [ ] Admin banner copy mentions expiry rotation
- [ ] Google Maps SDK pinned + SRI'd in HitListManager
- [ ] Admin CSP audit completed (see todo 129)

## Resources
- `/Users/jameschang/Projects/thirstypig/tina/BucketListManager.tsx:15`
- `/Users/jameschang/Projects/thirstypig/tina/HitListManager.tsx:18,33`
- `docs/solutions/integration-issues/cross-repo-admin-via-github-contents-api.md` ("PAT scope" section)
