---
status: complete
priority: p3
issue_id: 113
tags: ['code-review', 'python', 'quality']
dependencies: []
---

# `bin/_shared.py` quality polish: type hints, encoding, narrow excepts, dead imports

## Problem Statement
Cluster of small Pythonic-polish findings in `bin/_shared.py` and callers, each individually low-impact but collectively worth one cleanup pass:

1. **No type hints on public helpers.** `escape_html`, `relative_time`, `relative_time_html`, `replace_marker`, `content_changed`, `sanitize_error`, `record_heartbeat` have no annotations. Per kieran-python standard, public functions in shared modules should be hinted.
2. **`open(...)` calls without `encoding="utf-8"`** at lines 45, 59, 80, 100. Most paths handle ASCII JSON, but be explicit.
3. **`bare except Exception:`** in `sanitize_error` at line 204 with no comment. Add one-line justification.
4. **`bin/update-public-feeds.py:73`** `except Exception: continue` swallows everything from a date parse — narrow to `(ValueError, AttributeError)` or comment.
5. **`bin/update-public-feeds.py:122`** `except (HTTPError, URLError, KeyError)` for `mlb_block` — `KeyError` shouldn't be reachable; drop or comment.
6. **`bin/check-feed-health.py:88`** `datetime.fromisoformat(last)` has no naive-tz defense. Wrap in try/except or `.replace(tzinfo=timezone.utc)` if naive.
7. **Dead imports.** `bin/_shared.py:8-15` imports `HTTPError` / `URLError` (unused); `bin/check-feed-health.py:23` imports `timedelta` (unused).
8. **`bin/_shared.py:3-4`** docstring lists incomplete callers ("update-whoop, update-spotify, update-public-feeds") — actually used by all 6 sync scripts. Drop the list rather than maintain it.

**Surfaced by:** kieran-python-reviewer + code-simplicity-reviewer during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Single PR-equivalent commit covering all polish
- One sweep across `_shared.py`, `update-public-feeds.py`, `check-feed-health.py`
- Add type hints, fix encodings, narrow excepts, drop dead imports, fix docstrings
- **Effort:** Medium (~1-2h with test verification)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] All public functions in `_shared.py` have type hints
- [ ] All `open()` calls in `bin/` specify `encoding="utf-8"`
- [ ] No bare `except Exception:` without a justifying comment
- [ ] No unused imports
- [ ] `mypy bin/_shared.py` (if added) passes

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
