# Cron Scripts Architecture & Best Practices

This guide documents the architecture of cron-sync scripts that update jameschang.co and best practices for extending, modifying, or adding new feeds.

## Architecture Overview

**Goal:** Keep jameschang.co fresh by syncing external data (APIs, RSS feeds, GitHub events, etc.) into the static `/now` page.

**Pattern:** All sync scripts follow the same flow:
1. Fetch upstream data (API, RSS, GitHub, etc.)
2. Parse and format to HTML
3. Splice into existing HTML via `replace_marker()`
4. Check `content_changed()` (with `strip_volatile()`) before commit
5. Update `.feeds-heartbeat.json`

## Two Script Architectures

### API-Driven Scripts (Recommended)

Fetch data directly from APIs, parse, and render HTML. **No configuration file.**

**Examples:** `update-whoop.py`, `update-spotify.py`, `update-plex.py`, `update-gcal.py`, `update-public-feeds.py`

**Advantages:**
- Source of truth is live API (always current)
- No "missing field in render" trap
- Simpler: API response → HTML output
- All available fields automatically included

**Pattern:**
```python
def build_html(api_response):
    """Render API data to HTML."""
    # Parse API response
    # Format each field
    # Return HTML string

def main():
    items = fetch_api()                    # Fetch upstream data
    html = build_html(items)              # Render to HTML
    old = read_now_html()
    new, replaced = replace_marker(old, "FEED", html)
    if not content_changed(old, new):
        return  # No changes
    write_now_html(new)
    record_heartbeat("feed")
```

### Config-Driven Scripts (Use with Care)

Store configuration in a JSON file; render function outputs config values. **Used only by `update-projects.py`.**

**Risk:** Config fields might not be rendered if render function is incomplete.

**Mitigations:**
1. ✅ Config is the sole source of truth (not HTML)
2. ✅ Render function reads ALL config fields
3. ✅ Tests verify all fields render (config-drives-output tests)
4. ✅ Idempotency tests: same config → same output

**If you add a field to config, you MUST:**
1. Add it to the config schema (e.g., `projects-config.json`)
2. Update the render function to output it
3. Add unit test: change config field, run script, verify output
4. Add idempotency test: same input → same output

**Example:** `bin/projects-config.json` + `render_card()` in `update-projects.py`

See `docs/solutions/integration-issues/cron-script-config-driven-content-rendering.md` for the full trap + prevention guide.

## Marker-Based HTML Templating

All scripts use **marker pairs** to splice content into static HTML:

```html
<!-- {FEED}-START -->
  [cron script overwrites this]
<!-- {FEED}-END -->
```

The `replace_marker(old_html, "FEED", new_block)` function:
- Finds `<!-- FEED-START -->` and `<!-- FEED-END -->` markers
- Replaces everything between them
- Returns `(new_html, replaced)` where `replaced=False` if markers missing

### Bootstrap Rule

**If markers are missing, `replace_marker()` silently skips that feed forever.**

Example: A developer accidentally deletes `<!-- WHOOP-START -->` from `now/index.html`. The next cron run sees `replaced=False`, logs nothing, and exits. WHOOP data stops updating silently.

**Guards:**
- `tests/test_site_e2e.py::TestFeedMarkers` verifies all `EXPECTED_MARKERS` are present
- Any marker deletion fails CI, blocks the PR

**Current markers (14 total):**
```
ACTIVE-EYEBROW, ACTIVE-PROJECTS          ← update-projects.py
BACKBURNER-EYEBROW, BACKBURNER-PROJECTS  ← update-projects.py
WHOOP, SPOTIFY, PLEX                     ← individual feed scripts
MLB, GOODREADS-READING, GOODREADS, FBST  ← update-public-feeds.py (4 builders)
GCAL, GCAL-EYEBROW                       ← update-gcal.py
PAGE-UPDATED                             ← updated by every script
```

### Marker Boundaries & Content Persistence

**Content INSIDE markers** (`<!-- FEED-START -->...<!-- FEED-END -->`) is **regenerated** on every sync — hand-edits disappear.

**Content OUTSIDE markers** is **hand-curated** — cron scripts never touch it.

Trade-off: Put config-driven content inside markers (always synced), or outside (but it freezes on last edit). Choose based on freshness vs. stability needs.

