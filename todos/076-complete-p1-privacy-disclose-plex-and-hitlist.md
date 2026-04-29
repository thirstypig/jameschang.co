---
status: done
priority: p1
issue_id: 076
tags: ['code-review', 'security', 'privacy', 'documentation']
dependencies: []
---

# Privacy policy must disclose Plex integration and Thirsty Pig hitlist client-side fetch

## Problem Statement
The 2026-04-28 privacy trim removed Trakt + Letterboxd disclosures (correct — those feeds were dropped from /now). But it also exposed a pre-existing gap: **Plex** is named in the privacy meta-description and intro line ("WHOOP / Spotify / Plex integrations") but has no dedicated integration section in the body, and the **Thirsty Pig hitlist** (`https://thirstypig.com/places-hitlist.json`) is a client-side third-party fetch declared in `now/index.html`'s CSP `connect-src` but never named in the privacy policy.

**Surfaced by:** security-sentinel agent during /ce:review on 2026-04-28.

**Files:**
- `privacy/index.html` lines 79 (WHOOP block), 90 (Spotify block) — pattern to mirror for Plex
- `privacy/index.html` lines 105–113 — additional-APIs ul where hitlist should be added
- `now/index.html` line 9 — CSP `connect-src https://thirstypig.com` is the runtime evidence

## Proposed Solutions
### Option A: Add full Plex section + hitlist line (recommended)
- Add a new `<p>` block mirroring WHOOP/Spotify pattern: "This site displays the site owner's own recently-watched library entries from a personal Plex server. Plex is queried via a static API token using the relay URL pattern; only the owner's library metadata is read..."
- Add `<li><a href="https://thirstypig.com">Thirsty Pig hitlist JSON</a> — a list of restaurants the owner wants to try, fetched client-side. CORS locked to https://jameschang.co; no visitor data crosses the origin.</li>` to the additional-APIs `<ul>`
- Update the test in `tests/test_site_e2e.py::TestPrivacyPolicy::test_lists_all_feed_sources` to require "Plex" and "Thirsty Pig" or "hitlist"
- **Effort:** Small (15 minutes)
- **Risk:** None — additive only

### Option B: Remove Plex from meta-description / intro (rejected)
Less complete than Option A; misrepresents what /now actually does.

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] Plex integration paragraph added to privacy/index.html (between Spotify and the additional-APIs ul)
- [ ] Hitlist disclosure added to additional-APIs ul
- [ ] Privacy policy meta description updated if needed
- [ ] `test_lists_all_feed_sources` extended to require Plex + hitlist
- [ ] All e2e tests pass

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
