---
status: pending
priority: p2
issue_id: 126
tags: ['code-review', 'security', 'cross-repo-admin']
dependencies: []
---

# Sanitize titles before interpolating into commit messages

## Problem Statement
`BucketListManager.tsx:384,418,435,442,458` build commit messages by interpolating user-controlled `title` strings:

```ts
await commit(next, `Add "${title}" to bucket list`);
await commit(next, `Edit "${title}" in bucket list`);
await commit(next, `Mark "${item.title}" done`);
await commit(next, `Reopen "${item.title}"`);
await commit(next, `Remove "${item.title}" from bucket list`);
await commit(next, `Reorder "${target.title}"`);
```

Today `title` is operator-controlled and benign. **But** — if the bucket list ever accepts inbound entries from a webhook, a public form, or an automated agent, a title containing `\n\nCo-Authored-By: Someone Else <attacker@example.com>\n\n` would land in the git log as a fake co-author trailer. Other low-risk classes: title containing `\r` injecting carriage returns into the commit metadata, or extreme length pushing past GitHub's 72-char-first-line convention.

**Surfaced by:** security-sentinel during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Sanitize at the call site (recommended)
Add a tiny helper `safeTitle(s: string): string`:

```ts
const safeTitle = (s: string) => s.replace(/[\r\n\t]+/g, " ").trim().slice(0, 80);
```

Use everywhere a title gets interpolated:
```ts
await commit(next, `Add "${safeTitle(title)}" to bucket list`);
```

**Effort:** Small (~10 min)
**Risk:** Zero. Cosmetic for current operator-only use; defense-in-depth for the future.

### Option B — Move sanitization into `commit()`
Put it on the `message` parameter so every call site is automatically protected. Slightly less explicit at the call site but cheaper to enforce.

## Acceptance Criteria
- [ ] All six commit-message interpolations sanitize the title
- [ ] Pasting a title with `\n` doesn't produce a multi-line commit message
- [ ] Long titles get capped (80 chars is enough for "Add \"$title\" to bucket list" to fit in 72-char first line)
- [ ] HitListManager applies the same fix where it interpolates `name` into `commitMsg` (line 597)

## Resources
- `/Users/jameschang/Projects/thirstypig/tina/BucketListManager.tsx:384,418,435,442,458`
- `/Users/jameschang/Projects/thirstypig/tina/HitListManager.tsx:595` (same class of issue)
