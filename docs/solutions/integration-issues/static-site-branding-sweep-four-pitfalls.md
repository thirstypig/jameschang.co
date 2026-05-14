---
title: "Static site brand terminology sweep — four pitfalls: grep scope, cron source-of-truth, body.find() -1 trap, and regression guard"
category: integration-issues
tags: [branding, grep-sweep, cron, cross-repo-sync, e2e-tests, pytest, regression-guard, content-management]
symptom: "stale brand terminology persists after a sweep (missed file); E2E ordering test breaks when an optional HTML element is removed; cron silently reverts a manual patch within 24 hours"
root_cause: "targeted grep misses files; body.find() returning -1 produces wrong ordering comparisons silently; cron-derived now/index.html content is owned by an upstream repo, not this file; no regression test guards against re-entry"
module: static-site-content / now-page-sync-pipeline / tests/test_site_e2e.py
date_solved: 2026-05-13
severity: low
---

# Static site brand terminology sweep — four pitfalls

## Background

On 2026-05-13 all KCBS-specific terminology was removed from The Judge Tool project pages on jameschang.co, replacing "KCBS", "KCBS-style BBQ", and "KCBS-sanctioned" with "Barbeque" / "sanctioned competition". Four distinct pitfalls were encountered. Each is documented below as a reusable lesson.

---

## Pitfall 1 — Targeted grep scope misses files

### Symptom

After the sweep, a code-review agent found "Digital KCBS BBQ competition judging" still present in `projects/index.html`. The initial grep had not targeted this file.

### Root cause

The sweep was scoped to a hand-reasoned list of "obvious" files (the three judge-tool sub-pages, the homepage, and now/index.html). `projects/index.html` — the projects landing page — was not in the mental model. Static site repos accumulate content in unexpected places: project landing pages, cross-nav fragments, shared layout partials, JSON-LD blocks.

### Fix

Always begin with a **repo-wide grep** from the repo root. Never substitute a file list:

```bash
grep -rn "KCBS\|BBQ\|old-brand-term" . \
  --include="*.html" \
  --include="*.css" \
  --include="*.js" \
  --include="*.json" \
  --include="*.py" \
  --include="*.md"
```

Use the file list from the repo-wide grep as your work list, not one you constructed by reasoning about the site structure.

### All content vectors to audit

A terminology sweep on this site must cover every vector where a term can appear:

| Vector | What to grep |
|--------|--------------|
| HTML body text | `grep -rn "TERM" . --include="*.html"` |
| Meta/OG `content=` | Same pass — grep finds inline text |
| JSON-LD `"description"` and `"name"` | Same pass |
| Alt text on `<img>` | Same pass |
| CSS class names | `grep -rn "TERM" . --include="*.css"` |
| Python feed builders (emit HTML strings) | `grep -rn "TERM" bin/` |
| Image filenames | `find . -name "*TERM*" -type f` |
| Screenshot alt text in HTML | Same HTML pass |

---

## Pitfall 2 — Cron-derived file reverts manual patches within 24 hours

### Symptom

`now/index.html` was patched manually to replace "KCBS-style BBQ" in the `<!-- TLDR-judge-tool-START/END -->` block. Todo #145 was filed noting this would be silently overwritten within 24 hours by the 7 AM PT `projects-sync` cron.

### Root cause

`bin/update-projects.py` calls `replace_marker()` to rewrite the entire `<!-- TLDR-{slug}-START -->...<!-- TLDR-{slug}-END -->` block on every run, sourcing the text from the upstream repo's `CLAUDE.md`. Any manual edit inside the markers is overwritten. The derived file is not the source of truth.

### Investigation outcome

In this case, the Judge Tool repo's `CLAUDE.md` `<!-- now-tldr -->` block had **already been updated** to use "barbeque" (no KCBS). The cron ran at 9:12 AM PT the same day and produced correct output. The todo was closed as a false alarm — the derived file had been stale for at most one day before self-healing.

### Rule

Before patching content inside a `<!-- {FEED}-START/END -->` block in `now/index.html`:

1. Identify the upstream source: for project TLDRs, check `bin/projects-config.json` → `repo` field → that repo's `CLAUDE.md` `<!-- now-tldr -->` block.
2. Read the upstream source. If it already contains the correct text, do nothing — the next cron run will resolve the derived file.
3. If the upstream source has the stale text, fix **the upstream source only** (cross-repo change).
4. Never patch content inside a sync-managed marker block as the fix — it is at best a temporary cache that will be overwritten.

See also: `docs/solutions/integration-issues/marker-boundary-content-staleness.md` (general marker contract surface pitfalls).

---

## Pitfall 3 — `body.find()` returning -1 causes silent wrong ordering comparisons

### Symptom

`test_deep_dive_block_order` in `tests/test_site_e2e.py` failed after the `snapshot-banner` div was removed from `projects/judge-tool/tech/index.html`. The test enforced `project-nav → snapshot-banner → work-hero` ordering on all deep-dive pages.

