---
status: complete
priority: p3
issue_id: 140
tags: ['code-review', 'documentation', 'projects-sync', 'security']
dependencies: []
---

# Fix PAT scope documentation in CLAUDE.md

## Problem Statement

CLAUDE.md's `Required GitHub Secret` bullet for `TLDR_FETCH_TOKEN` says the PAT needs `Contents:Read` on "every repo listed in `bin/projects-config.json`'s `shipping_repos`". This is wrong: `shipping_repos` drives the GitHub Events API (which is public and doesn't need a PAT); the token needs `Contents:Read` on the `repo` field (singular), which is the CLAUDE.md fetch source.

For most projects `repo` and `shipping_repos[0]` are the same, masking the bug — but ktv-singer proves they can diverge. Whoever rotates the PAT next (~2026-07-22) may grant access to the wrong set of repos.

**Surfaced by:** architecture-strategist during /ce:review 2026-05-11.

## Findings

- CLAUDE.md, projects TLDR section: "fine-grained PAT with Contents:Read on every repo listed in `bin/projects-config.json`'s `shipping_repos` for any private project"
- Correct statement: PAT needs Contents:Read on each project's `repo` field (the CLAUDE.md source). `shipping_repos` are used for the public GitHub Events API — no token needed for public repos, and the existing token covers private repos' events as a side effect of Contents:Read.
- PAT expires ~2026-07-22

## Proposed Solutions

### Option A — Fix the documentation (recommended)

Replace the incorrect sentence with:

> fine-grained PAT with Contents:Read on every private repo listed in `bin/projects-config.json`'s **`repo`** field (the CLAUDE.md source). `shipping_repos` drive the public GitHub Events API and do not require the PAT.

**Effort:** Trivial
**Risk:** None — documentation only.

## Recommended Action

Option A. Fix before PAT rotation in July.

## Acceptance Criteria

- [ ] CLAUDE.md `TLDR_FETCH_TOKEN` bullet correctly references `repo` field, not `shipping_repos`
- [ ] Bullet notes that `shipping_repos` uses the public Events API

## Work Log

- 2026-05-11: Identified during /ce:review — architecture-strategist finding. PAT expires ~2026-07-22.
