# Cron Scripts Operations & Debugging Guide

Quick-reference guide for troubleshooting, testing, and maintaining jameschang.co's cron-sync infrastructure.

## Quick Diagnosis Flowchart

```
Feed looks stale on https://jameschang.co/now/
         |
         v
Check GitHub issue (labeled feed-stale)
         |
         +-- No issue? → Still good (< 48h stale)
         |
         +-- Yes, issue open? → Look at issue body for guidance
                    |
                    v
              See "Common Issues" section below
```

## Common Issues & Fixes

### Issue: Feed hasn't updated in 48+ hours

**Check:** Open GitHub issue labeled `feed-stale`

**Diagnosis steps:**
```bash
# 1. Check the heartbeat — what does it say?
cat .feeds-heartbeat.json | grep {FEED_NAME}

# 2. Run the script locally to see the actual error
cd bin
python3 update-{feed}.py 2>&1 | tail -20

# 3. Check if token/API is accessible
# (See per-feed secrets below)
```

**Common causes:**
- GitHub Secret expired or misconfigured
- External API (WHOOP, Spotify, Plex, etc.) is down
- Network error (check GitHub Action logs)
- Missing marker in `now/index.html` (bootstrap trap)

**Fix roadmap by feed:**

#### WHOOP (daily sync at 6 AM PT)
```bash
# Token expired? Re-authorize
./bin/whoop-auth.sh              # Requires WHOOP_CLIENT_ID/SECRET

# Then re-encrypt it
./bin/whoop-encrypt.sh {new-token}

# Or check secrets exist
gh secret list | grep WHOOP
```
**Secrets needed:** `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, `WHOOP_TOKEN_KEY`

#### Spotify (every 30 min)
```bash
# Check if refresh token is expired
python3 -c "import os; print(os.environ.get('SPOTIFY_REFRESH_TOKEN'))"

# If missing or expired, re-auth at https://spotify.com/account/apps
# Then update GitHub Secret
gh secret set SPOTIFY_REFRESH_TOKEN --body "$(pbpaste)"
```
**Secrets needed:** `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`

#### Plex (every 6 hours)
```bash
# Check if the relay URL is reachable
curl -H "X-Plex-Token: {token}" "{PLEX_URL}/status/sessions/history/all"

# Token in GitHub Secret?
gh secret list | grep PLEX
```
**Secrets needed:** `PLEX_URL`, `PLEX_TOKEN`

#### Google Calendar (hourly at :00 UTC)
```bash
# Calendar secret is the iCal feed URL (secret by obscurity)
# Just verify it's set and accessible
curl "$(gh secret list | grep GCAL)"  # Don't run this — it prints the secret!

# Better: check Actions logs
```
**Secret needed:** `GCAL_ICAL_URL` (secret-by-obscurity, don't share)

#### MLB / Goodreads / FBST (every 6 hours)
```bash
# These are unauthenticated public APIs — check if they're down
curl https://statsapi.mlb.com/api/v1/teams/119
curl https://www.goodreads.com/review/list_rss/33966778?shelf=read
curl https://app.thefantasticleagues.com/api/public/leagues/ogba-2026/standings
```
**No secrets needed** — if these fail, the APIs are down

#### Projects (daily at 6 AM PT)
```bash
# Check if GitHub token has access to private repos
gh secret list | grep TLDR_FETCH_TOKEN

# Verify it can read events from private repos
gh api repos/thirstypig/alephco.io-app/events --limit 1
```
**Secret needed:** `TLDR_FETCH_TOKEN` (fine-grained PAT, `contents:read` on all private shipping repos)

---

### Issue: Marker missing from now/index.html

**Symptom:** A feed hasn't synced in weeks, but there's no GitHub issue

**Cause:** Bootstrap trap — if markers are missing, `replace_marker()` silently returns `replaced=False`

**Fix:**
```bash
# Verify all 14 markers exist
grep -c "WHOOP-START" now/index.html    # Should be 1
grep -c "SPOTIFY-START" now/index.html  # Should be 1
# ... repeat for all feeds

# If any are 0, re-add the marker pair:
# <!-- {FEED}-START -->
#   <p class="feed-empty">Default content</p>
# <!-- {FEED}-END -->

