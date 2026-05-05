---
status: pending
priority: p2
issue_id: 130
tags: ['code-review', 'documentation', 'cross-repo-admin', 'agent-native']
dependencies: []
---

# Augment bucketlist-admin-spec.md with missing failure modes + agent paths

## Problem Statement
The current `docs/bucketlist-admin-spec.md` is the contract between admin and renderer, and the canonical "how would an agent do this" doc. It's missing several real concerns surfaced during the review:

1. **`id` derivation rules** — the admin slugifies title → kebab + dedupe `-2`/`-3` suffix (`BucketListManager.tsx:214-229`). An agent generating raw UUIDs would technically be valid but break the "stable kebab id" expectation downstream code relies on. Not in spec.

2. **Reorder semantics restricted to within-status** — admin only swaps within the same `status` bucket (`BucketListManager.tsx:447`) because the public renderer groups by status. Spec says "Rewrite items[]" without that caveat. An agent reordering across buckets would do invisible churn.

3. **Direct-commit path for agents with clone access** — spec only documents the GitHub Contents API. Agents with repo write access can `git commit && push` directly, faster and PAT-free. Not mentioned.

4. **PAT expiry runbook** — fine-grained PATs max at 1 year; should be rotated every 90 days. Spec doesn't say where to set up rotation reminders or what to do on expiry.

5. **409 conflict recovery** — see todo 123. Spec doesn't tell the writer what to do.

6. **Branch protection / required reviews** — if `main` ever gains protection, every PUT 422s. Spec assumes `main` accepts direct writes.

7. **Atomicity** — admin commits one item per action. Multi-edit (reorder five rows) creates five commits. Document the choice.

8. **Pages CDN cache window** — GitHub Pages serves with `max-age=600`. A save lands on github but `bucketlist.json` may be stale-from-CDN for up to 10 minutes despite `cache: 'no-cache'` on the fetch. Document or use `cache: 'reload'`.

**Surfaced by:** agent-native-reviewer (F2, F3, F6) and architecture-strategist (#3) during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Add a "Failure modes & gotchas" section + an "Agent direct-commit" section (recommended)

Add to `docs/bucketlist-admin-spec.md`:

```markdown
## Agent direct-commit (alternative to GitHub Contents API)

Agents with clone access to thirstypig/jameschang.co can edit `bucketlist.json`
and commit + push to `main` directly. The Contents API path is the
browser-admin's mechanism; the canonical interface is the JSON file in the repo.

## id derivation
Use kebab slug from title (lowercase, ASCII only, dashes for non-alphanumeric),
deduped with `-2`, `-3`, ... suffix. The admin enforces this; agents writing
directly should follow the same convention.

## Reorder
Order matters only WITHIN a single `status` bucket. Cross-bucket moves are
no-ops at render time (the renderer groups by status, then sorts by priority,
then by array order).

## Failure modes
- **PAT expiry**: rotate every 90 days. Set a calendar reminder.
- **409 conflict**: refetch sha, replay your write, retry once.
- **422 on PUT**: usually means branch protection added on `main`. Spec assumes
  unrestricted main.
- **Pages CDN staleness**: ~10 minute window after a write before all CDN edges
  serve the new file.
- **Atomicity**: one mutation = one commit. No batch endpoint. Multi-edits
  create commit-spam in git log.
```

**Effort:** Small (~30 min)
**Risk:** None — pure documentation.

### Option B — Skip; let agents read the source
Reasonable if the spec is purely for the admin. Less reasonable for the agent-native principle in CLAUDE.md.

## Acceptance Criteria
- [ ] All 8 items above documented in `docs/bucketlist-admin-spec.md`
- [ ] Spec cross-links the schema test in `tests/test_site_e2e.py::TestBucketList`
- [ ] Spec links the cross-repo solution doc

## Resources
- `docs/bucketlist-admin-spec.md` (current)
- `BucketListManager.tsx:214-229,445-459` (id and reorder logic)
