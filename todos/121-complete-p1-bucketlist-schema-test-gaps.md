---
status: complete
priority: p1
issue_id: 121
tags: ['code-review', 'testing', 'agent-native', 'bucketlist']
dependencies: []
---

# TestBucketList misses key invariants — agent-native gap

## Problem Statement
The schema tests added in `tests/test_site_e2e.py::TestBucketList` (commit `521b464`) are asymmetric and miss enforceable invariants from the contract at `docs/bucketlist-admin-spec.md`. An external writer (the cross-repo admin OR an agent committing directly) can land subtly invalid state that the public renderer trips on at runtime, while CI passes.

Concretely:

1. **`status==done` is unconstrained.** Test enforces `status==todo → completed_date is null` (line 937), but not the converse. An agent writing `{"status":"done","completed_date":null}` passes CI but the renderer's "✓ done <date>" line shows literal "✓ done " with nothing after it. Spec §Admin actions explicitly says "Mark done → flip status, set completed_date to today (UTC ISO)" — needs a test.

2. **`note` and `title` aren't type-checked.** `REQUIRED_KEYS` enforces presence but not shape. `"note": null` passes the current test (key exists, value is None) and the renderer's `if (item.note)` skips it silently. `"title": null` would render `null` literally as a `<strong>null</strong>`.

3. **`last_updated` isn't validated.** Spec says "ISO 8601 timestamp — admin must update on every save." Not parsed by the test; an agent writing `"last_updated": "yesterday"` passes.

This is a P1 because the cross-repo admin pattern (just shipped) explicitly relies on consumer-side schema enforcement to compensate for the fact that two separate repos write to this file. If the test isn't strict, the contract isn't enforceable.

**Surfaced by:** agent-native-reviewer (F1, F4) and architecture-strategist during /ce:review 2026-05-05.

## Proposed Solutions

### Option A — Tighten existing test in place (recommended)
Add three assertions to `test_every_item_has_required_schema`:
- `if item.get("status") == "done" and item.get("completed_date") is None: failures.append(...)`
- `if not isinstance(item.get("title"), str): failures.append(...)`
- `if not isinstance(item.get("note"), str): failures.append(...)` (allow empty `""`, reject `None`)

Add a separate `test_last_updated_is_valid_iso8601`:
- Parse with `datetime.fromisoformat`, fail on `ValueError`.

**Effort:** Small (~15 min including writing the failing-case fixtures)
**Risk:** Low — additive; current 11 seed items pass all four checks.

### Option B — Switch to JSON Schema validator
Ship a `bucketlist.schema.json` and validate with `jsonschema` Python package. Heavier; pulls in a new dep (currently zero pip deps for tests beyond pytest). Better when the schema gets >5 fields. Defer until then.

## Acceptance Criteria
- [ ] All four new assertions in `TestBucketList`
- [ ] Test fails on a planted bad fixture (one for each rule)
- [ ] All 11 current seed items pass
- [ ] Spec doc cross-references these test rules

## Resources
- `tests/test_site_e2e.py::TestBucketList` (lines 906-955)
- `docs/bucketlist-admin-spec.md` (the contract)
- `bucketlist.json` (current data)
