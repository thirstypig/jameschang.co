---
status: done
priority: p2
issue_id: 053
tags: [code-review, compliance]
dependencies: []
---

# Privacy policy omits GitHub, MLB, Letterboxd, FBST integrations

## Problem
`privacy/index.html` documents WHOOP and Spotify but not the four integrations added in `update-public-feeds.py`: GitHub public events, MLB Stats API, Letterboxd RSS, FBST public standings. All public APIs with no visitor data, but the policy's implicit claim of completeness is now inaccurate.

## Proposed Solutions
Add a "Public activity feeds" section listing the four sources and stating they display the site owner's public activity only — no visitor data collected or stored.

## Acceptance Criteria
- [ ] privacy/index.html mentions all four public-feed sources with accurate scope description.
