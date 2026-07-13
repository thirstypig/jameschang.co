---
name: cron-script-config-driven-content-rendering
title: "Cron Script Config-Driven Content: Hand-Edits Don't Survive Sync Cycles"
description: Roadmap items disappeared from /now project cards because render_card() didn't read config; demonstrates config-as-source-of-truth pattern
category: integration-issues
problem_type: integration-issues
components:
  - bin/update-projects.py
  - bin/projects-config.json
  - now/index.html
symptoms:
  - roadmap items visible in local preview but absent from production /now page
  - manually-added content inside marker blocks gets deleted on next cron run
  - configured roadmap_items in projects-config.json ignored by render pipeline
root_cause: render_card() function in update-projects.py did not read or output roadmap_items field; script regenerates entire marker block from config, overwriting hand-edits
tags:
  - cron-sync
  - marker-based-templating
  - config-driven-output
  - content-persistence
  - /now-page-architecture
resolved: "2026-06-25"
---

> **Audit note (2026-07-13):** this doc records the 2026-06-25 fix, when `bin/projects-config.json` held **9** projects. It now holds **11** (added `vouch` 2026-07-01, `spar` 2026-07-10), so the "all 9 projects" counts below read as historical — the config-as-source-of-truth pattern applies to all 11 identically.

## Problem Summary

Project cards on the `/now` page were losing their "upcoming roadmap features" sections during cron syncs. When you manually added roadmap items to `/now/index.html`, they would disappear after `bin/update-projects.py` ran its daily sync.

The root issue: the script regenerates **entire** card HTML from `projects-config.json` and GitHub events — it doesn't merge with or preserve existing HTML between markers. Hand-edited content inside marker blocks is silently overwritten.

## Root Cause

The `render_card()` function in `bin/update-projects.py` was incomplete. It rendered:
- Project name, domain, badges
- Activity (most recent GitHub event)
- Description
- "Next up" line

But it **had no code path** to output roadmap items. When the script rewrote the card HTML between `<!-- TLDR-{slug}-START -->` / `<!-- TLDR-{slug}-END -->` markers, any manually-added roadmap sections were deleted because they weren't part of the programmatic output.

**The pattern:** Cron scripts that use `replace_marker()` **regenerate content completely** from source data (config, API responses). They don't merge with existing HTML. Content inside markers is a temporary artifact, not a persistent store.

## Investigation Steps

1. **Symptom observation**: Roadmap items rendering locally (`python3 -m http.server 8787`) but missing on production (jameschang.co)
2. **Browser verification**: Checked `https://jameschang.co/now/` — DOM had 0 roadmap sections; curl showed they were also missing from the HTML
3. **Traced the sync**: Reviewed git history of `now/index.html` — roadmap divs were added in commit `725e8e6`, then removed by commit `2f89779` (the "sync project TLDRs" cron run)
4. **Located the generator**: Found `render_card()` in `bin/update-projects.py` builds the entire card output; audited the function and found no roadmap handling
5. **Checked the config**: `bin/projects-config.json` had no `roadmap_items` field — the config schema wasn't prepared to carry this data
6. **Designed the fix**: 
   - Add `roadmap_items` array to each project in config (source of truth)
   - Extend `render_card()` to read and output roadmap items (generator)
   - Regenerate `now/index.html` to apply the fix (apply to production)

## Working Solution

### Step 1: Add roadmap_items to projects-config.json

Each project object now includes a `roadmap_items` array with 3-5 upcoming features:

```json
{
  "slug": "aleph",
  "name": "Aleph",
  "url": "https://alephco.io",
  "desc": "The compliance platform for US importers...",
  "next_up": "Onboard the first beta users...",
  "roadmap_items": [
    "Beta user onboarding",
    "Module override architecture",
    "Vertical expansion roadmap"
  ],
  "shipping_repos": ["thirstypig/alephco.io-app", "thirstypig/alephco.io-www"]
}
```

Applied to all 9 projects: aleph, fantastic-leagues, bahtzang-trader, judge-tool, tabledrop, tastemakers, thirsty-pig, ktv-singer, jameschang-co.

### Step 2: Modify render_card() in bin/update-projects.py

Extended the function to extract and render roadmap items:

```python
def render_card(project, shipping_events, now_str):
    # ... existing code for name, badge, activity, desc, next_up ...
    
    roadmap_items = project.get("roadmap_items") or []  # Extract the array from config
    slug = project["slug"]
    
    # ... existing lines for activity and description rendering ...
    
    if roadmap_items:  # Conditionally render the roadmap section
        lines += [
            '          <div class="nb-proj-roadmap">',
            '            <p class="nb-proj-roadmap-label">upcoming roadmap features</p>',
            '            <ul>',
        ]
        for item in roadmap_items:
            safe_item = escape_html(item)  # XSS safety: escape before outputting
            lines.append(f'              <li>{safe_item}</li>')
        lines += [
            '            </ul>',
            '          </div>',
        ]
    
    lines += [
        f'          <p class="feed-updated">Auto-updated {now_str} via GitHub events.</p>',
        f'          <!-- TLDR-{slug}-END -->',
        '        </article>',
    ]
    return "\n".join(lines)
```

