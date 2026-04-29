---
status: discarded
priority: p3
issue_id: 112
tags: ['code-review', 'security', 'hardening', 'decided-to-skip']
dependencies: []
---

# Switch RSS parsing to `defusedxml` for entity-expansion DoS hardening

**Discarded 2026-04-29 (Option B accepted) — residual risk is bounded.**
The DoS attack surface requires a *compromised* letterboxd.com or goodreads.com
serving a billion-laughs document. The cron runs in an ephemeral GitHub
Actions container with no persistent state and is rate-limited by cron cadence,
so a successful DoS would burn one workflow run, recover automatically, and
hit the 48h staleness monitor on the way down. CLAUDE.md's "Python 3 is the
only tooling dependency" rule is more valuable than the marginal hardening,
and `defusedxml` would force introducing a `requirements.txt` for a single
import. Re-evaluate if the upstream RSS sources change to ones we don't trust,
or if the Python "stdlib only" rule is otherwise relaxed.

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
