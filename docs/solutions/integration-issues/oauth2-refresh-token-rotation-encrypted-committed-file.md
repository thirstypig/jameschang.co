---
title: "WHOOP API integration on static GitHub Pages site with self-healing refresh token rotation"
category: integration-issues
tags: [oauth2, github-actions, refresh-token-rotation, cloudflare, static-site, whoop-api, encrypted-secrets]
symptom: "WHOOP data sync from GitHub Actions failed across multiple layers: OAuth redirect had no server to land on, Cloudflare returned error 1010 blocking runner IPs, token endpoint rejected client_secret_basic auth, v1 endpoints 404'd, and rotated refresh tokens couldn't be written back to GitHub Secrets (GITHUB_TOKEN lacks secrets:write)."
root_cause: "Compounded mismatch between WHOOP's OAuth2 server requirements (client_secret_post, rotating refresh tokens, Cloudflare UA filtering, v2 API path) and the constraints of a static GitHub Pages site with no backend and no elevated Actions permissions for secret mutation."
module: whoop-integration (.github/workflows/whoop-sync.yml, bin/update-whoop.py, whoop/callback/index.html, .whoop-token.enc)
date_solved: 2026-04-15
severity: high
---

# WHOOP OAuth2 Integration on GitHub Pages: A Self-Healing Static Pipeline

## The Problem

The initial symptom was deceptively simple: the daily GitHub Actions workflow that synced WHOOP biometric data to `/now/index.html` on jameschang.co worked perfectly on its first run, then failed on every subsequent run with a `400 invalid_request` error from the WHOOP token endpoint.

Observable behavior:
- Day 1: Manual OAuth flow completed, `WHOOP_REFRESH_TOKEN` secret populated, workflow ran green, `/now/index.html` updated with fresh recovery/sleep/workout data.
- Day 2 (scheduled run): Workflow failed at the token-refresh step. Logs showed `HTTP 400: {"error": "invalid_request"}`.
- Day 3+: Same failure. Manual re-auth fixed it for exactly one more run before failing again.

The pipeline was only "working" in the sense that a wind-up toy works: one turn of the crank per manual intervention. That defeated the entire point of a daily cron.

## Investigation Steps (what failed first)

Before arriving at the token-rotation issue, four unrelated red herrings had to be cleared:

### 1. Cloudflare error 1010 (access denied)

The very first attempt to hit `api.prod.whoop.com` from a GitHub Actions runner returned a Cloudflare error code 1010 page rather than JSON. Python's `urllib` default User-Agent (`Python-urllib/3.x`) was being filtered at the edge.

**Fix:** Send a well-formed UA and an explicit `Accept` on every request:

```python
headers={
    "User-Agent": "jameschang.co/1.0 (WHOOP personal dashboard; +https://jameschang.co)",
    "Accept": "application/json",
}
```

### 2. HTTP Basic auth rejected at `/oauth/oauth2/token`

Second attempt passed `client_id:client_secret` as HTTP Basic. WHOOP's IdP responded with `invalid_client` and a hint explicitly naming the supported method:

> The OAuth 2.0 Client supports client authentication method "client_secret_post", but method "client_secret_basic" was requested.

**Fix:** Move credentials into the form-encoded POST body:

```python
data = urlencode({
    "grant_type": "refresh_token",
    "refresh_token": refresh_token,
    "client_id": client_id,
    "client_secret": client_secret,
}).encode()
```

### 3. Wrong API version

Initial data-fetch calls used `/developer/v1/recovery` and returned 404s. WHOOP's personal-scope collection endpoints live at v2.

**Fix:**

```python
API_BASE = "https://api.prod.whoop.com/developer/v2"
# endpoints: /recovery, /activity/sleep, /activity/workout, /cycle
```

### 4. Refresh-token rotation (the real bug)

With the three above fixed, day 1 worked. Day 2 failed. Logging revealed WHOOP's response to `grant_type=refresh_token` always contained a **new** `refresh_token`, and the old one was invalidated at the moment of exchange. Rotation on every use.

