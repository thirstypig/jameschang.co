---
status: pending
priority: p1
issue_id: 021
tags: [code-review, bug, content]
dependencies: []
---

# Broken link on /now/: Thirsty Pig "rebuild case study" points to Fantastic Leagues tech page

## Problem

`/now/index.html:140` under the Thirsty Pig module:
```html
running itself. See the
<a href="/work/fantastic-leagues/tech/">rebuild case study</a>.
```

Wrong target. Readers click "rebuild case study" expecting Thirsty Pig content and land on FBST architecture.

## Proposed Solutions

### Option A (Recommended): Link to the Thirsty Pig case study on the homepage
```html
<a href="/#case-studies">rebuild case study</a>
```
But `#case-studies` no longer exists as a nav anchor (removed in recent simplification). Works as an ID if the section still has one — verify.

### Option B: Link to the live site
```html
<a href="https://thirstypig.com">see it live</a>
```
Simpler; matches other Thirsty Pig mentions on the site.

### Option C: Remove the link
Drop "See the rebuild case study" sentence entirely.

## Acceptance Criteria
- [ ] `/now/` has no links pointing to mismatched content
- [ ] If linking to case study, section ID resolves
- [ ] Click-through from /now/ Thirsty Pig leads to Thirsty Pig content (or no link)

## Resources
- pattern-recognition review 2026-04-15, H1
