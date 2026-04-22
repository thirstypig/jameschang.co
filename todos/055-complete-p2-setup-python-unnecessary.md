---
status: done
priority: p2
issue_id: 055
tags: [code-review, performance]
dependencies: []
---

# actions/setup-python@v5 adds 20-30s cold start per workflow, unnecessary for stdlib-only scripts

## Problem
All three workflows use `actions/setup-python@v5` but the scripts use only Python stdlib (urllib, json, re, xml.etree). `ubuntu-latest` ships Python 3.12 pre-installed. The setup-python step adds 20-30s of cold start per run × 3 workflows × multiple runs/day = significant wasted CI minutes.

## Proposed Solutions
Remove the setup-python step from all three workflows. Change `python bin/update-*.py` to `python3 bin/update-*.py` (the pre-installed binary).

## Acceptance Criteria
- [ ] No actions/setup-python references; all three workflows run stdlib scripts against pre-installed python3.