# Markers list (all 14):
# WHOOP, SPOTIFY, PLEX, MLB, GOODREADS-READING, GOODREADS, FBST, GCAL, GCAL-EYEBROW
# ACTIVE-EYEBROW, ACTIVE-PROJECTS, BACKBURNER-EYEBROW, BACKBURNER-PROJECTS
# PAGE-UPDATED
```

**Guard:** E2E tests will catch missing markers and block the PR

---

### Issue: Script produces identical output but still commits

**Symptom:** Cron job commits every run even though data hasn't changed

**Cause:** Volatile content (timestamps) not being stripped for comparison

**Fix:**
```bash
# Check if strip_volatile() handles your new field
# in bin/_shared.py — look for _VOLATILE_REL_TIME_RE

# If you added a new time field, extend the regex:
# OLD: _VOLATILE_REL_TIME_RE = r'<time data-rel>[^<]+</time>'
# NEW: _VOLATILE_REL_TIME_RE = r'<time data-rel>[^<]+</time>|<span class="when">[^<]+</span>'

# Test it
python3 -c "from _shared import strip_volatile; print(strip_volatile(open('now/index.html').read()))" | tail -20
```

---

## Testing & Verification

### Test locally before pushing

```bash
# Set up environment
export WHOOP_CLIENT_ID="..."
export WHOOP_CLIENT_SECRET="..."
# ... set all needed secrets

# Run the script with DRY_RUN if available
python3 bin/update-{feed}.py

# Check output
git diff now/index.html | head -50

# Run tests
python3 -m pytest tests/test_{feed}.py -v

# Verify idempotency (run twice, should match)
python3 bin/update-{feed}.py
BEFORE=$(cat now/index.html | md5)
python3 bin/update-{feed}.py
AFTER=$(cat now/index.html | md5)
[ "$BEFORE" = "$AFTER" ] && echo "✅ Idempotent" || echo "❌ Not idempotent"
```

### Check heartbeat staleness

```bash
# Manual check (normally automated every 6h)
python3 bin/check-feed-health.py

# Dry run (don't open/close issues)
DRY_RUN=1 python3 bin/check-feed-health.py
```

### Verify all tests pass

```bash
# Full suite
python3 -m pytest tests/ -v

# Just feed tests
python3 -m pytest tests/test_projects.py tests/test_whoop.py tests/test_spotify.py tests/test_gcal.py tests/test_feed_builders.py -v

# Just E2E
python3 -m pytest tests/test_site_e2e.py::TestFeedMarkers -v
python3 -m pytest tests/test_site_e2e.py::TestProjectCardRoadmaps -v
```

---

## Manual Sync (Override GitHub Actions)

**Use case:** Need to update a feed immediately (API recovered, token renewed, etc.)

```bash
# Set up environment
cd /Users/jameschang/Projects/jameschang.co
export GITHUB_ACTOR="manual-sync"

# Set secrets (choose one method)
# Method 1: Read from GitHub Secrets
export WHOOP_CLIENT_ID=$(gh secret list --json name,value | jq -r '.[] | select(.name=="WHOOP_CLIENT_ID") | .value')
# ... etc for all secrets

# OR Method 2: Prompt for secrets
read -sp "WHOOP_CLIENT_ID: " WHOOP_CLIENT_ID
export WHOOP_CLIENT_ID

# Run the script
cd bin && python3 update-whoop.py

# Verify output
git diff ../now/index.html

# Commit and push (if successful)
git add ../now/index.html ../FEEDS-heartbeat.json
git commit -m "chore: manual sync of whoop feed (token refreshed)"
git push
```

---

## Monitoring & Alerts

### Staleness monitor

- Runs every 6 hours via `.github/workflows/feeds-staleness-check.yml`
- Opens GitHub issue if feed > 48h stale
- Adds comment on subsequent failures
- Auto-closes when feed recovers

**Check status:**
```bash
# Last heartbeat check
gh run list -w feeds-staleness-check.yml -L 5

# Open issues
gh issue list -l feed-stale
```

### View GitHub Actions logs

```bash
# Last run of a specific workflow
gh run view -w whoop-sync.yml --log

