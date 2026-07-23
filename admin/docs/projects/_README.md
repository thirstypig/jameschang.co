<!-- How the per-project docs work — the portfolio dimension. -->
# Projects

Each project in the portfolio gets a folder here (slug matches `bin/projects-config.json`
and the `/admin/` portfolio board): `aleph/`, `spar/`, `fantastic-leagues/`, …

Inside each project folder:
- `prds/` — one file per feature (`PRD-###-<slug>.md`)
- `roadmap.md` — that project's macro roadmap
- `adrs/` — one file per big engineering decision (`ADR-###-*.md`)
- `notes.md` — scratchpad

Every doc carries `project: <slug>` in its frontmatter (defined in Step 2), so the
board can filter the whole hub by project. `aleph/` is seeded below as the worked example.