**Example:**
```html
<!-- PROJECT-CARDS-START -->
<!-- TLDR-aleph-START -->
[render_card() regenerates this; hand-edits deleted next run]
<!-- TLDR-aleph-END -->
<!-- PROJECT-CARDS-END -->

<div class="project-hero">
  [Hand-curated section outside markers; never touched by cron]
</div>
```

## Content Volatility & Idempotency

### The Problem

Relative timestamps like `<time data-rel>2h ago</time>` reformat every minute, causing `content_changed()` to see fake "diffs" even when nothing actually changed. This triggers unnecessary commits.

### The Solution

`_shared.py` provides `strip_volatile()`:
- Removes `Auto-updated {timestamp}` eyebrow lines
- Removes content inside `<time data-rel>...</time>` elements
- Compares the stripped versions to detect real changes

**When adding new volatile content:**
1. Use `<time data-rel="{ISO-timestamp}">` for relative times
2. Add your pattern to `_VOLATILE_REL_TIME_RE` in `_shared.py`
3. Verify: run script twice with no upstream changes, confirm no commit

See `docs/solutions/integration-issues/relative-time-html-defeats-content-changed-cache.md` for the full analysis.

## Idempotency Testing

**Every cron script should pass idempotency tests:** same input → same output (modulo volatiles).

### Unit-Level Test

```python
def test_build_html_is_deterministic(self):
    """Same input data → identical HTML."""
    data = {"field": "value", "time": "2026-06-25T12:00:00Z"}
    html1 = build_html(data)
    html2 = build_html(data)
    assert html1 == html2
```

### Script-Level Test (E2E)

```python
def test_cron_sync_is_idempotent(self):
    """Run twice with no API changes; output unchanged."""
    # First run
    main()
    old_file = read_file("now/index.html")
    
    # Second run (no upstream changes)
    main()
    new_file = read_file("now/index.html")
    
    # Strip volatiles and compare
    assert strip_volatile(old_file) == strip_volatile(new_file)
```

**Current coverage:**
- ✅ test_projects.py (6 tests)
- ✅ test_whoop.py (3 tests)
- ✅ test_spotify.py (3 tests)
- ✅ test_gcal.py (2 tests)
- ✅ test_feed_builders.py (6 tests: Plex, MLB, Goodreads, FBST)

## Adding a New Data Feed

### Checklist (8 steps)

1. **Create the fetcher function**
   ```python
   def fetch_data():
       # Fetch from API/RSS/etc
       # Return structured data or None on error
   ```

2. **Create the builder function**
   ```python
   def build_html(data):
       # Format data to HTML
       # Include Auto-updated line
       # Return HTML string
   ```

3. **Add markers to `/now/index.html`**
   ```html
   <!-- MYFEED-START -->
     <p class="feed-empty">No data yet.</p>
   <!-- MYFEED-END -->
   ```

4. **Call `replace_marker()` in main()**
   ```python
   html_block = build_html(fetch_data())
   content, replaced = replace_marker(old_html, "MYFEED", html_block)
   if not replaced:
       print("ERROR: MYFEED markers not found")
       sys.exit(1)
   ```

5. **Add heartbeat recording**
   ```python
   record_heartbeat("myfeed", error=None if data else "fetch failed")
   ```

6. **Add to EXPECTED_MARKERS in test_site_e2e.py**
   ```python
   EXPECTED_MARKERS = [..., "MYFEED", ...]
   ```

7. **Write unit tests** (fetch, build, error cases)
   ```python
   class TestMyFeedBuild:
       def test_renders_data(self): ...
       def test_empty_returns_fallback(self): ...
   ```

8. **Write idempotency tests**
   ```python
   class TestMyFeedIdempotency:
       def test_build_html_is_deterministic(self): ...
   ```

9. **Add GitHub Action** (if new external API/token)
   - Secret: API key / token
   - Cron schedule (6h, 30min, daily, etc.)
   - Heartbeat monitoring

See `docs/guides/adding-new-feed.md` for the full 8-step process.

## Common Patterns & Gotchas

### Pattern 1: Fallback Content

When fetch fails, use a fallback instead of failing the whole sync:

```python
def main():
    items = fetch_data()                    # Returns None on error
    if items is None:
        record_heartbeat("feed", error="fetch failed")
        print("Feed fetch failed; leaving existing content untouched.")
        return  # Preserve last known state
    
    html = build_html(items)
    # ... proceed with sync
```

**Don't:** Delete the marker block on error (content disappears forever).

