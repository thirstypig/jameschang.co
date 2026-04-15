---
status: pending
priority: p1
issue_id: 020
tags: [code-review, simplicity, security, yagni]
dependencies: []
---

# Cut the sync-work.py + GitHub Action pipeline

## Problem

Two independent agents flagged the same pipeline:

1. **Security-sentinel (P1.1):** Stored XSS risk. The script regex-extracts `version`/`date`/`title` from upstream TSX via `[^"]+` (any character except `"`), concatenates unescaped into HTML, and the GitHub Action auto-commits + pushes with no human review. A compromised `fbst` repo could inject arbitrary HTML into `jameschang.co`.

2. **Code-simplicity-reviewer (CUT #1):** "The script doesn't sync, it writes a date." 260 LOC of infra (Python + YAML + README) to patch a per-page "Last updated: YYYY-MM-DD" string. Same outcome achievable in 3 lines via `git log -1 --format=%ad FILE` at deploy time. Includes dead code (`injected = f'{pattern.pattern and ""}'`, tautological `return 0 if True else ...`) — the author's own tell that something was off.

Performance-oracle found no perf benefit. Pattern-recognition found the sync markers add cruft.

**Convergence is decisive. Cut.**

## Proposed Solutions

### Option A (Recommended): Delete the whole subsystem
```
bin/sync-work.py                              [-149 LOC]
bin/README.md                                 [-74 LOC]
.github/workflows/sync-work.yml               [-37 LOC]
styles.css .synced-line + .page-updated       [~-20 LOC]
<!-- sync-start/end --> + <!-- updated-start/end --> markers on 10 /work/ pages + snapshot patch
<p class="page-updated">...</p>               [10 lines × 1 page]
<p class="synced-line">...</p>                [1 line on fbst/changelog]
```
If you still want a "Last updated" signal: single footer line with git-log date, computed at deploy time.

### Option B: Harden the script (escape HTML, pin TLS, make main() honest)
Closes the P1.1 security risk but doesn't address the simplicity critique. Still a cron that patches a date.

### Option C: Status quo
- Accept weekly cron + regex brittleness + XSS surface for one date string. Not recommended.

## Acceptance Criteria
- [ ] `bin/sync-work.py`, `bin/README.md`, `.github/workflows/sync-work.yml` deleted
- [ ] `.synced-line` and `.page-updated` CSS removed (or converted if replacing with git-log timestamps)
- [ ] `<!-- sync-start/end -->` and `<!-- updated-start/end -->` comments removed from /work/ pages + associated `<p>` elements
- [ ] Optionally: single footer "Last updated" line added using git log at deploy
- [ ] Site renders identically; no 404s; no XSS surface

## Resources
- security-sentinel review 2026-04-15, P1.1 (HTML injection from upstream TSX)
- code-simplicity-reviewer review 2026-04-15, CUT #1 ("260 LOC for a date string")
- If Option A: also closes P2.1 (TLS pinning), P2.2 (always-0 return), P2.3 (git add -A), P2.4 (bot user.name)
