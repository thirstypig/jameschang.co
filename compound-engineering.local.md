---
review_agents:
  - security-sentinel
  - performance-oracle
  - code-simplicity-reviewer
  - pattern-recognition-specialist
---

## Project Review Context

Plain static HTML/CSS/JS site on GitHub Pages. No build step. No framework. No package.json.

**Stack:**
- HTML/CSS/JS (frontend)
- Python 3 (sync scripts in `bin/`)
- GitHub Actions (cron workflows)
- pytest (224 tests across 9 files)

**Key patterns to enforce:**
- No KCBS/BBQ branding in Judge Tool content (use "Barbeque")
- CSS tokens from `notebook.css` (never hardcoded hex)
- Feed markers (`<!-- FEED-START/END -->`) must never be removed
- `snapshot-banner` divs are optional on deep-dive pages
- No `frame-ancestors` in CSP (GitHub Pages HTTP header limitation)
- All sync scripts must call `record_heartbeat()` on success and no-change paths
- `<time data-rel>` elements require `strip_volatile()` coverage to avoid spurious commits

**Protected paths:**
- `docs/solutions/` — institutional knowledge, never delete
- `todos/` — code review history, never delete
- `.whoop-token.enc` — never touch manually
- `.feeds-heartbeat.json` — written by cron only
