---
status: pending
priority: p3
issue_id: 112
tags: ['code-review', 'security', 'hardening']
dependencies: []
---

# Switch RSS parsing to `defusedxml` for entity-expansion DoS hardening

## Problem Statement
`bin/update-public-feeds.py:137,184,223` use stdlib `xml.etree.ElementTree`, which blocks external entities but is still vulnerable to billion-laughs / quadratic blowup. Risk is bounded — runs in an ephemeral Actions container against trusted upstreams (letterboxd.com, goodreads.com) — but a compromised upstream could DoS the workflow.

**Surfaced by:** security-sentinel during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: `import defusedxml.ElementTree as ET`
- Drop-in replacement for stdlib ElementTree
- Adds one dependency (`defusedxml` is small, single-purpose, well-maintained)
- Conflicts with CLAUDE.md's "Python 3 is the only tooling dependency" — confirm acceptable
- **Effort:** Trivial

### Option B: Document residual risk and accept
- Bound by ephemeral runner + trusted-upstream assumption
- **Effort:** Trivial (CLAUDE.md note)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] Decision documented (adopt or accept residual)
- [ ] If adopted, `requirements.txt` (or equivalent) introduced or note the divergence from "stdlib only"

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
