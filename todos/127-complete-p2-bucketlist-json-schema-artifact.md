---
status: pending
priority: p2
issue_id: 127
tags: ['code-review', 'architecture', 'cross-repo-admin', 'bucketlist']
dependencies: []
---

# Schema lives in three places — promote to a shared JSON Schema

## Problem Statement
The bucket list contract is currently described in three independent artifacts that don't cross-validate at build time:

1. **`docs/bucketlist-admin-spec.md`** — prose for human readers.
2. **`tina/BucketListManager.tsx:18-35`** — TypeScript interfaces (admin's view).
3. **`tests/test_site_e2e.py::TestBucketList`** — runtime asserts (renderer's view).

Failure modes:
- **Add a field on the admin only** → the public test still passes (extra keys ignored), but the renderer doesn't know about it. Field is dead until the renderer ships.
- **Add a field on the renderer only** → the admin can't write it, so it's effectively unsettable.
- **Change a type** → the prose drifts silently.

This is the architectural seam the architecture-strategist flagged most strongly. The cross-repo solution doc already calls out the schema-as-contract idea but doesn't operationalize it.

**Surfaced by:** architecture-strategist and agent-native-reviewer during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Ship a `bucketlist.schema.json` (recommended)
Commit a JSON Schema file at the repo root next to `bucketlist.json`:

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "BucketList",
  "type": "object",
  "required": ["items", "last_updated"],
  "properties": {
    "items": {
      "type": "array",
      "items": { "$ref": "#/definitions/item" }
    },
    "last_updated": { "type": "string", "format": "date-time" }
  },
  "definitions": {
    "item": { ... }
  }
}
```

Three consumers:
- **Admin (TypeScript):** import via `import schema from '../jameschang.co/bucketlist.schema.json'` (or fetch at admin-load) and validate with a tiny JSON-schema validator (zod-from-json-schema, or hand-rolled). Replaces the type guard from todo 122.
- **e2e test (Python):** load the schema and validate every item with `jsonschema` (one new pip dep, justified). Replaces the hand-coded checks from todo 121.
- **Spec doc:** keep prose, but add `<!-- generated from bucketlist.schema.json -->` at the top so the source-of-truth is unambiguous.

**Effort:** Medium (~2 hours including the validator wiring)
**Risk:** Low. Same checks, fewer copies.

### Option B — Generate types from the schema
Run `json-schema-to-typescript` at admin build time → `BucketListItem` and `BucketListData` types come from the same source. More tooling. Defer until the schema is stable for a few weeks.

### Option C — Leave alone
Two repos, two writers. Tolerable today; pre-mortem says "first regression from drift will sting." Reasonable to defer until that regression actually happens. Mark this todo `discarded` if you want to wait.

## Recommended Action
**Option A** is the right size. JSON Schema is the universal interchange; both languages consume it natively. Defer Option B until you ship the second schema-bearing managed file (e.g., a quotes file, a reading list).

## Acceptance Criteria
- [ ] `bucketlist.schema.json` committed at repo root
- [ ] e2e test loads + validates against the schema
- [ ] Admin loads + validates on read AND before write
- [ ] Spec doc cross-references the schema file
- [ ] Closing-the-loop test: planted bad fixture (e.g., extra `urgent` priority) is rejected by both sides

## Resources
- `docs/solutions/integration-issues/cross-repo-admin-via-github-contents-api.md`
- Any JSON Schema validator: `ajv` (TS), `jsonschema` (Python pip)

## Work Log
- 2026-05-05: Shipped `bucketlist.schema.json` as the contract artifact. Validator wiring on both sides (Python `jsonschema` lib in test_site_e2e.py, TS validator in BucketListManager) deferred — to be picked up alongside todos #121 and #122 once those land.
