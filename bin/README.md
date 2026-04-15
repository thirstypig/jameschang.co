# /bin/ — sync scripts

## `sync-work.py`

Keeps the `/work/` replica pages in loose sync with the live source
projects they mirror.

### What it does today (pilot scope)

- Fetches the public `Changelog.tsx` from the `fbst` repo on GitHub
- Extracts the latest release version + date + title via regex
- Patches a `Last synced …` line into the snapshot banner on
  `/work/fantastic-leagues/changelog/index.html`

It does **not** yet regenerate the full replica body from source — just
the synced-at marker. That's the next iteration.

### Running it

Manual:

    python3 bin/sync-work.py

Scheduled: a GitHub Action runs this every Monday at 15:00 UTC and
commits any changes — see `.github/workflows/sync-work.yml`. You can
also trigger it manually from the repo's **Actions** tab → "Sync
/work/ replica pages" → **Run workflow**.

### Extending to new sources

Pattern: add a `sync_*()` function to `sync-work.py` that:

1. Fetches source content from a public URL (GitHub raw, or a published
   JSON/meta file on the project's site)
2. Extracts the fields you care about
3. Patches the target `/work/*.html` file idempotently (safe to re-run)
4. Returns `True` if anything changed

Then add it to the `jobs` list in `main()`.

### Adding private source projects (Aleph, Judge Tool)

Two options:

**A. Publish a public JSON from each source project.** Each source
project adds a build step that emits, e.g.,
`public/meta/changelog.json`, and the jameschang.co sync fetches from
the live URL. Cleanest pattern — no cross-repo auth, format stays
stable. Requires a small change in each source project.

**B. Give the workflow a PAT with read access to the private repos.**
Store as a repo secret (`SOURCE_REPO_PAT`); pass it to the action as
`GH_TOKEN`; clone the private repo in-step. Works today with no
changes to source projects, but adds a maintenance surface (the PAT
expires).

Option A is strongly preferred long-term; Option B is viable as a
stopgap.

### Known limitations

- Regex parsing of TSX source is brittle. If `fbst`'s `Changelog.tsx`
  stops following the `version: "x.y.z"` / `date: "YYYY-MM-DD"` /
  `title: "..."` pattern (e.g., it's refactored to load from JSON or
  a headless CMS), the parser here needs updating — or, better, the
  source project starts emitting a stable JSON meta file (Option A
  above).
- Aleph and Judge Tool replicas are not synced yet — see Option A or B
  to add them.
- The sync is a "last-seen" marker, not full-content regeneration. For
  real content sync, the replica HTML would need to be regenerated from
  a template + parsed source data on every run. That's intentionally
  deferred: the current replicas carry a lot of hand-written prose
  context that isn't in the source files.
