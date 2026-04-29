---
status: done
priority: p3
issue_id: 086
tags: ['code-review', 'security', 'csp']
dependencies: []
---

# Plan migration from `unsafe-inline` script-src to hash-based CSP

## Problem Statement
All 16 pages have `script-src 'self' 'unsafe-inline' https://www.googletagmanager.com`. The `'unsafe-inline'` is required for the inline gtag init snippet and small inline scripts (theme toggle init, etc.). With `'unsafe-inline'` present, the recent `img-src` widening to `googletagmanager.com` is essentially defense-in-depth only — a successful HTML injection on any page could already exfiltrate via any allowed connect-src/img-src host.

Replacing `'unsafe-inline'` with `'sha256-…'` hashes for the few remaining inline blocks would meaningfully tighten the CSP. Achievable on GitHub Pages (no need for response headers) since CSP meta-tag supports hash sources.

**Surfaced by:** security-sentinel during /ce:review on 2026-04-28.

Out-of-scope for current work; tracked here as future hardening.

## Proposed Solutions
### Option A: Move all inline scripts to `script.js` + use script hashes
- Move gtag init snippet + theme toggle init + headshot rotator code to `script.js`
- Compute sha256 of any remaining inline blocks (or script.js if loaded inline)
- Replace `'unsafe-inline'` with the hash list
- **Effort:** Medium

### Option B: Defer
Document as a known limitation; revisit if a real injection vector ever appears.

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] All inline `<script>` blocks externalized OR hashed
- [ ] CSP `script-src` no longer contains `'unsafe-inline'`

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
