---
status: done
priority: p2
issue_id: 082
tags: ['code-review', 'testing', 'security']
dependencies: []
---

# Add e2e assertion locking CSP byte-equality across the homogeneous 15 pages

## Problem Statement
15 of 16 pages share an identical CSP meta-tag (verified during /ce:review). `now/index.html` differs only by adding `https://thirstypig.com` to `connect-src` — intentional and documented. No test asserts byte-equality across the homogeneous 15, so a single-file CSP edit (e.g., the recent googletagmanager.com fix) could silently leave one page un-patched.

**Surfaced by:** pattern-recognition-specialist during /ce:review on 2026-04-28.

## Proposed Solutions
### Option A: Add `TestCSP::test_csp_homogeneous_across_15_pages`
Hash the `<meta http-equiv="Content-Security-Policy">` content of each non-`now/` page; assert all 15 hashes match. Exempt `now/index.html` with a comment explaining the intentional connect-src difference.
- **Effort:** Small

## Recommended Action
_(Filled during triage, leave blank initially)_

## Acceptance Criteria
- [ ] New test asserts CSP equality across the 15 pages
- [ ] `/now/` exemption documented inline in the test

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-28 | Created | Found during /ce:review multi-agent code review |

## Resources
- Recent commits: cede613, 5f06bd8, 42cf3e8, 24ab923, 8027ee2 (this session)
- Review agents: security-sentinel, code-simplicity-reviewer, pattern-recognition-specialist, agent-native-reviewer, learnings-researcher
| 2026-04-28 | Resolved | Fixed inline as part of /ce:review response batch |