The obvious fix — "just update the `WHOOP_REFRESH_TOKEN` secret at the end of each run" — is blocked by a hard GitHub constraint: the default `GITHUB_TOKEN` has no `secrets: write` scope, and cannot be granted one. A PAT would work, but storing a PAT with `repo` scope just to rotate a WHOOP token is a huge blast-radius expansion for a personal hobby site.

## Root Cause

A chicken-and-egg between two rotating credentials and an immutable secret store:

- **WHOOP** insists refresh tokens rotate on every exchange. You cannot opt out.
- **GitHub Actions** lets a workflow *read* secrets but not *write* them back (without a privileged PAT).
- **Without a stateful server**, there is nowhere to persist the new refresh token between runs.

The only writable surface a workflow has by default is **the repo itself** via `contents: write`. So the refresh token has to live in the repo. But committing a raw refresh token to a public GitHub Pages repo is obviously unacceptable.

That gap — "need to persist a rotating secret, only have the public repo to persist it in" — is the root cause. The solution is to turn the repo into an encrypted keystore by splitting the credential in two: the ciphertext lives in the repo, the key lives in GitHub Secrets. Neither half is useful without the other, and only one of them (the ciphertext) needs to rotate.

## Solution

### Workflow (`.github/workflows/whoop-sync.yml`)

```yaml
name: Sync WHOOP data to /now
on:
  schedule:
    - cron: '0 10 * * *'    # daily at 10:00 UTC (3am PT)
  workflow_dispatch:

permissions:
  contents: write            # needed to commit the rotated ciphertext

jobs:
  update-whoop:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }

      - name: Fetch WHOOP data and update /now/
        env:
          WHOOP_CLIENT_ID:     ${{ secrets.WHOOP_CLIENT_ID }}
          WHOOP_CLIENT_SECRET: ${{ secrets.WHOOP_CLIENT_SECRET }}
          WHOOP_TOKEN_KEY:     ${{ secrets.WHOOP_TOKEN_KEY }}
        run: python bin/update-whoop.py

      - name: Commit and push (updated /now + rotated token)
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add now/index.html .whoop-token.enc
          if git diff --cached --quiet; then
            echo "No changes to commit."
          else
            git commit -m "chore: update WHOOP data on /now page"
            git push
          fi
```

### Python script (`bin/update-whoop.py`, key functions)

```python
import os, json, subprocess
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE  = "https://api.prod.whoop.com/developer/v2"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
TOKEN_ENC = ".whoop-token.enc"
UA        = "jameschang.co/1.0 (WHOOP personal dashboard; +https://jameschang.co)"

def decrypt_refresh_token(key: str) -> str:
    res = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-d", "-pbkdf2",
         "-in", TOKEN_ENC, "-pass", f"pass:{key}"],
        capture_output=True, text=True, check=True,
    )
    return res.stdout.strip()

def encrypt_refresh_token(token: str, key: str) -> None:
    subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-pbkdf2",
         "-out", TOKEN_ENC, "-pass", f"pass:{key}"],
        input=token, text=True, check=True,
    )

def refresh(client_id: str, client_secret: str, refresh_token: str) -> dict:
    body = urlencode({
        "grant_type":    "refresh_token",
        "refresh_token": refresh_token,
        "client_id":     client_id,
        "client_secret": client_secret,
    }).encode()
    req = Request(TOKEN_URL, data=body, headers={
        "User-Agent":   UA,
        "Accept":       "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urlopen(req) as r:
        return json.loads(r.read())

def main():
    key = os.environ["WHOOP_TOKEN_KEY"]
    cid = os.environ["WHOOP_CLIENT_ID"]
    sec = os.environ["WHOOP_CLIENT_SECRET"]

    rt  = decrypt_refresh_token(key)
    tok = refresh(cid, sec, rt)

    # CRITICAL: persist the rotated token before any subsequent network call.
    # If a data fetch fails after this, the commit still pushes the new cipher
    # and the next run recovers automatically.
    encrypt_refresh_token(tok["refresh_token"], key)

    access = tok["access_token"]
    # ... fetch /recovery, /activity/sleep, /cycle and render now/index.html ...
```

