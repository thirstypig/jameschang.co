---
category: integration-issues
title: OpenSSL PBKDF2 iteration count mismatch between shell and Python callers
problem_type: latent-incompatibility
components:
  - bin/whoop-encrypt.sh
  - bin/update-whoop.py
symptoms:
  - WHOOP token decrypt fails with "bad decrypt" after re-encryption by a different script
  - GitHub Actions workflow fails after manual token re-seed via whoop-encrypt.sh
  - Token encrypted by shell script cannot be decrypted by Python subprocess (or vice versa)
root_cause: >
  whoop-encrypt.sh specified -iter 600000 for AES-256-CBC PBKDF2, but the Python
  subprocess calls in update-whoop.py omitted -iter entirely. OpenSSL falls back
  to a version-dependent default iteration count. Any encrypt/decrypt pair using
  different iteration counts produces "EVP_DecryptFinal_ex:bad decrypt".
fix_summary: >
  Added "-iter", "600000" to both the decrypt and re-encrypt subprocess.run()
  calls in update-whoop.py so all three callsites (shell encrypt, Python
  decrypt, Python re-encrypt) use the same iteration count.
tags:
  - openssl
  - pbkdf2
  - aes-256-cbc
  - iteration-count
  - subprocess
  - whoop
  - token-rotation
resolved: 2026-04-18
---

# OpenSSL PBKDF2 iteration count mismatch between shell and Python callers

## Symptoms

The WHOOP sync GitHub Action can fail with `bad decrypt` errors when decrypting `.whoop-token.enc`, despite the token being valid. The failure is environment-dependent — it surfaces when the encrypting and decrypting scripts use different OpenSSL `-iter` values.

## Investigation

1. Compared the encryption command in `bin/whoop-encrypt.sh` with the decryption/re-encryption subprocess calls in `bin/update-whoop.py`.
2. `whoop-encrypt.sh` explicitly passes `-iter 600000` to `openssl enc -aes-256-cbc -pbkdf2`.
3. `update-whoop.py` calls `openssl enc -aes-256-cbc -d -pbkdf2` and `openssl enc -aes-256-cbc -pbkdf2` (for re-encryption) — neither specifies `-iter`.
4. OpenSSL documentation confirms: when `-pbkdf2` is used without `-iter`, the iteration count defaults to a version-dependent value (10000 in OpenSSL 1.1.1, potentially different in 3.x builds). The shell script's explicit `600000` never matches any default.
5. A file encrypted with `-iter 600000` cannot be decrypted without `-iter 600000`. The mismatch produces `EVP_DecryptFinal_ex:bad decrypt`.

## Root cause

The Python subprocess calls omitted the `-iter 600000` flag that the shell encryption script uses. This worked by coincidence when both scripts used the same OpenSSL version's default, or when the token had only ever been through the Python re-encrypt path (which consistently used the default). The moment the file passed through `whoop-encrypt.sh` (which uses `-iter 600000`), the Python script could no longer decrypt it.

## Fix

Add `"-iter", "600000"` to both subprocess arrays in `update-whoop.py`:

```python
# Decrypt (~line 44)
subprocess.run([
    "openssl", "enc", "-aes-256-cbc", "-d", "-pbkdf2", "-iter", "600000",
    "-in", TOKEN_ENC, "-pass", f"pass:{key}"],
    capture_output=True, text=True,
)

# Re-encrypt (~line 58)
subprocess.run([
    "openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "600000",
    "-out", TOKEN_ENC, "-pass", f"pass:{key}"],
    input=token, capture_output=True, text=True,
)
```

## Key insight

When using `openssl enc` with `-pbkdf2`, the iteration count is a cryptographic parameter baked into the derived key — not a performance tuning knob. Every encrypt/decrypt call chain must use the exact same `-iter` value, and that value must be explicit. Relying on OpenSSL's default is fragile because (a) the default varies across versions, and (b) any script in the chain that specifies `-iter` will silently diverge from any script that doesn't. **Treat `-iter` as mandatory whenever `-pbkdf2` is used.**

## Prevention

1. **Never rely on OpenSSL defaults for PBKDF2 iterations.** Always pass `-iter` explicitly.
2. **Document the invariant.** CLAUDE.md should note that all OpenSSL calls must use `-pbkdf2 -iter 600000`.
3. **Quick verification grep:** `grep -rn "openssl enc" bin/ | grep -v "\-iter 600000"` should return nothing.
4. **Round-trip smoke test.** After any change, encrypt a test value with the shell script and decrypt with the Python script (or vice versa). If they disagree, the test fails immediately.

## Related

- `docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md` — the full WHOOP OAuth2 architecture that this encryption supports