The section is **optional** — if a project has no roadmap_items or an empty array, the div is not rendered.

### Step 3: CSS styling (already in notebook.css)

The design system already defines the styling classes. Rendering is consistent with existing notebook design:

```css
.nb-proj-roadmap { margin-top: 8px; }
.nb-proj-roadmap-label { 
  font-family: var(--mono);
  font-weight: 600;
  text-transform: uppercase;
  font-size: 10px;
}
.nb-proj-roadmap li:before { content: '·'; color: var(--accent); }
```

### Step 4: Verification

**Local test:**
```bash
python3 bin/update-projects.py
curl http://localhost:8787/now/ | grep -c "upcoming roadmap"  # Should find 9+
```

**Live verification:**
```bash
curl https://jameschang.co/now/ | grep "Standings accuracy refinement"  # Should be present
```

**Idempotency test:** Run the sync twice, compare output (should be identical):
```bash
python3 bin/update-projects.py
git diff now/index.html  # Should be empty
python3 bin/update-projects.py
git diff now/index.html  # Still empty
```

## Prevention Strategies

### For Adding New Content to Cron-Managed Sections

**Rule: Config is the source of truth, not HTML.**

When you want to add new fields to project cards (or any cron-managed section):

1. **Add to config** (`projects-config.json`): `"roadmap_items": [...]`
2. **Update the render function** (`render_card()`): read the field and emit HTML
3. **Never hand-edit HTML inside marker blocks** — it will disappear on the next run
4. **Test the round-trip**: change config → run script → verify output

**Anti-pattern:** Manually adding `<div class="nb-proj-roadmap">` to `now/index.html` and expecting it to survive. The script will delete it on the next sync because it's not in the regenerated output.

### For Cron Script Development

**Design principle: Generative, not integrative.**

Cron scripts that use `replace_marker()` **generate** content from input (config, API responses), not **integrate** with existing HTML. The contract is:

- **Input:** Config file + external data (GitHub events, RSS, APIs)
- **Process:** Parse input, format to HTML
- **Output:** Replace entire marker block with generated HTML
- **Side effect:** Any hand-edits to the marker block are lost

If you need to preserve hand-edits:
- Move them **outside** the marker block (but then they freeze on last-edit)
- Or source them from **config**, not HTML (safer, what we did here)

### Testing Strategy

For any cron script that manages HTML sections:

| Test | Purpose | How |
|------|---------|-----|
| **Config-drives-output** | Verify config field → rendered output | Change `roadmap_items`, run script, verify HTML |
| **Idempotency** | Verify no-change → no-op | Run twice, compare (strip volatiles), should match |
| **Hand-edit danger** | Document what gets deleted | Manually edit inside markers, run script, show it's gone |
| **Round-trip** | Verify full cycle | Add to config, sync, run again, verify still there |

**Example:** Test for the roadmap items fix:
```python
def test_roadmap_items_survive_sync():
    # Arrange: projects-config has roadmap_items
    # Act: render_card() with that project
    # Assert: HTML contains <div class="nb-proj-roadmap"> with all items
    
def test_roadmap_items_missing_empty_array():
    # Arrange: project with empty roadmap_items: []
    # Act: render_card()
    # Assert: HTML has no <div class="nb-proj-roadmap">
    
def test_empty_roadmap_items_doesnt_crash():
    # Arrange: project with no roadmap_items field at all
    # Act: render_card()
    # Assert: HTML renders without error, no roadmap div
```

### Monitoring

In code review and testing:

- **Flag hand-edits to marker blocks** as "will disappear on next run" (testing checklist)
- **Verify cron test includes idempotency** (run twice, compare, should be identical modulo volatiles)
- **Audit all config additions** — if you add a field to config, check that the render function outputs it (not just stored)

**Early warning:** If you see repeated timestamp-only commits from a sync script, the bug is likely something in the rendered HTML changing on a wall clock (relative times, status badges, etc.). The fix is usually extending `strip_volatile()` in `_shared.py` to ignore that time-drift.

## Related Issues & Patterns

### Similar Problems (Documented)

