# Bucket list admin spec — for thirstypig.com/admin

The bucket list on jameschang.co is a flat JSON file. It's rendered client-side on `/bucketlist/` (full list) and `/now/` (top 5 todos). Sort order: priority desc (high → medium → low → unset), with array order as the tiebreaker within each priority bucket. Drag-reorder rewrites the array, which controls ordering *within* the same priority.

## Source of truth

`https://github.com/thirstypig/jameschang.co/blob/main/bucketlist.json`

## Schema

```json
{
  "items": [
    {
      "id": "string (stable kebab slug or UUID — used as React key / dedupe)",
      "title": "string (required, the visible label)",
      "note": "string (optional 1-line context, shown as ' — note' after the title)",
      "status": "todo | done",
      "completed_date": "ISO 8601 date string, or null when status=todo",
      "priority": "high | medium | low | null",
      "difficulty": "easy | hard | null"
    }
  ],
  "last_updated": "ISO 8601 timestamp — admin must update on every save"
}
```

## Admin actions

| Action          | Effect on JSON                                                                   |
|-----------------|----------------------------------------------------------------------------------|
| Add item        | `items.push({...})` with a fresh `id`, `status:"todo"`, `completed_date:null`    |
| Edit item       | Mutate `title` / `note` in place                                                 |
| Delete item     | Splice out of `items[]` by `id`                                                  |
| Reorder         | Rewrite `items[]` in the new order — drives ordering *within* a priority bucket  |
| Set priority    | Radio: `high` / `medium` / `low`. Drives the primary sort on /bucketlist/ + /now |
| Set difficulty  | Radio: `easy` / `hard`. Display chip; not a sort key                             |
| Mark done       | Flip `status` → `"done"`, set `completed_date` to today (UTC ISO)                |
| Re-open         | Flip `status` → `"todo"`, set `completed_date` → null                            |

Every save must also update `last_updated` to the current ISO timestamp.

## GitHub API

Read:

```
GET https://api.github.com/repos/thirstypig/jameschang.co/contents/bucketlist.json
Authorization: Bearer <PAT>
Accept: application/vnd.github+json
```

Response includes `content` (base64), `sha` (required for the next write).

Write:

```
PUT https://api.github.com/repos/thirstypig/jameschang.co/contents/bucketlist.json
Authorization: Bearer <PAT>
Body: {
  "message": "chore(bucketlist): <human description>",
  "content": "<base64 of new JSON, with trailing newline>",
  "sha": "<sha from the read>",
  "branch": "main"
}
```

GitHub Pages redeploys within ~60 seconds — no further action needed.

## PAT scope

Fine-grained personal access token with **Contents: Read and Write** on `thirstypig/jameschang.co`. Same token can have the same scope on `thirstypig/thirstypig.com` so one token serves both the hitlist and the bucket list admin.

## Validation

The renderer is forgiving but the admin should enforce on save:
- `id` is unique within `items[]`
- `title` is non-empty
- `status` is one of `"todo"` / `"done"`
- `completed_date` is either null or a valid ISO date

## Public surfaces (read-only)

- `https://jameschang.co/bucketlist/` — full list, two groups (Want to do / Done)
- `https://jameschang.co/now/` — top 5 `status:"todo"` items in priority order, with a "see the full list →" link

Both fetch `/bucketlist.json` directly (same-origin), so changes appear within ~60s of the GitHub Pages redeploy.

## Agent direct-commit (alternative to GitHub Contents API)

Agents with clone access to `thirstypig/jameschang.co` can edit `bucketlist.json` and commit + push to `main` directly. The Contents API path is the browser admin's mechanism; the canonical interface is the JSON file in the repo.

## id derivation

Use kebab-case slug from title (lowercase, ASCII only, dashes for non-alphanumeric), deduped with `-2`, `-3`, ... suffix. The admin enforces this; agents writing directly should follow the same convention.

## Reorder semantics

Order matters only WITHIN a single `status` bucket. Cross-bucket moves are no-ops at render time (the renderer groups by status, then sorts by priority, then by array order).

## Failure modes

- **PAT expiry**: rotate every 90 days. Set a calendar reminder.
- **409 conflict**: refetch sha, replay your write, retry once. The admin auto-recovers (see todo 123).
- **422 on PUT**: usually means branch protection got added to `main`. Spec assumes unrestricted main.
- **401/403**: token expired or scope is wrong (see todo 124). Admin auto-clears the dead token and re-prompts.
- **GitHub Pages CDN staleness**: ~10 minute window after a write before all CDN edges serve the new file. The renderer fetches with `cache: 'reload'` to force network revalidation, but downstream CDN edges may still be stale briefly.
- **Atomicity**: one mutation = one commit. No batch endpoint. Multi-edits create commit-spam in git log.

## last_updated field

The `last_updated` field is **admin-asserted**, not commit-derived. Operator clock skew or an agent-direct-commit that forgets to bump it can produce inaccurate timestamps. Display only — do not rely on it for ordering or freshness logic.