### Pattern 2: Multiple Builders in One Script

`update-public-feeds.py` has 4 builders (MLB, Goodreads reading, Goodreads, FBST). Each is independent:

```python
def main():
    feeds = [
        ("MLB", mlb_block, '<p class="feed-empty">No data.</p>'),
        ("GOODREADS", goodreads_block, '<p class="feed-empty">No books.</p>'),
    ]
    for marker, builder, fallback in feeds:
        if f"<!-- {marker}-START -->" not in content:
            continue  # Skip if marker missing (bootstrap guard)
        result = builder()
        html = result if result else fallback
        content, _ = replace_marker(content, marker, html)
```

**Advantage:** One cron job updates multiple feeds; one failure doesn't block others.

### Pattern 3: Token Rotation

WHOOP uses OAuth2 refresh token rotation:
- Token stored encrypted in repo (`.whoop-token.enc`)
- Decrypted at runtime with GitHub Secret passphrase (`WHOOP_TOKEN_KEY`)
- Re-encrypted after refresh, committed back
- Avoids needing a PAT with `secrets: write` scope

See `docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md`.

### Gotcha 1: Silent Marker Bootstrap Failure

```python
# ❌ BAD: Script returns silently if markers missing
def main():
    new_html, replaced = replace_marker(old_html, "FEED", html_block)
    # Script continues even if replaced=False
```

**Fix:** Check and exit:
```python
# ✅ GOOD: Explicit error on missing markers
if not replaced:
    print("ERROR: FEED markers not found", file=sys.stderr)
    sys.exit(1)
```

### Gotcha 2: Forgetting to Strip Volatiles

```python
# ❌ BAD: Timestamp causes false "changes" every run
if content_changed(old, new):  # new has "Auto-updated 12:34 PM"
    write_now_html(new)        # Commits even though data unchanged
```

**Fix:** Let `_shared.strip_volatile()` handle it:
```python
# ✅ GOOD: Volatiles stripped before comparison
if not content_changed(old, new):  # strip_volatile() runs internally
    return  # True no-op
```

### Gotcha 3: Hardcoded Constants vs Config

```python
# ❌ API-driven script with hardcoded constant
GOODREADS_USER_ID = "33966778"  # Hard to change without editing code

# ✅ If many users, consider config file (but then add tests!)
# Otherwise, leave as hardcoded constant — it's fine for single-user site
```

## Monitoring & Alerting

**Feed staleness monitor** (`bin/check-feed-health.py`):
- Runs every 6 hours
- Checks `.feeds-heartbeat.json`
- Opens GitHub issue if any feed > 48 hours stale
- Auto-closes when feed recovers

**Heartbeat structure:**
```json
{
  "whoop": {
    "last_success_utc": "2026-06-25T13:00:00Z",
    "last_error": null
  },
  "spotify": {
    "last_success_utc": "2026-06-25T12:30:00Z",
    "last_error": "Token expired"
  }
}
```

## Summary Checklist

**Before modifying a cron script:**
- [ ] Understand if it's API-driven or config-driven
- [ ] Check if you're adding fields to config (requires render function update + test)
- [ ] Verify all markers exist in `now/index.html`
- [ ] Run idempotency test: script twice, no commit if unchanged
- [ ] Verify `content_changed()` uses `strip_volatile()` for time fields

**Before adding a new feed:**
- [ ] Follow the 8-step checklist above
- [ ] Write unit tests (fetch, build, errors)
- [ ] Write idempotency tests
- [ ] Add marker pair to HTML
- [ ] Add to EXPECTED_MARKERS in test_site_e2e.py
- [ ] Create GitHub Action with cron + secrets
- [ ] Test locally first

**When debugging a broken sync:**
1. Check `.feeds-heartbeat.json` for the most recent `last_error`
2. Run the script locally with `DRY_RUN=1` or similar
3. Verify markers exist (`grep "FEED-START" now/index.html`)
4. Check GitHub Action logs for auth/network errors
5. Verify GitHub Secrets are set (especially auth tokens)

---

See also:
- `docs/solutions/integration-issues/cron-script-config-driven-content-rendering.md` — Config trap deep-dive
- `docs/solutions/integration-issues/relative-time-html-defeats-content-changed-cache.md` — Volatility gotcha
- `docs/guides/adding-new-feed.md` — New feed checklist
- `.github/workflows/` — All cron job definitions