- **[[marker-boundary-content-staleness]]** — Content *outside* marker blocks freezes on last hand-edit; the retired-feed-slug cleanup loop doesn't visit them. Rule: all time-sensitive content must live **inside** markers or be config-driven.
- **[[relative-time-html-defeats-content-changed-cache]]** — Server-rendered `<time data-rel>Nh ago</time>` reformats every minute, causing `content_changed()` to see fake diffs. Solution: `strip_volatile()` in `_shared.py` must account for all time-drift patterns.
- **[[client-rendered-json-section-on-now]]** — `/now` mixes server-rendered feeds (cron, markers) and client-rendered sections (JSON fetch, JS IIFE). Four gotchas: hardcoded section numbers, missing bootstrap targets, XSS safety, silent-fail behavior.

### Related Code Patterns

**All sync scripts follow the same flow:**
1. Fetch upstream data (API, RSS, file)
2. Parse and format to HTML
3. Call `replace_marker()` to splice into existing HTML
4. Check `content_changed()` (with `strip_volatile()`) before commit
5. Update `.feeds-heartbeat.json`

**Scripts in `bin/`:**
- `update-whoop.py` — WHOOP daily, OAuth2, encrypted token rotation
- `update-spotify.py` — Spotify every 30 min, state-cache hash
- `update-plex.py` — Plex every 6h, static token
- `update-public-feeds.py` — MLB/Goodreads/FBST every 6h, unauthenticated
- `update-projects.py` — GitHub events daily, active/back-burner classification (THIS FIX)
- `update-project-docs.py` — Roadmap/changelog daily, per-project adapters

All share `_shared.py` utilities (`replace_marker()`, `content_changed()`, `strip_volatile()`, `relative_time_html()`).

### CLAUDE.md References

See CLAUDE.md "Data feeds on /now" (lines 139–174) for the canonical feed architecture:
- 8 feeds with heartbeats in `.feeds-heartbeat.json`
- Marker pairs (`<!-- {FEED}-START/END -->`) for each feed
- Content outside markers freezes; content inside is regenerated
- Bootstrap rule: missing markers cause the sync to silently skip that page
- "Adding a new data feed" (line 174) documents the 8-step process

## Testing

Two categories of tests:

**Unit test (config → render function):**
```python
def test_render_card_with_roadmap_items():
    project = {
        "slug": "test",
        "name": "Test",
        "desc": "...",
        "roadmap_items": ["Feature A", "Feature B"]
    }
    html = render_card(project, [], "June 25, 2026 at 12:00 AM PDT")
    assert '<div class="nb-proj-roadmap">' in html
    assert '<li>Feature A</li>' in html
    assert '<li>Feature B</li>' in html
```

**E2E test (full sync round-trip):**
```python
def test_roadmap_items_survive_cron_sync():
    # Load projects-config
    config = load_config()
    
    # Find a project with roadmap_items
    aleph = next(p for p in config if p['slug'] == 'aleph')
    assert len(aleph['roadmap_items']) > 0
    
    # Run sync
    main()  # Calls update-projects.py logic
    
    # Verify HTML contains the roadmap
    html = read_now_html()
    for item in aleph['roadmap_items']:
        assert item in html  # Exact text match
        
    # Verify idempotency: run twice, should be identical
    old_html = html
    main()
    new_html = read_now_html()
    assert old_html == new_html  # Byte-for-byte match
```

## Files Modified

- `bin/projects-config.json` — added `roadmap_items` array to all 9 projects (git commit `6389e87`)
- `bin/update-projects.py` — extended `render_card()` to output roadmap section (git commit `6389e87`)
- `now/index.html` — regenerated with roadmap items restored (git commit `6389e87`)

## Deployment Notes

**Live verification (2026-06-25 07:02 UTC):**
```bash
$ curl https://jameschang.co/now/ | grep -c "upcoming roadmap"
9
$ curl https://jameschang.co/now/ | grep "Standings accuracy refinement"
Found (part of The Fantastic Leagues card)
```

GitHub Pages deployed within ~1 minute of push. Roadmap items now persistent across future cron runs because they're part of the programmatic output (render_card), not hand-edits to the HTML.

## Timeline

| Date | Event |
|------|-------|
| 2026-06-23 00:35 | Manually added roadmap_items to `/now/index.html` (commit `4a9e6f4`) |
| 2026-06-23 15:31 | First cron sync removed them (commit `2f89779` "sync project TLDRs") |
| 2026-06-25 06:45 | Investigated root cause: `render_card()` doesn't read roadmap_items |
| 2026-06-25 06:50 | Added `roadmap_items` to config + modified render function |
| 2026-06-25 06:52 | Tested locally: roadmap items render correctly |
| 2026-06-25 06:55 | Pushed to main (commit `6389e87`) |
| 2026-06-25 07:02 | Live verification: 9 roadmap sections now on production |
