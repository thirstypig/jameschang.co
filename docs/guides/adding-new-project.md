# Adding a project to the doc sync

The `/now` page syncs changelogs and roadmaps from source repositories. To add a new project's docs to the sync:

## Steps

1. Add a new `(slug, repo, doctype)` tuple to `PROJECT_DOCS` in `bin/update-project-docs.py`.

2. Add a matching `<!-- {DOCTYPE}-START -->` / `<!-- {DOCTYPE}-END -->` marker pair to the destination HTML page in the **same commit** (bootstrap requirement — without markers, the cron silently does nothing forever).

3. Update `tests/test_project_docs.py::TestProjectDocsConfig::test_expected_entries_present` and `tests/test_site_e2e.py::TestProjectDocSyncMarkers::EXPECTED` to include the new entry.

4. Verify `TLDR_FETCH_TOKEN` PAT has `Contents:Read` scope on the source repo (necessary for any private repo).

5. Author `docs/{doctype}.md` in the source repo following the heading-line convention (see **Markdown conventions** below). The sync will pick it up on the next 13:15 UTC cron tick (or trigger via `workflow_dispatch`).

## Markdown conventions

The sync uses small dedicated parsers, not a general markdown library. Authors of source-repo `docs/*.md` files must follow these rules — anything outside the contract is ignored, malformed entries are skipped silently. Supported inline: `**bold**` → `<strong>`, `` `code` `` → `<code>`. HTML in source is escaped.

### `docs/changelog.md` — one release per H2

The H2 line carries metadata; the H3 is the human title; bullets are the body.

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

- H2 format: `## <version> — <date> [— <tag1, tag2, ...>]`. Em-dash (`—`, U+2014) is canonical; ASCII `--` works as fallback. The date can carry trailing suffix like `2026-04-13 · Session 63` — anything up to the next em-dash is the date.
- Tags map 1:1 to CSS classes in `projects/projects.css`. Known tags: `feature`, `improvement`, `security`, `fix`, `breaking`, `docs`, `refactor`. Unknown tags get a sanitized class name.
- Title (`###` line) is optional but recommended.
- Body must be bullets (`-` or `*`). Paragraphs above the bullets are ignored. Continuation lines (indented 2+ spaces) are joined into the preceding bullet.

### `docs/roadmap.md` — one module per H2

H2 line carries `<name> — <NN>%`. Inside each module: prose description, then optional `### Workflow` (ordered list) and `### Features` (task list).

```markdown
## CPSIA / CPC — 60%
Generate Children's Product Certificates for products intended for children
12 and under. Covers the seven required CPC fields under CPSIA Section 14(a).

### Workflow
1. Add children's product with SKU, manufacturer, country of origin
2. Upload lab test report from a CPSC-accepted lab
3. Complete CPC form — seven required fields
4. Preview and generate the formatted PDF

### Features
- [x] Product creation (children's product type)
- [x] CPC 7-field data entry form
- [ ] Cohort-aware product creation form
- [~] CPSC e-Filing integration
```

- H2 format: `## <name> — <NN>%`. Percent must be an integer 0–999.
- Description is the prose between the H2 line and the first H3 (or end of section). Multi-line descriptions collapse to a single space-joined paragraph.
- `### Workflow` items use `1.`, `2.`, ... ordered-list syntax.
- `### Features` items use task-list syntax with three states:
  - `- [x]` → shipped
  - `- [ ]` → committed but unshipped
  - `- [~]` → explicitly deprioritized

## Adapter factory

The sync is driven by per-project adapters — small callables that fetch + parse one project's source-of-truth format. Currently wired (6 entries):

| Slug | Doctype | Source | Destination |
|------|---------|--------|-------------|
| `aleph` | changelog | `thirstypig/alephco.io-app:docs/changelog.md` | `/projects/aleph/changelog/` |
| `aleph` | roadmap | `thirstypig/alephco.io-app:docs/plans/roadmap.md` | `/projects/aleph/roadmap/` |
| `fantastic-leagues` | changelog | `thirstypig/TheFantasticLeagues:docs/changelog.md` | `/projects/fantastic-leagues/changelog/` |
| `fantastic-leagues` | roadmap | `thirstypig/TheFantasticLeagues:client/src/pages/Roadmap.tsx` | `/projects/fantastic-leagues/roadmap/` |
| `judge-tool` | changelog | `thirstypig/thejudgetool:docs/changelog.md` | `/projects/judge-tool/changelog/` |
| `judge-tool` | roadmap | `thirstypig/thejudgetool:docs/PRODUCTION_ROADMAP.md` | `/projects/judge-tool/roadmap/` |

Custom adapters can parse heterogeneous sources (plain markdown, custom-shape markdown, TypeScript data structures) without forcing a shared convention across repos.
