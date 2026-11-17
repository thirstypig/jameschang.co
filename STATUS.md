# STATUS — jameschang.co

**Last updated:** 2026-11-17

## One-line description
Personal résumé site for James Chang (founder of Aleph Co., senior product manager), with a cron-fed /now page and a gated operator cockpit at /admin/.

## Scope / positioning
- Canonical professional profile; print stylesheet doubles as the résumé PDF.
- /now: Derek Sivers-style page with cron-synced data feeds and per-project status cards (13 projects in `bin/projects-config.json`).
- /admin/: "a curtain, not a lock" — public-safe portfolio cockpit plus a docs hub.

## Stack & hosting
- Plain static HTML/CSS/vanilla JS; no build step, no `package.json`.
- Python 3 sync scripts in `bin/`, run by GitHub Actions cron workflows that commit feed updates back to `main`.
- pytest suite (README: 610 tests) runs in CI (`ci-tests.yml`) on every push to `main`.
- GitHub Pages, custom apex domain via A/AAAA records + `CNAME`.
- Google Analytics 4 + Search Console.

## URLs
- https://jameschang.co
- https://jameschang.co/now/
- https://jameschang.co/projects/
- https://jameschang.co/admin/ (gated curtain)

## Shipped (last 60 days)
Most commits are automated feed chores; human work:
- **Books on /now (2026-11-17):** the Goodreads RSS feeds were retired (Goodreads stopped serving public shelf RSS ~2026-10-27; /now had shown an empty shelf since). Books now come from a hand-kept `books.json`, rendered client-side in the /07 "reading" card. 8 cron feeds → 6.
- **CI fix (2026-11-16):** an MLB test that assumed it was always baseball season failed every run after the Nov 15 off-season cutoff; its clock is now pinned.
- **/admin/ cockpit (2026-09-30):** /admin/ merged with the cockpit and redesigned — red/amber/green per project, goal tiers, 7-day trends; in-page editors for goals (`admin/goals.json` now source of truth), a money ledger (revenue + costs per project per month) and ideas.
- **New pages (2026-09-30):** /app/ (describes the jameschang.co Google app) and /terms/; privacy + terms linked from the homepage.
- **Homepage content:** Pasadena Works and résumé details added, two print bugs fixed (2026-09-24); SoCal Mini Club membership on homepage and /now (2026-10-13); new /now quote (2026-09-28).
- **Cockpit snapshot guard (2026-11-05):** test blocks Claude-encoded home paths from the published snapshot.
- **Ops:** slower Spotify/Calendar syncs to save Actions budget (2026-09-21); local preview moved to port 3090 (2026-09-12).

## In progress
- None recorded. CLAUDE.md lists 0 pending todos; all 152 files in `todos/` are complete or discarded.

## Open bugs / known issues
- **MLB/FBST blank on a failed fetch:** `update-public-feeds.py` writes its "unavailable" placeholder over the last good content when a fetch fails (the trap that blanked Goodreads). Plex preserves last content; these two should too.
- **/now project cards frozen since 2026-10-19:** `TLDR_FETCH_TOKEN` is invalid (401 on every repo, public included); the sync safely leaves the page unchanged. Needs a regenerated PAT.
- **Spotify feed disabled (2026-10-24):** failing under Spotify dev-mode lockdown.
- **Feed staleness monitor paused (2026-11-05, by choice):** feed outages are now silent until it is re-enabled.
- Trakt sync dormant since 2026-04-28 (dropped from /now on purpose).
- Known limit: project cards judge a push by its HEAD commit only.
- Accepted risk: private-repo commit subjects can appear on public /now cards.

## Next phases (in order)
- Unknown — not documented in repo. (`PLAN.md` is the April 2026 redesign plan, not a current roadmap.)

## Decisions changed recently
- 2026-09-30: /admin/ public-safe rule amended — cockpit snapshot (hours, spend, folder names, goals) published as-is; session titles and local paths still stripped.
- 2026-09-30: goals moved to `admin/goals.json` in this repo as the single source of truth; /admin/ no longer read-only.
- 2026-09-30: real revenue/cost figures shown on /admin/, with client codenames instead of real names.
- 2026-10-24: Spotify sync disabled (workflow renamed `.yml.disabled`).
- 2026-11-17: Goodreads feeds retired for a hand-kept `books.json` (Goodreads dropped public RSS).
- 2026-11-05: staleness-alert workflow disabled and open `feed-stale` issues closed.
- 2026-09-12: `PORTS.md` retired; `MASTER-PORTS.md` no longer published.