### Root cause

`str.find()` returns `-1` when the substring is absent. The original comparison:

```python
# FRAGILE — do not use this pattern:
i_snap = body.find('class="snapshot-banner"')
ok = i_pnav < i_snap < i_hero
```

When `i_snap == -1`, Python evaluates `i_pnav < -1 < i_hero`. For any non-negative `i_pnav` (which is always the case when the element is found), `i_pnav < -1` is `False`, and the chain short-circuits — producing a spurious failure with a confusing message (`project-nav=42, snapshot-banner=-1, work-hero=800`). The inverse is also dangerous: if `i_pnav == 0`, `0 < -1` is `False`, which happens to be the right answer for the wrong reason. The test was accidentally catching the missing element but would not reliably generalize to other optional elements.

### Fix

Guard every `find()` result before using it in any comparison. Explicitly distinguish required from optional elements:

```python
i_pnav = body.find('class="project-nav"')
i_snap = body.find('class="snapshot-banner"')  # optional
i_hero = body.find('class="work-hero"')

# Required elements fail hard with a clear message:
if i_pnav == -1 or i_hero == -1:
    failures.append(
        f"{f}: missing required element — project-nav={i_pnav}, work-hero={i_hero}"
    )
    continue

# Optional element changes the assertion but never causes a spurious failure:
if i_snap == -1:
    ok = i_pnav < i_hero           # banner absent: only check required ordering
else:
    ok = i_pnav < i_snap < i_hero  # banner present: enforce full ordering
```

### General rule

**Any time `str.find()` or `str.index()` results feed into a comparison, guard for `-1` first.** The pattern `a < b < c` where any of the three is `-1` will behave arithmetically but incorrectly. The guard both produces a useful error message and prevents the silent wrong-answer case.

---

## Pitfall 4 — No regression guard → term can re-enter via cron or new pages

### Symptom

After the sweep, there was no automated check preventing "KCBS" from re-appearing in the judge-tool project pages — whether from a new page being added without the sweep, a cron run from an un-updated upstream source, or a future edit that inadvertently re-introduces the term.

### Fix

Added `TestJudgeToolBranding` to `tests/test_site_e2e.py`:

```python
class TestJudgeToolBranding:
    """Regression guard: 'KCBS' must not reappear in Judge Tool project pages.

    The membership section on index.html and calendar event names in
    now/index.html legitimately retain 'KCBS' — these pages are intentionally
    excluded. The project deep-dive pages have no valid reason to use the term.
    """

    JUDGE_TOOL_PAGES = [
        f for f in STANDARD_PAGES
        if f.startswith("projects/judge-tool/")
    ]

    def test_no_kcbs_in_judge_tool_pages(self):
        assert self.JUDGE_TOOL_PAGES, "No judge-tool pages found — path filter broke"
        failures = []
        for f in self.JUDGE_TOOL_PAGES:
            _, body = fetch(f)
            if "KCBS" in body:
                positions = [m.start() for m in re.finditer("KCBS", body)]
                failures.append(f"{f}: 'KCBS' at char positions {positions[:5]}")
        assert not failures, (
            "Legacy KCBS branding must not appear in Judge Tool project pages:\n"
            + "\n".join(failures)
        )
```

Note `assert self.JUDGE_TOOL_PAGES` — a guard that prevents the test from silently vacuous-passing if the path filter breaks and yields an empty list.

### General pattern for any term-banishment regression guard

```python
class TestBrandingRegression:
    TARGET_PAGES = [f for f in STANDARD_PAGES if f.startswith("projects/<slug>/")]
    BANNED_TERMS = ["OLD TERM", "LEGACY TERM"]

    def test_banned_terms_absent(self):
        assert self.TARGET_PAGES, "path filter broke — empty page list"
        failures = []
        for f in self.TARGET_PAGES:
            _, body = fetch(f)
            for term in self.BANNED_TERMS:
                if term in body:
                    failures.append(f"{f}: found '{term}'")
        assert not failures, "\n".join(failures)
```

---

## Summary table

| Pitfall | Root cause | Fix |
|---------|------------|-----|
| Grep missed a file | Targeted file list, not repo-wide | `grep -rn "TERM" . --include="*.html"` from root |
| Cron reverted manual patch | Derived file is not the source of truth | Fix upstream repo's CLAUDE.md; never patch inside sync markers |
| `body.find()` -1 comparison | `str.find()` returns -1 for absent elements; `a < -1 < c` is wrong | Guard for -1 explicitly; handle optional vs required separately |
| Term re-entered after sweep | No CI gate | Add a `TestBrandingRegression` class to the E2E suite |

## Related docs

- `docs/solutions/integration-issues/marker-boundary-content-staleness.md` — general marker contract surface; content outside markers freezes silently
- `docs/solutions/integration-issues/relative-time-html-defeats-content-changed-cache.md` — another cron sync gotcha (volatile time strings defeating content-change detection)
