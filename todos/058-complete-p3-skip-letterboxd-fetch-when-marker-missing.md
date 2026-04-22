---
status: done
priority: p3
issue_id: 058
tags: [code-review, performance]
dependencies: []
---

# Letterboxd fetch fires even when LETTERBOXD marker is absent

## Problem
`bin/update-public-feeds.py:289` calls `letterboxd_block()` unconditionally. If someone removes the `<!-- LETTERBOXD-START -->` marker from /now, the network call still happens, and `replace_marker` just warns. Couples network cost to HTML shape.

## Proposed Solutions
Read now/index.html first; only call block-builder functions whose START marker appears in the content. Trivial check.

## Acceptance Criteria
- [ ] No network call for a feed whose marker isn't present in the HTML.
