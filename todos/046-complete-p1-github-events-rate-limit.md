---
status: done
priority: p1
issue_id: 046
tags: [code-review, performance, security]
dependencies: []
---

# GitHub events script makes up to N+1 unauth API calls, will hit 60/hr limit

## Problem
`bin/update-public-feeds.py:138` fetches `/repos/{repo}/commits/{sha}` inside the loop for every push event — a busy week with 60+ pushes exhausts the 60/hr anon rate limit partway through and the `except` silently returns partial data. Also wasteful: only top 5 events render, but every push event gets enriched.

## Proposed Solutions
Two changes: (1) Pass `Authorization: Bearer ${{ github.token }}` via workflow env to lift limit to 1000/hr (GITHUB_TOKEN is free inside the Action). (2) Move commit-enrichment after `recent = recent[:5]` slicing — enrich only what will render.

## Acceptance Criteria
- [ ] GitHub API calls authenticated with GITHUB_TOKEN
- [ ] Commit enrichment runs on at most 5 events per run
