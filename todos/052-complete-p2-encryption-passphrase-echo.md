---
status: done
priority: p2
issue_id: 052
tags: [code-review, security]
dependencies: []
---

# whoop-encrypt.sh echoes passphrase to terminal

## Problem
`bin/whoop-encrypt.sh:19` uses plain `read -rp` (no `-s` flag) so the passphrase is echoed as typed. Generated passphrase is printed at line 24 and again at line 33. Shell scrollback, recordings, or over-shoulder viewers see it. Also, openssl default PBKDF2 iteration count is 10000 — OWASP 2023 recommends 600000+ for AES-256-CBC key derivation.

## Proposed Solutions
(1) Use `read -rs` for passphrase entry. (2) When generating, write to tempfile with mode 600 instead of echoing to stdout. (3) Pass `-iter 600000` explicitly to openssl.

## Acceptance Criteria
- [ ] No passphrase echoed to terminal; iteration count ≥ 600000; tempfile mode 600.
