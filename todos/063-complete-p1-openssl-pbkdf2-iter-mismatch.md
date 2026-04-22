---
status: done
priority: p1
issue_id: 063
tags: [code-review, security, whoop]
dependencies: []
---

# OpenSSL PBKDF2 iteration count mismatch between encrypt and decrypt

## Problem Statement
`bin/whoop-encrypt.sh` uses `-iter 600000` for AES-256-CBC encryption, but `bin/update-whoop.py` omits `-iter` in both the decrypt (line 44) and re-encrypt (line 58) subprocess calls. OpenSSL's default iteration count varies by version (10000 on older builds, different on newer). This creates a latent incompatibility: a token encrypted with the shell script may fail to decrypt in the GitHub Action, or vice versa.

**Why it matters:** If someone re-runs `whoop-encrypt.sh` to seed a new token, the Action's `update-whoop.py` cannot decrypt it due to the iteration count mismatch. The WHOOP sync pipeline would silently break.

## Findings
- `bin/whoop-encrypt.sh:34` — `openssl enc -aes-256-cbc -pbkdf2 -iter 600000`
- `bin/update-whoop.py:43-46` — decrypt call omits `-iter`
- `bin/update-whoop.py:57-59` — re-encrypt call omits `-iter`
- Flagged independently by Security Sentinel and Agent-Native reviewers

## Proposed Solutions

### Option A: Add `-iter 600000` to Python calls (Recommended)
Add `"-iter", "600000"` to both subprocess.run arrays in update-whoop.py.
- **Pros:** Matches the documented manual encryption path; 600000 is a strong KDF parameter
- **Cons:** None
- **Effort:** Small (2 lines)
- **Risk:** None — aligns both tools

### Option B: Remove `-iter` from shell script
Remove `-iter 600000` from whoop-encrypt.sh so both use OpenSSL's default.
- **Pros:** Fewer parameters to maintain
- **Cons:** Weaker KDF; default varies by OpenSSL version, could still mismatch across environments
- **Effort:** Small (1 line)
- **Risk:** Low — but default instability across versions is the original problem

## Recommended Action
Option A — standardize on `-iter 600000` everywhere.

## Technical Details
- **Affected files:** `bin/whoop-encrypt.sh`, `bin/update-whoop.py`
- **Components:** WHOOP OAuth token rotation pipeline

## Acceptance Criteria
- [ ] `bin/update-whoop.py` decrypt call includes `-iter 600000`
- [ ] `bin/update-whoop.py` re-encrypt call includes `-iter 600000`
- [ ] Both match `bin/whoop-encrypt.sh`
- [ ] Document the chosen iteration count in CLAUDE.md

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-18 | Created | Found during full-repo code review |

## Resources
- `docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md`
