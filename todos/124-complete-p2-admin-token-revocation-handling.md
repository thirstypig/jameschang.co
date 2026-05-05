---
status: pending
priority: p2
issue_id: 124
tags: ['code-review', 'cross-repo-admin', 'security', 'ux']
dependencies: []
---

# 401/403 from GitHub leaves user stranded with dead token

## Problem Statement
When the GitHub PAT expires, gets revoked, or has insufficient scope mid-session, both managers (`BucketListManager.tsx`, `HitListManager.tsx`) surface the failure as a generic `"GitHub PUT failed: 401 Unauthorized"` message and leave the dead token in sessionStorage. The user has to know to click "(change)" to re-enter — the form doesn't auto-prompt, and the error doesn't suggest the action.

Common triggers:
- Fine-grained PAT 90-day expiry (the most likely real-world case)
- User regenerated PAT but forgot to update sessionStorage
- PAT was issued without `Contents: Read+Write` on one of the two repos (403 on that repo only — even more confusing)

**Surfaced by:** kieran-typescript-reviewer (#3) during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Auto-clear and re-prompt on 401/403 (recommended)

In both `BucketListManager.tsx` and `HitListManager.tsx`, in the `commit`/`handleSubmit` catch block:

```ts
} catch (e) {
  const msg = (e as Error).message;
  if (msg.includes("401") || msg.includes("403")) {
    clearToken();
    setMessage({
      type: "error",
      text: "Token rejected (401/403). It may have expired or lack Contents: Read+Write on this repo. Please re-enter.",
    });
  } else if (msg.includes("409")) {
    // see todo 123
  } else {
    setMessage({ type: "error", text: `Save failed: ${msg}` });
  }
}
```

For 403 specifically, surface "or lack the right scope" so the user knows to check repo selection on the PAT page.

**Effort:** Small (~15 min, same pattern in both managers)
**Risk:** Low.

### Option B — Preflight token on save
Before paste-saving the token, call `GET /repos/thirstypig/jameschang.co` (or just `bucketlist.json`) and verify 200. Surfaces scope errors at paste time, not write time. Combined with Option A this would be very tight.

## Acceptance Criteria
- [ ] 401 error → token cleared, form re-shown, banner explains why
- [ ] 403 error → same, with hint about scope mismatch
- [ ] Other errors still surface generically (don't false-positive on a network blip)
- [ ] Both managers updated identically (or fix is in shared infra — see todo 128)

## Resources
- `/Users/jameschang/Projects/thirstypig/tina/BucketListManager.tsx:184-192,341-363`
- `/Users/jameschang/Projects/thirstypig/tina/HitListManager.tsx:204-237,543-625`
