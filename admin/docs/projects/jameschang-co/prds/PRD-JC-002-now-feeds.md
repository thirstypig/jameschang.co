---
id: PRD-JC-002
type: prd
project: jameschang-co
status: active
stage: shipped
owner: james
tags: [integration, infra]
links: [PRD-JC-001]
updated: 2026-07-24
---

# jameschang.co — the self-updating /now page

## 1. Problem statement
[inferred] A static portfolio reads as archival. To prove "an operator who ships," the
site needed to visibly stay current on its own — without manual updates.

## 2. Strategic rationale
[intended] The /now page + live feeds ARE the demonstration: the site updates itself, so
it argues the thesis by existing. Post-MVP, this is the flagship differentiator.

## 3. User story
[inferred] As a visitor, I want to see what James is doing right now (health, music,
reading, projects shipping) so the portfolio feels alive.

## 4. Hypothesis / assumptions
- [intended] A living /now page beats prose at signaling "ships continuously."
- [unknown] Whether visitors value the feeds vs. the case studies. **← confirm.**

## 5. Impact & KPIs
- (a) SHOULD measure: [unknown] /now engagement, return visits.
- (b) TODAY: [unknown] — not broken out. **← confirm.**

## 6. Technical notes
[inferred] 8 cron-synced feeds (WHOOP, Spotify, Plex, MLB, FBST, Goodreads×2, GCal) +
per-project activity cards; Python `bin/*.py` sync scripts commit to the repo; a
staleness monitor opens a GitHub issue when a feed goes quiet.

## 7. AI implementation notes
n/a — data plumbing, not AI.

## 8. Testing plan
[inferred] Feed builders + idempotency + heartbeat-correctness are unit-tested;
markers/CSP are E2E-tested.

## 9. Deferred / what we'd do differently
[inferred] Spotify feed is deferred (Feb-2026 Dev Mode lockdown). Lesson learned:
heartbeat must reflect real upstream success, not just "script didn't crash."
