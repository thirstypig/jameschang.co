---
status: complete
priority: p1
issue_id: 122
tags: ['code-review', 'security', 'cross-repo-admin', 'bucketlist']
dependencies: []
---

# BucketListManager: JSON.parse cast is unsafe — runtime crash on malformed file

## Problem Statement
`tina/BucketListManager.tsx:295` and `:312` cast `JSON.parse(content)` and `(await resp.json())` to `BucketListData` with no runtime validation. If `bucketlist.json` is hand-edited on github.com to a malformed shape (e.g., `items` becomes an object instead of an array, or an item is missing `id`), the admin UI crashes hard:

- `data.items || []` saves us from a missing `items` key, but if `items` is `{...}` not `[]`, every downstream `.map`/`.filter`/`.find` blows up.
- Items missing `id` produce ghost rows that can't be edited or deleted (the row identity is lost).

The sibling `HitListManager.tsx:776-780` validates required fields with explicit checks before mutating. Bucket list manager doesn't.

This is P1 because the admin is the SOLE write path for non-developers. A crash here means the operator can't recover the file without dropping into a terminal — defeats the purpose of the cross-repo admin.

**Surfaced by:** kieran-typescript-reviewer (#4) during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Type guard before set state (recommended)
Add a small `parseBucketList(raw: unknown): BucketListData` function:

```ts
function parseBucketList(raw: unknown): BucketListData {
  if (!raw || typeof raw !== "object") throw new Error("bucketlist.json: expected object");
  const r = raw as Record<string, unknown>;
  if (!Array.isArray(r.items)) throw new Error("bucketlist.json: items must be array");
  const items = r.items.filter(
    (it): it is BucketListItem =>
      it && typeof it === "object" && typeof (it as { id?: unknown }).id === "string"
        && typeof (it as { title?: unknown }).title === "string"
  );
  return { items, last_updated: typeof r.last_updated === "string" ? r.last_updated : "" };
}
```

Use in both load paths (`reload` and `loadPublicReadOnly`). Items missing `id`/`title` are silently dropped; the operator sees a count mismatch and can investigate.

**Effort:** Small (~20 min)
**Risk:** Low — additive guard. Could surface "lost items" via a console warn.

### Option B — Surface validation errors as a banner
Same parser, but raise on any malformed item and show "row N skipped: missing id" in the message banner. More transparent, slightly more code.

## Acceptance Criteria
- [ ] `parseBucketList` covers `items` shape and per-item `id`/`title` types
- [ ] `reload()` and `loadPublicReadOnly()` both go through it
- [ ] Manually corrupted local copy (e.g., `items: {}`) shows a friendly error, doesn't crash the React tree
- [ ] HitListManager pattern matched as much as possible

## Resources
- `/Users/jameschang/Projects/thirstypig/tina/BucketListManager.tsx:295,312`
- `/Users/jameschang/Projects/thirstypig/tina/HitListManager.tsx:776-780` (existing pattern)