The ordering in `main()` is load-bearing: **encrypt and write the new refresh token to disk immediately** after the refresh call succeeds. If the subsequent data fetches fail partway through, the commit step still pushes the rotated token and the next run recovers on its own.

### Bootstrap: one-time callback page and encryption

Static OAuth callback (`whoop/callback/index.html`):

```html
<script>
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  document.body.textContent = code || 'No code in URL. Arrive here via the WHOOP OAuth flow.';
</script>
```

Manual seed (`bin/whoop-encrypt.sh`, run once locally after completing the auth code exchange):

```bash
# TOKEN = refresh_token from initial code exchange (whoop-auth.sh output)
# KEY   = passphrase (auto-generated; saved to GitHub Secret WHOOP_TOKEN_KEY)
echo "${TOKEN}" | openssl enc -aes-256-cbc -pbkdf2 \
  -out .whoop-token.enc -pass "pass:${KEY}"
git add .whoop-token.enc && git commit -m "whoop: seed token" && git push
```

After this, no manual step is ever required again.

## Architecture

```
                           ONE-TIME BOOTSTRAP (local)
                           ==========================
  Browser -> /whoop/callback/ -> copy code -> terminal
                                               |
                                               v
                                    POST /oauth2/token (auth code)
                                               |
                                               v
                                    refresh_token_v0
                                               |
                       openssl enc -aes-256-cbc -pbkdf2 (KEY)
                                               |
                                               v
                                    .whoop-token.enc  --commit-->  GitHub repo

                           DAILY LOOP (GitHub Actions)
                           ===========================

   +---------------------+        +------------------------------+
   |  GitHub Secrets     |        |  Repo @ HEAD                 |
   |  - WHOOP_CLIENT_ID  |        |  - .whoop-token.enc  (cipher)|
   |  - WHOOP_CLIENT_SEC |        |  - now/index.html            |
   |  - WHOOP_TOKEN_KEY  |        +---------------+--------------+
   +----------+----------+                        |
              |  (env)                            |  checkout
              v                                   v
   +------------------------------------------------------+
   |              Actions runner (ubuntu)                 |
   |                                                      |
   |  1. openssl -d  (.enc + KEY)  ->  refresh_token_vN   |
   |                                                      |
   |  2. POST token endpoint (client_secret_post + UA)    |
   |     <-- access_token + refresh_token_v(N+1)          |
   |                                                      |
   |  3. openssl enc  (v(N+1) + KEY) -> .whoop-token.enc  |
   |     [persist FIRST, before data calls]               |
   |                                                      |
   |  4. GET /developer/v2/{recovery,sleep,workout,cycle} |
   |                                                      |
   |  5. render now/index.html                            |
   |                                                      |
   |  6. git commit .whoop-token.enc + now/index.html     |
   |     git push  (contents: write)                      |
   +-----------------------+------------------------------+
                           |
                           v
                  Repo @ HEAD+1 (new cipher committed)
                           |
                           v
                 GitHub Pages rebuilds /now/
                           |
                           v
                  Next cron tick reads HEAD+1
```

The loop is closed and self-healing: every successful run leaves the repo in a valid state for the next run, with no writable surface required outside the repo itself.

## Prevention Strategies

- **Read the provider's full OAuth2 docs before coding** — confirm the current API version, token endpoint URL, required scopes, whether refresh tokens rotate, and their exact lifetime.
- **Verify the client authentication method** the provider expects (`client_secret_post`, `client_secret_basic`, PKCE, or mTLS). Check the `token_endpoint_auth_methods_supported` field or equivalent.
- **Check the provider's bot/WAF posture** — if they sit behind Cloudflare, Akamai, or similar, test a curl from a non-residential IP early. Confirm whether a `User-Agent` header is required.
- **Confirm GitHub Actions permissions up front** — know that `GITHUB_TOKEN` cannot write repository secrets or variables. Decide early: PAT, committed encrypted file, or external store.
- **Inventory your secrets' rotation cadence** before choosing a storage strategy. One-time secrets differ fundamentally from rotating-on-every-use refresh tokens.
- **Plan the bootstrap flow** — how does the first valid token get into the system? Do you have a safe way to re-seed if the chain breaks?

