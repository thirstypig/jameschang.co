---
status: done
priority: p1
issue_id: 001
tags: [code-review, security, privacy]
dependencies: []
---

# Remove `CONTENT_SOURCES.md` and `PLAN.md` from the public GitHub repo

## Problem Statement

The public GitHub repo (`thirstypig/jameschang.co`) is linked from the homepage footer at `index.html:523` ("source on GitHub"). Anyone following that link can read two working-notes files that were never meant to be public:

- `CONTENT_SOURCES.md` — inventory of 15+ private repos, full integration list for Bahtzang Trader (Schwab, Alpaca, Alpha Vantage, Supabase, Slack notifier, guardrails/kill switch), internal deliberations about framing
- `PLAN.md` — ~32 KB of design rationale, open questions, resolved answers, DNS config, and the explicit note on Bahtzang: *"keep it a little vague; indicate it's an experiment, not real-money trading"* — which directly undoes the public framing

This leaks a threat-surface map for what James is building, and publishes internal product deliberations that contradict the public-facing messaging.

## Findings

From security-sentinel agent (P1-1, P1-2):
- `CONTENT_SOURCES.md:48–65` lists every private repo by name and what it does
- `CONTENT_SOURCES.md:50` exposes Bahtzang integration details vs. public framing on `index.html`
- `PLAN.md:22, 618` records the rebrand deliberation
- Both tracked in git (`git ls-files` confirms), repo is public, footer link makes it trivially discoverable

## Proposed Solutions

### Option A: `git rm --cached` + gitignore, keep local copies
- **Effort:** Small (~5 min)
- **Pros:** One command, local working docs survive for reference, clean break
- **Cons:** History still contains full contents — anyone cloning can `git log -p -- PLAN.md` to recover. Need force-push history rewrite to truly scrub.
- **Risk:** Low for forward-looking cleanup; historical leak remains unless rewrite.

### Option B: Rewrite history to erase the files from all past commits
- **Effort:** Medium (~15 min, force-push needed)
- **Pros:** Content genuinely unreachable via git history
- **Cons:** Force-push rewrites commit SHAs, which is fine for a solo repo but annoying if anyone has forked
- **Risk:** If forks exist, they keep the old content.

### Option C (Recommended): Move files to private repo, add to gitignore
- **Effort:** Small (~10 min)
- **Pros:** Keep working notes accessible to yourself, remove from public exposure, same mechanics as Option A + separation
- **Cons:** Two repos to maintain

## Technical Details

Files affected:
- `/Users/jameschang/Projects/jameschang.co/CONTENT_SOURCES.md`
- `/Users/jameschang/Projects/jameschang.co/PLAN.md`
- `/Users/jameschang/Projects/jameschang.co/.gitignore` (add both filenames)

Commands (Option A):
```
git rm --cached CONTENT_SOURCES.md PLAN.md
echo -e "CONTENT_SOURCES.md\nPLAN.md" >> .gitignore
git add .gitignore
git commit -m "Remove internal working notes from public repo"
git push
```

Optional history rewrite (Option B, after A):
```
git filter-repo --path CONTENT_SOURCES.md --path PLAN.md --invert-paths
git push --force origin main
```

## Acceptance Criteria

- [ ] `CONTENT_SOURCES.md` and `PLAN.md` no longer appear in `git ls-files`
- [ ] `.gitignore` includes both filenames
- [ ] Live GitHub repo at `https://github.com/thirstypig/jameschang.co` does not show these files in the file browser
- [ ] (Optional) `git log -- PLAN.md` returns empty if history rewrite was done

## Work Log

_(blank — update when work starts)_

## Resources

- Security audit output (4 review agents run 2026-04-14)
- `index.html:523` — footer "source on GitHub" link
