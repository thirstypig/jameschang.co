---
status: done
priority: p2
issue_id: 035
tags: [code-review, security]
dependencies: []
---

# Remove TODO comments from production HTML

## Problem
Two HTML comments at index.html lines ~241-242 contain personal drafting notes: `<!-- TODO (James): add direct-report or PM-mentee count ... -->` and one about ARR numbers. These are visible to anyone who views source and leak internal thinking about what data was considered including.

## Proposed Solutions
Remove both TODO comments from the HTML. Keep them in a separate task tracker.

## Acceptance Criteria
- [ ] No `<!-- TODO` comments in any production HTML file.
