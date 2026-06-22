# Setup: Add Changelog Syncing to Your Source Repo

Quick guide to enable automatic changelog syncing from your project repos to jameschang.co.

---

## Step 1: Create `docs/changelog.md` in Your Source Repo

In your project repo (e.g., `thirstypig/alephco.io-app`):

```bash
# Create the docs directory if it doesn't exist
mkdir -p docs

# Create changelog.md using the template
touch docs/changelog.md
```

Then copy the format from `docs/guides/changelog-template.md` (this repo) and start adding your releases.

**Example** (`docs/changelog.md`):

```markdown
## v0.3.0 — 2026-06-22 — feature
### Prop 65 compliance module launch

- **Feature:** Auto-generate Prop 65 warning labels from product SKU
- **Feature:** California chemical list auto-sync (weekly)
- **Improvement:** Reduced label generation time from 2 min to 15 sec
```

---

## Step 2: Verify Sync Configuration

Check that your project is already wired in `bin/projects-config.json`:

```bash
cd /path/to/jameschang.co
grep -A 10 '"slug": "aleph"' bin/projects-config.json
```

If your project is NOT listed, add it:

```json
{
  "slug": "aleph",
  "repo": "thirstypig/alephco.io-app",
  "name": "Aleph",
  ...
}
```

---

## Step 3: Verify Destination Markers

On jameschang.co, check that `/projects/[slug]/changelog/index.html` has the markers:

```html
<!-- CHANGELOG-START -->
<!-- Content will appear here -->
<!-- CHANGELOG-END -->
```

If markers are missing, add them:

```bash
# Edit the file and insert:
<!-- CHANGELOG-START -->
<!-- CHANGELOG-END -->
```

---

## Step 4: Test the Sync

Trigger the sync manually:

```bash
cd /path/to/jameschang.co
python3 bin/update-project-docs.py
```

Or wait for the daily cron (6:15 AM PT / 13:15 UTC).

---

## Repos to Update

Add `docs/changelog.md` to these source repos:

| Repo | Config Slug | Destination |
|------|------------|-------------|
| `thirstypig/alephco.io-app` | `aleph` | `/projects/aleph/changelog/` |
| `thirstypig/TheFantasticLeagues` | `fantastic-leagues` | `/projects/fantastic-leagues/changelog/` |
| `thirstypig/thejudgetool` | `judge-tool` | `/projects/judge-tool/changelog/` |

---

## Format Validation

The sync parser is strict but forgiving:

✅ **Will work:**
- H2: `## v0.1.0 — 2026-06-22 — feature`
- H3: `### Release title` (or omitted)
- Bullets: `- **Bold:** text` or plain bullets
- Inline markdown: `**bold**`, `` `code` ``

❌ **Will skip silently:**
- H1 entries (only H2 parsed)
- Paragraphs above bullets (bullets only)
- Unknown tag names (sanitized to class name)
- Malformed dates or versions (logged but skipped)

---

## Troubleshooting

**Q: Changelog shows empty on jameschang.co**
- A: Check that `docs/changelog.md` exists in source repo
- Check that markers exist in destination HTML
- Wait for next cron tick (6:15 AM PT / 13:15 UTC)

**Q: My releases show but without styling**
- A: You used a tag that's not in `projects/projects.css`
- Add CSS rule: `.release-[tag-name] { ... }`

**Q: Sync failed with "marker not found"**
- A: The destination page is missing `<!-- CHANGELOG-START/END -->`
- Add the markers manually to the HTML

**Q: How often does it sync?**
- A: Daily at 6:15 AM PT (13:15 UTC) via GitHub Actions
- You can trigger manually: `python3 bin/update-project-docs.py`

---

## Next Steps

1. Add `docs/changelog.md` to Aleph, Fantastic Leagues, Judge Tool
2. Author your first release using the template
3. Commit and push
4. Changelog auto-appears on jameschang.co the next sync

See `docs/guides/changelog-template.md` for the full format spec.
