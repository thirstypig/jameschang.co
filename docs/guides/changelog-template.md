# Changelog Template

Use this template in your source repos as `docs/changelog.md` to enable automatic syncing to the jameschang.co project deep-dive pages.

---

## Format Rules

**One release per H2.** The H2 line carries metadata; the H3 is the human title; bullets are the body.

```markdown
## v0.12.0 — 2026-04-14 — security, improvement
### Code review batch — security, quality & cleanup

- **Security:** Fixed SoQL injection in ENERGY STAR search
- **Quality:** 47 inline auth checks → router middleware
- **Cleanup:** Renamed service files to PascalCase

## v0.11.0 — 2026-04-13 — improvement
### Admin consolidation — 11 pages to 6

- 11 sidebar items → 6 (Operations, Planning groups)
- ~3,700 lines of static JSX eliminated
```

### H2 Format

`## <version> — <date> [— <tag1, tag2, ...>]`

- **Version**: Semantic (v0.12.0) or date-based (2026-04-14)
- **Date**: ISO format (YYYY-MM-DD) or natural (April 14, 2026)
- **Tags** (optional): Comma-separated descriptors from the list below
  - Em-dash (`—`, U+2014) is canonical; ASCII `--` works as fallback
  - Date can have trailing suffix: `2026-04-13 · Session 63` (anything before next em-dash is included)

### Tag Reference

Tags map to CSS classes in `projects/projects.css`. Known tags (pre-styled):

| Tag | Color | Usage |
|-----|-------|-------|
| `feature` | green | New capability |
| `improvement` | blue | Enhancement to existing feature |
| `security` | red | Security fix or hardening |
| `fix` | orange | Bug fix |
| `breaking` | red-bold | Breaking change |
| `docs` | gray | Documentation update |
| `refactor` | purple | Code quality / architecture |

Unknown tags get a sanitized class name `[a-z0-9-]` — add CSS if you want styling.

### H3 Format (Title)

`### Release Title — optional context`

- Optional but recommended
- Empty title renders as `<h3 class="release-title"></h3>`
- Plain text or one-line description

### Body Format (Bullets)

- Must be bullets (`-` or `*`)
- Paragraphs above bullets are **ignored**
- Continuation lines (indented 2+ spaces) join into the preceding bullet
- Inline markdown supported: `**bold**` → `<strong>`, `` `code` `` → `<code>`
- HTML is escaped (literal `<Component>` renders as text, not HTML)

---

## Example: Complete Changelog

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## v1.2.0 — 2026-06-22 — feature, improvement
### Public API launch — GraphQL + REST endpoints

- **Feature:** GraphQL API with 40+ query/mutation types
- **Feature:** OpenAPI 3.0 spec auto-generated from schema
- **Improvement:** Response times cut 30% via N+1 query elimination
- **Improvement:** Added request tracing for all endpoints
  Uses correlation IDs to track requests across services
- **Docs:** API reference guide and 5 example workflows

## v1.1.5 — 2026-06-18 — fix, security
### Hotfix for session vulnerability

- **Security:** Session tokens now rotated every 4 hours (was never)
- **Security:** Fixed timing attack in password comparison
- **Fix:** Race condition in concurrent writes to billing table

## v1.1.4 — 2026-06-14 — improvement
### Performance tuning

- 25% faster report generation via caching layer
- Reduced memory footprint by 40% for large datasets
- Database connection pooling now configurable

## v1.1.3 — 2026-06-10 — fix
### Bug fixes from early June

- Fixed logout hanging on slow networks
- Corrected time zone handling for all-day events
  Daylight saving time now handled correctly
- Resolved duplicate charges for failed payment retries
```

---

## Integration: How It Syncs

1. **Source:** Your repo → `docs/changelog.md` (this format)
2. **Parser:** `bin/update-project-docs.py` in jameschang.co
3. **Destination:** `/projects/[slug]/changelog/index.html`
4. **Schedule:** Daily at 6:15 AM PT (13:15 UTC)
5. **Markers:** Must exist in destination HTML:
   ```html
   <!-- CHANGELOG-START -->
   <!-- Content replaced here -->
   <!-- CHANGELOG-END -->
   ```

---

## Checklist: Adding to Your Repo

- [ ] Create `docs/changelog.md` in your source repo
- [ ] Use the format above (H2 per release, H3 title, bullets body)
- [ ] Test locally: `python3 bin/update-project-docs.py` (from jameschang.co)
- [ ] Add markers to `/projects/[slug]/changelog/index.html` if not present
- [ ] Update `bin/projects-config.json` if it's a new project
- [ ] Sync runs automatically daily; verify on next cron tick

---

## Notes

- **No library required:** Parser is hand-rolled regex in Python (no markdown library)
- **Fail-safe:** If source is missing, cron skips silently (no crash)
- **Deferred:** If no `docs/changelog.md` exists, the page shows empty until you add it
- **Versioning:** Choose semantic or date-based consistently within your repo
- **Dates:** ISO format (YYYY-MM-DD) is preferred for sorting and parsing
