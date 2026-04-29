---
status: pending
priority: p2
issue_id: 105
tags: ['code-review', 'security', 'rss']
dependencies: []
---

# RSS-sourced URLs not scheme-validated before HTML output

## Problem Statement
`bin/update-public-feeds.py:163,204,254` reads `link_el.text` from Letterboxd / Goodreads RSS and emits it inside `<a href="...">`. Strings are HTML-attribute-escaped, so no breakout, but a hostile upstream serving `href="javascript:..."` or `data:..."` would render. `now/now.js:60` correctly does `if (!/^https?:\/\//i.test(url)) return;` — same pattern should apply server-side.

Same applies to `pr.html_url` / `rel.html_url` / `commit` URLs in `bin/update-projects.py:215`.

**Surfaced by:** security-sentinel during /ce:review 2026-04-29.

## Proposed Solutions
### Option A: Add `_safe_url(s)` helper in `_shared.py`
- Returns the URL only if it begins with `http://` or `https://`, else `"#"` or empty
- Apply to all `link_el.text` ingest points and to `*.html_url` / `commit` fields
- **Effort:** Small (~30 min)

## Recommended Action
_(Filled during triage)_

## Acceptance Criteria
- [ ] `_safe_url()` exported from `_shared.py`
- [ ] All RSS-sourced URLs and GitHub event URLs pass through it
- [ ] Unit test for hostile schemes (javascript:, data:, file:)

## Work Log
| Date | Action | Notes |
|------|--------|-------|
| 2026-04-29 | Created | /ce:review whole-repo audit |
