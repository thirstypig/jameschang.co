# Bucket list admin spec — for thirstypig.com/admin

The bucket list on jameschang.co is a flat JSON file. It's rendered client-side on `/bucketlist/` (full list) and `/now/` (top 5 todos). Order in `items[]` is the priority order — drag-reorder = rewrite the array.

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
      "completed_date": "ISO 8601 date string, or null when status=todo"
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
| Reorder         | Rewrite `items[]` in the new order — array order IS priority                     |
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