## Best Practices

- **One authoritative token store, one writer.** Pick the location (encrypted repo file, secret manager, KV store) and ensure only the scheduled job writes to it. Concurrent writers will race and corrupt a rotating chain.
- **Commit atomically after refresh.** Fetch, refresh, decrypt old token, call API, encrypt new token, commit — in one job run. If any step fails, the commit doesn't happen and the old token is preserved.
- **Run setup commands back-to-back when bootstrapping.** Interactive auth returns a token that may already be consumed if you pause. Script the entire "auth → encrypt → commit" sequence as a single command.
- **Pin a descriptive `User-Agent`** that identifies your project. Generic Python/Node UAs get blocked; identifying yours helps providers allowlist you.
- **Log the HTTP status and response body on every refresh.** Silent failures are the worst failure mode for unattended jobs.
- **Keep the encryption key in Actions secrets, the encrypted payload in the repo.** Never put both in the same place.
- **Add a canary**: a weekly workflow that just verifies the token refreshes successfully, independent of the data sync, so you learn of breakage before the daily job fails.

## Debugging Checklist

1. **Check the HTTP status**: 400 vs 401 vs 403 vs 429 each point to different root causes.
2. **401 invalid_grant** — token was already consumed, rotated without being saved, or expired. Check the last successful commit to the encrypted file.
3. **400 invalid_client / invalid_request** — wrong auth method (`_post` vs `_basic`), wrong client_id, or secret mismatch. Read the `error_hint`.
4. **403 or Cloudflare error code** — missing or generic User-Agent; check response headers for `cf-ray`.
5. **Verify the token endpoint URL and API version** — silent 404s or HTML responses usually mean wrong path.
6. **Verify scopes** haven't changed server-side; some providers revoke tokens when scopes are removed.
7. **Check clock skew** on the runner if JWT-based.
8. **Re-run the bootstrap** as a last resort, but only after confirming the chain is truly broken.

## When to Apply This Pattern

**Use encrypted-file-in-repo when:**
- The site is static (GitHub Pages, Netlify, S3) and you want zero runtime infrastructure.
- Refresh cadence is daily or slower — commit churn stays manageable.
- You control the repo and can protect the branch.
- Exactly one scheduled writer exists.

**Prefer a PAT or fine-grained token when:**
- The secret doesn't rotate on use (simple API keys, long-lived tokens).

**Prefer an external secret store (Doppler, Vault, AWS Secrets Manager) when:**
- Multiple workflows or machines need concurrent access.
- Rotation is sub-hourly, making repo commits noisy.
- Compliance requires audited secret access.

**Prefer a tiny serverless function (Cloudflare Worker, Lambda) when:**
- You need the token at request-time from the browser, not just at build-time.
- The API forbids storing credentials in source-controlled artifacts, even encrypted.
- You already pay for the platform and want to consolidate.

## Related

- **Prior docs**: None — this is the first solution doc in the repo.
- **Adjacent repo context**: `todos/020-complete-p1-cut-sync-pipeline.md` (inverse context — a prior sync pipeline that was removed; useful for background only).

**External references:**
- [WHOOP Developer Docs](https://developer.whoop.com/api/)
- [GitHub Actions — Encrypted secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [OAuth 2.0 (RFC 6749)](https://datatracker.ietf.org/doc/html/rfc6749)
- [OAuth 2.0 Refresh Token rotation (RFC 6749 §6)](https://datatracker.ietf.org/doc/html/rfc6749#section-6)
- [OAuth 2.0 Security Best Current Practice](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
