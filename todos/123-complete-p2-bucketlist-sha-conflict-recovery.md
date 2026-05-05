---
status: pending
priority: p2
issue_id: 123
tags: ['code-review', 'cross-repo-admin', 'bucketlist', 'reliability']
dependencies: []
---

# 409 sha conflict has no auto-recovery — user gets stuck

## Problem Statement
`BucketListManager.tsx:354` PUTs to GitHub with the locally-cached `sha`. On 409 (concurrent edit from another tab, manual GitHub web edit, or a future cron writer), GitHub rejects the write and the local `sha` stays stale. **Every subsequent save also 409s** until the user manually clicks "(reload from GitHub)" — but the error message just says `"GitHub PUT failed: 409 Conflict"`. User sees a generic failure, retries, fails again, gets frustrated.

Compounds with rapid clicks: if `submitting` flips one render-cycle late, two near-simultaneous mutations can both stomp the same sha.

**Surfaced by:** kieran-typescript-reviewer (#1) and architecture-strategist during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Detect 409 in `commit()`, auto-reload, surface friendly retry (recommended)

```ts
async function commit(nextItems: BucketListItem[], message: string) {
  // ... existing prelude ...
  try {
    const newSha = await githubPut(token, payload, sha, message);
    setItems(nextItems);
    setSha(newSha);
    setMessage({ type: "success", text: `Saved · ${message} · ...` });
  } catch (e) {
    if ((e as Error).message.includes("409")) {
      // Concurrent edit collided. Pull the fresh state and tell user to retry.
      await reload(token);
      setMessage({
        type: "error",
        text: "Someone else (or another tab) just saved. Reloaded — please re-apply your change.",
      });
    } else {
      setMessage({ type: "error", text: `Save failed: ${(e as Error).message}` });
    }
  }
}
```

Also add a `if (submitting) return;` guard at the top of every mutation handler (`handleAdd`, `saveEdit`, `toggleDone`, `handleDelete`, `move`) as belt-and-suspenders even though `disabled={submitting}` already gates the button.

**Effort:** Small (~30 min)
**Risk:** Low. Worst case the user re-types one edit.

### Option B — Diff-merge on conflict
Auto-reapply the user's pending change on top of the freshly-fetched list. Brittle because the change may collide with the upstream change in a way that isn't obvious. Skip until needed.

## Acceptance Criteria
- [ ] Simulated 409 (open two admin tabs, edit in both) shows "Reloaded — please re-apply"
- [ ] Sha state is correct after the auto-reload
- [ ] Form state (in-progress edit) preserves what the user typed when possible
- [ ] All five mutation handlers gated against `submitting`

## Resources
- `/Users/jameschang/Projects/thirstypig/tina/BucketListManager.tsx:341-363,445-459`
