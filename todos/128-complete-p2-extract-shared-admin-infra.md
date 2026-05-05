---
status: pending
priority: p2
issue_id: 128
tags: ['code-review', 'cross-repo-admin', 'architecture', 'thirstypig']
dependencies: []
---

# Extract shared cross-repo admin infrastructure

## Problem Statement
`BucketListManager.tsx` and `HitListManager.tsx` duplicate four blocks verbatim:

1. `base64ToUtf8` / `utf8ToBase64` (UTF-8 safe encoding helpers)
2. `githubGet(token)` and `githubPut(token, content, sha, message)` (Contents API wrappers)
3. The token-paste form UI + sessionStorage load/save/clear
4. The message banner styling + auto-dismiss timer

Both manager files needed identical edits this session for the shared-PAT migration (commit `d64bdb85`). The next time a security finding lands (todos 123, 124, 126 above all touch both files) the same edit happens twice. As soon as a third managed-JSON file ships (e.g., a quotes file, reading list, recipe index), the copy-paste rot becomes a problem.

**Surfaced by:** kieran-typescript-reviewer (#5), architecture-strategist (#4) during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Extract `tina/_shared/github-contents.ts` (recommended)
Pure utilities only. Keep UI per-manager since the help copy is repo-specific:

```ts
// tina/_shared/github-contents.ts
export function base64ToUtf8(b64: string): string { ... }
export function utf8ToBase64(s: string): string { ... }

export interface GithubContents { content: string; sha: string; }

export async function githubGet(
  token: string, owner: string, repo: string, path: string
): Promise<GithubContents> { ... }

export async function githubPut(
  token: string, owner: string, repo: string, path: string,
  newContent: string, sha: string, message: string
): Promise<string /* new sha */> { ... }
```

Each manager imports + supplies the (owner, repo, path) tuple. ~150 LOC removed across the two files.

**Effort:** Small-medium (~1 hour including a small unit test for base64 round-trip)
**Risk:** Low. Drop-in extraction; behavior identical.

### Option B — Full factory
`createJsonFileManager({ owner, repo, path, schema, renderRow, sortFn })` produces a complete React screen. Much more reusable but a bigger refactor and probably premature until the third file lands. Architecture-strategist recommends this for the third instance, not yet.

### Option C — Defer
Two managers is bearable; revisit when the third arrives. Reasonable.

## Recommended Action
**Option A now, Option B when the third file lands.** Option A is small enough that the next bug fix (e.g., 401 handling per todo 124) gets a single-file fix instead of two.

## Acceptance Criteria
- [ ] `tina/_shared/github-contents.ts` exists with the four exports above
- [ ] Both managers import from it
- [ ] Both files compile (`npx tsc --noEmit` passes)
- [ ] Manual smoke test: hitlist add still works, bucketlist add still works
- [ ] The 401/sha-conflict fixes (todos 123, 124) become single-file changes after this lands

## Resources
- `/Users/jameschang/Projects/thirstypig/tina/HitListManager.tsx:196-237` (helpers)
- `/Users/jameschang/Projects/thirstypig/tina/BucketListManager.tsx:170-211`