# Specific workflow + run number
gh run view {RUN_ID} -w whoop-sync.yml --log | tail -50
```

---

## Adding a New Feed (Operational Checklist)

1. **Create the Python script** (`bin/update-{feed}.py`)
   - Implement fetch, parse, build_html
   - Add heartbeat recording
   - Test locally first

2. **Add markers to `/now/index.html`**
   ```html
   <!-- {FEED}-START -->
     <p class="feed-empty">Fallback content</p>
   <!-- {FEED}-END -->
   ```

3. **Add to EXPECTED_MARKERS** in `tests/test_site_e2e.py`
   ```python
   EXPECTED_MARKERS = [..., "MYFEED", ...]
   ```

4. **Create GitHub Action** (`.github/workflows/{feed}-sync.yml`)
   - Set schedule (cron)
   - Add secrets if needed
   - Call `python3 bin/update-{feed}.py`
   - Record heartbeat

5. **Set GitHub Secrets** (if API requires auth)
   ```bash
   gh secret set API_TOKEN --body "$(pbpaste)"
   ```

6. **Write tests**
   - Unit tests: fetch, build, error cases
   - Idempotency test: same input → same output

7. **Manual verification**
   ```bash
   python3 bin/update-{feed}.py
   git diff now/index.html  # Looks good?
   python3 -m pytest tests/test_{feed}.py -v
   ```

8. **Deploy**
   - Commit to main
   - CI runs tests + E2E checks
   - Workflow triggers on next cron run

---

## Pre-PR Checklist

Before pushing to main:

- [ ] Tests pass: `python3 -m pytest tests/ -v`
- [ ] Script runs locally: `python3 bin/update-{feed}.py`
- [ ] Idempotent: run twice, output unchanged
- [ ] Markers present: `grep "{FEED}-START" now/index.html`
- [ ] No hardcoded secrets: `git diff --cached | grep -i "token\|secret\|password"`
- [ ] Volatiles handled: new timestamps stripped by `strip_volatile()`
- [ ] Heartbeat updated: `.feeds-heartbeat.json` has latest entry
- [ ] GitHub Actions exists: `.github/workflows/{feed}-sync.yml` defined
- [ ] GitHub Secrets set: `gh secret list | grep {FEED}`

---

## Key Files Reference

```
bin/
  _shared.py                 ← replace_marker(), content_changed(), strip_volatile()
  update-projects.py         ← Project cards (config-driven)
  update-whoop.py           ← WHOOP fitness data
  update-spotify.py         ← Spotify tracks + podcasts
  update-plex.py            ← Plex watch history
  update-public-feeds.py    ← MLB, Goodreads, FBST
  update-gcal.py            ← Google Calendar events
  check-feed-health.py      ← Staleness monitor
  projects-config.json      ← Project card configuration
  .env.example              ← Local secrets template

.github/workflows/
  whoop-sync.yml
  spotify-sync.yml
  plex-sync.yml
  public-feeds-sync.yml
  gcal-sync.yml
  projects-sync.yml
  project-docs-sync.yml
  feeds-staleness-check.yml

now/
  index.html                ← All 14 marker pairs live here
  now.js                    ← Client-side logic (relative times, modals)
  project-cards.js          ← Opt-in JS data layer

.feeds-heartbeat.json       ← Last success timestamp per feed

docs/
  solutions/
    integration-issues/
      cron-script-config-driven-content-rendering.md
      relative-time-html-defeats-content-changed-cache.md
      marker-boundary-content-staleness.md
  guides/
    cron-scripts-architecture.md
    cron-scripts-operations.md (this file)
    adding-new-feed.md
```

---

## Support Resources

- **GitHub Actions docs:** https://docs.github.com/actions
- **GitHub Secrets:** `gh secret list`, `gh secret set`
- **Test runner:** `python3 -m pytest tests/ -v`
- **Architecture guide:** `docs/guides/cron-scripts-architecture.md`
- **Pattern deep-dives:** `docs/solutions/integration-issues/`

---

## SOS: Nothing Works

Last-resort steps:

1. Check `.github/workflows/` to see if workflow is enabled
2. Check GitHub Actions run history for logs
3. Check `.feeds-heartbeat.json` for last error message
4. Check if GitHub Secrets are set: `gh secret list`
5. Run script locally: `python3 bin/update-{feed}.py 2>&1 | tail -50`
6. Check if markers exist: `grep "{FEED}-START" now/index.html`
7. Check test suite: `python3 -m pytest tests/test_site_e2e.py::TestFeedMarkers -v`

If still stuck: open a GitHub issue with:
- Workflow name + last run link
- Heartbeat error message (from `.feeds-heartbeat.json`)
- Local test results
- Any error logs from GitHub Actions
