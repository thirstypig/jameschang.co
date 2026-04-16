---
status: pending
priority: p1
issue_id: 048
tags: [code-review, reliability, architecture]
dependencies: []
---

# whoop-sync.yml lacks git pull --rebase + concurrency guard, races with other workflows

## Problem
`.github/workflows/whoop-sync.yml:38` pushes without rebasing. Both whoop-sync (`0 10 * * *`) and public-feeds-sync (`15 */6 * * *`) can fire at 10:00 UTC. Spotify has `git pull --rebase origin main` as a defensive; WHOOP does not — a non-fast-forward push fails. Additionally all three workflows lack `concurrency:` blocks so two manual `workflow_dispatch` runs can interleave and corrupt state (especially critical for WHOOP's token rotation).

## Proposed Solutions
Add `git pull --rebase origin main` to whoop-sync.yml before push. Add a concurrency block to all three workflows:
```yaml
concurrency:
  group: now-html-writer
  cancel-in-progress: false
```

## Acceptance Criteria
- [ ] Three parallel `workflow_dispatch` runs across the three workflows serialize correctly
- [ ] whoop-sync never loses a push to a non-fast-forward rejection
