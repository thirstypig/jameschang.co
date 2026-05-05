---
status: complete
priority: p3
issue_id: 135
tags: ['code-review', 'reliability', 'bucketlist']
dependencies: []
---

# Bucket list `last_updated` is admin-asserted, not commit-derived

## Problem Statement
`BucketListManager.tsx:351` writes `last_updated: new Date().toISOString()` from the operator's clock. A clock-skewed phone (or an agent in a misconfigured timezone) produces a value the renderer at `bucketlist/bucketlist.js:71-78` and `/now/now.js` trust uncritically.

Worse: the admin can write the file with `last_updated` UNCHANGED (the spec says "must update on every save" but it's not enforced). An agent committing directly via git might forget the field entirely.

The git commit metadata already records authoritative timestamps. The renderer could derive `last_updated` from the latest commit touching `bucketlist.json`.

**Surfaced by:** architecture-strategist during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Defer until it bites
Currently the field is informational only ("// last updated May 4, 2026" eyebrow on /bucketlist/). A wrong date is cosmetic. Document as "best effort, may be skewed" in `docs/bucketlist-admin-spec.md` (covered by todo 130 augmentation).

**Effort:** Trivial (~5 min in the spec doc)
**Risk:** None.

### Option B — Drop the field entirely
Pull the date from the GitHub Pages response headers (`Last-Modified`) at fetch time on the public side. Or add a small `bin/update-bucketlist-stamp.py` cron that rewrites `last_updated` to the latest `git log -1 --format=%cI` for the file. Either solution is more code than the field is worth right now.

### Option C — Validate via test
Schema test rejects values older than the file's git mtime. Most expensive, least valuable.

## Recommended Action
**Option A.** Document as best-effort. The spec already implies it; just make the implication explicit. Promote to P2 only if a real wrong-date causes operator confusion.

## Acceptance Criteria
- [ ] `docs/bucketlist-admin-spec.md` notes that `last_updated` is admin-asserted and may be skewed; renderer should display but not rely on its accuracy

## Resources
- `BucketListManager.tsx:351`
- `bucketlist/bucketlist.js:71-78`
