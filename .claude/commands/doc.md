Synchronize every project doc against recent changes, atomically.

The argument `$ARGUMENTS` is an optional short description of what to document (e.g. `code review session`, `now page update`, `testing infrastructure`). If empty, infer from the last few commits / session transcript.

## Why this command exists

"Document the update" has too many ambiguous targets — README, CLAUDE.md, docs/test-plan.md, docs/solutions/, llms.txt. Without a checklist, docs drift: CLAUDE.md says "71 tests" while the real count is 72, test-plan.md claims a function isn't tested when it is, CLAUDE.md references a directory that doesn't exist. This command turns "update the docs" into a deterministic sweep.

## Phase 1 — Discover the doc surface

Run these and build a *project-specific inventory*. **Only update files that actually exist.** Never create new top-level doc files without explicit user approval.

```bash
# Top-level docs
ls README.md CLAUDE.md llms.txt sitemap.xml 2>/dev/null
# docs/ directory
ls docs/*.md docs/solutions/*/*.md 2>/dev/null
# Todo files
ls todos/*.md 2>/dev/null | tail -5
```

Report the list back so the user can spot anything unusual. Classify each found file:

| Type | Purpose | Update style |
|---|---|---|
| README.md | External audience — what is this project? | Edit in place; only if top-level architecture changed |
| CLAUDE.md | Agent/contributor conventions | Edit in place when conventions, architecture, or counts change |
| docs/test-plan.md | Testing strategy and inventory | Edit in place when tests are added/removed; update counts |
| docs/solutions/*.md | Institutional knowledge — past solved problems | **Append** new solutions; never edit past entries |
| llms.txt | Plain-text summary for LLM crawlers | Edit in place when projects or positioning changes |
| sitemap.xml | URL index for search engines | Add new URLs; remove dead ones |
| todos/*.md | Code-review findings | Update status in YAML frontmatter when resolved |

## Phase 2 — Review what changed

```bash
git log --oneline -15
git diff HEAD~5..HEAD --stat
```

Read through recent commits. Classify each meaningful change:

- **Architectural / convention change** → CLAUDE.md
- **Testing changes** → docs/test-plan.md + CLAUDE.md test count
- **New page / URL added** → sitemap.xml + llms.txt
- **Problem solved worth documenting** → docs/solutions/
- **Content / positioning change** → README.md + llms.txt
- **Nothing user-visible** → no doc update needed

**Never dump the full git log into a doc.** A doc entry is a curated story, not a diff.

## Phase 3 — Cross-reference verification

Before writing, read the doc files and check for **drift from reality**:

- Test counts in CLAUDE.md and docs/test-plan.md should match `python3 -m pytest tests/ --collect-only -q 2>/dev/null | tail -1`.
- Architectural claims should match the actual code (e.g., "7 photos" in headshot rotation — count the actual `<picture>` elements).
- File path references in CLAUDE.md should point to files that exist.
- URLs in sitemap.xml should correspond to actual HTML files.
- Print stylesheet order values in CLAUDE.md should match the CSS.
- CSS token values in CLAUDE.md should match styles.css.
- Privacy policy claims should match what the site actually does.
- Link integrity: if CLAUDE.md links to `docs/test-plan.md`, that file must exist.

List each drift found. Fix them as part of this same update pass — do not leave known-wrong claims in place because "someone else" will fix them.

## Phase 4 — Write updates

For each doc that needs updating:

1. **Read the current file** in full before editing. Understand the structure and style — mimic it.
2. **Match tone and format** — CLAUDE.md uses terse bullet lists and tables; README.md is a concise overview; docs/test-plan.md is structured with tables. Follow the existing pattern.
3. **Be specific** — "Updated docs" is useless. "Updated test count from 71 to 72 after adding corrupt-JSON recovery test" tells the next reader what changed and why.
4. **Prefer edits in place** for reference sections. **Prefer appends** for solution docs.
5. **Date stamps**: use the current date (`YYYY-MM-DD` ISO format). Convert relative dates in the user's request ("last week", "Thursday") to absolute.

## Phase 5 — Report

Output exactly:

```
Docs updated:
  ✏️  CLAUDE.md              — <one-line reason>
  ✏️  docs/test-plan.md      — <one-line reason>
  ⏭  README.md              — skipped (no top-level changes)
  ⏭  llms.txt               — skipped (no positioning changes)

Drift found and fixed:
  - CLAUDE.md said "71 tests"; actual 72. Updated.
  - docs/test-plan.md missing corrupt-JSON test. Added.

Drift found but NOT fixed (needs decision):
  - <item>: <reason why it needs user input>

Not committed. Review changes, then commit when ready.
```

## Phase 6 — Do NOT commit

This command only writes docs. It does not commit, push, or trigger tests. That's the calling session's job.

## Guardrails

- **Don't create new top-level docs without explicit approval.** If the project has no CHANGELOG.md and the user hasn't asked for one, skip that step with a note.
- **Don't touch generated files.** `resume.pdf`, `.feeds-heartbeat.json`, `.spotify-state.json`, `now/index.html` feed content.
- **Don't rewrite history.** Past docs/solutions/ entries, past todo entries — those are immutable records. New info goes in new entries.
- **Don't pretend things are done that aren't.** If a feature is half-shipped, say so. Better to flag "pending" than create drift.
- **Don't inflate.** Small change, small entry. A typo fix doesn't need a docs/solutions/ write-up; a subtle PBKDF2 mismatch does.
- **Don't duplicate.** If docs/solutions/ has the full story, CLAUDE.md just needs the one-line architectural note. Don't copy the same content to three files.
