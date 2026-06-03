---
title: "Adding a client-rendered JSON-backed section to /now"
category: integration-issues
tags: [now-page, client-render, json-feed, dialog-modal, xss, bootstrap, section-numbering]
severity: moderate
module: now-page-client-render
symptom: "Adding a new /now section that reads a root JSON file and renders client-side hits four non-obvious traps: section numbering, modal bootstrap, XSS surface, and silent-fail — none enforced by the cron/marker machinery that governs server-rendered feeds."
root_cause: >-
  /now mixes two rendering models. Server-rendered feeds live between
  <!-- FEED-START/END --> markers and are governed by sync scripts + e2e marker
  tests. Client-rendered sections (hitlist, bucketlist, quotes) are pure now/now.js
  IIFEs that fetch a JSON file and build DOM at runtime — they bypass markers, the
  cron, and most static-HTML tests, so their conventions (numbering, bootstrap,
  escaping) are tribal knowledge until written down.
date_solved: 2026-06-02
---

# Adding a client-rendered JSON-backed section to /now

## Context

`/now` has two kinds of sections:

1. **Server-rendered feeds** (WHOOP, Spotify, MLB, …) — a Python sync script writes
   HTML between `<!-- {FEED}-START -->` / `-END -->` markers in `now/index.html`.
   Governed by cron + `replace_marker()` + `EXPECTED_MARKERS` e2e tests.
2. **Client-rendered sections** (Thirsty Pig hitlist, bucket list, **quotes**) — a
   self-contained IIFE in `now/now.js` fetches a JSON file and builds the DOM at
   runtime. No markers, no cron, no sync script.

This doc is the canonical recipe for adding a **type 2** section. It was written
while building the `/12 quotes` section (`quotes.json` → grid of cards → expand
modal), generalizing the `bucketlist.json` precedent.

## The recipe

1. **Author the data file** at the repo root: `quotes.json`, shape
   `{ "last_updated": ISO, "items": [...] }` where **array order = display order**
   (mirror `bucketlist.json`).
2. **Seed an empty render target** in `now/index.html`:
   `<section class="nb-section" id="quotes-section"></section>`. The IIFE fills it.
3. **Seed any shared UI** (e.g. an expand `<dialog>`) in the **same commit** — see
   gotcha #2.
4. **Write the IIFE** in `now/now.js`: fetch same-origin with `{ cache: 'reload' }`,
   `.remove()` the section on error/empty, build nodes with `textContent`.
5. **Add CSS** to `notebook.css` using design tokens (`--surface`, `--ink`,
   `--accent`, `--shadow-offset`, `--display`, `--mono`).
6. **Add tests** to `tests/test_site_e2e.py` (a `TestQuotes`-style class): JSON
   schema + unique ids + the render target/dialog presence + `now.js` references
   the JSON path.

## The four gotchas

### 1. Section numbers are hardcoded in JS and continue PAST the static range

Server-rendered sections are numbered `/01`–`/09` in static HTML. Client-rendered
sections **hardcode their own number in JS** and continue the sequence:

| Section | Number | Set where |
|---|---|---|
| hitlist | `/10` | `now/now.js` (`num.textContent = '/10'`) |
| bucket list | `/11` | `now/now.js` |
| quotes | `/12` | `now/now.js` |

There is no auto-numbering. A new client section must hardcode the **next** number.
The e2e test `TestNowSectionStructure::test_section_numbers_are_sequential` only
asserts the static `/01`–`/09` from `body`, so a JS-rendered `/12` neither satisfies
nor breaks it — verify the number by eye / via a DOM check, not the suite.

### 2. Bootstrap the container AND any shared modal in the SAME commit

The IIFE *populates* `#quotes-section` and the shared `<dialog id="quote-modal">`;
it does **not** create them. If either is missing from `now/index.html`, the section
silently no-ops (the `if (!container) return;` / `if (!modal) return;` guards). This
is the client-side analog of the marker-bootstrap rule (see cross-links): the HTML
placeholders and the JS that fills them must land together. Add the render-target id
+ dialog id to an e2e test so a future deletion fails fast.

### 3. Render with `textContent`, never `innerHTML` (XSS surface)

Quote/idiom/poem text is arbitrary content (CJK, Latin, `<angle brackets>`, quote
marks). Build every node with `document.createElement` + `textContent` so markup is
inert. A small helper keeps it clean:

```js
function el(tag, cls, text, lang) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;   // never innerHTML
  if (lang) node.lang = lang;
  return node;
}
```

For any **external link** in the rendered content, gate on the protocol the same way
the hitlist feed does — only emit an anchor for `http(s)` URLs:

```js
if (q.link && q.link.url && /^https?:\/\//i.test(q.link.url)) {
  const a = document.createElement('a');
  a.href = q.link.url; a.textContent = q.link.label || 'Watch ↗';
  a.target = '_blank'; a.rel = 'noopener noreferrer';
  modalBody.appendChild(a);
}
```

This blocks `javascript:`/malformed URLs at the render layer; enforce it again in the
JSON schema test (`link.url` must match `^https?://`). A plain `<a href>` navigation
needs **no CSP change** — CSP governs fetch/embed/script origins, not user clicks.

### 4. Silent-fail is the contract — and it hides localhost differences

Each IIFE wraps its work in `try { … } catch (e) { console.warn(...); container.remove(); }`
and removes the section on empty data. Consequences:

- A **same-origin** JSON fetch (`/quotes.json`) renders fine on `localhost`.
- A **cross-origin** fetch (the hitlist's `thirstypig.com`) is CORS-locked to
  production and silently `.remove()`s on localhost — expected, not a bug.
- A graceful try/catch can hide *stacked* failures (wrong path + wrong shape + CSP).
  See `silent-fetch-failure-csp-graceful-fail-debugging.md` — when a client section
  "just disappears," temporarily log inside the catch.

## Optional extension: collection + poem cards (one box → expand module)

The quotes section added an expand-into-module variant on top of single-quote cards:

- An item with `title` + `entries[]` renders as **one card** whose modal lists many
  quotes (`<ol class="nb-quote-list">`). Used for "Bruce Lee", "Ed Catmull" boxes.
- `category: "poem"` renders `entries[]` as **stanzas** with `white-space: pre-line`
  (each entry is a multi-line string with `\n`) instead of a numbered list.
- A single shared `<dialog>` is reused for every card; `openModal(q)` rebuilds its
  body via `replaceChildren()` + `textContent`, giving ESC/`::backdrop`/focus-return
  for free. Set `max-height: 82vh; overflow-y: auto` so long collections scroll.

Schema that supported all cases: `{id, text, source}` required + optional
`original, lang, translation, note, category, title, entries, link`.

## Content discipline: verify attributions BEFORE publishing

For a quotes section specifically, attribution is the product. Run a verification
pass (web research) before shipping — popular quotes are routinely misattributed:

- "Art is never finished, only abandoned" → **Paul Valéry**, not da Vinci.
- "I choose a lazy person…" → **Gilbreth lineage**, not Bill Gates.
- Bruce Lee box: dropped "knowing is not enough" (**Goethe**), "love is a friendship
  caught on fire" (**Jeremy Taylor**), "key to immortality" (**1993 film Dragon**).

Keep a `source` on every item (use `"Source unknown"` rather than omitting), and put
provenance caveats in `note` ("commonly misattributed to…"). Enforce
"every-quote-has-a-source" in the schema test so an unsourced quote can't slip in.

## Verification checklist

- [ ] New `*.json` at repo root, valid, unique ids, `last_updated` ISO.
- [ ] `<section id="…-section">` + any `<dialog>` seeded in `now/index.html` (same commit).
- [ ] IIFE hardcodes the next section number; verified via DOM (`querySelector`).
- [ ] All nodes built with `textContent`; links gated on `^https?://`.
- [ ] CSS uses notebook tokens; checked light + dark headless.
- [ ] e2e test class added (schema + render target + dialog + JSON reference).
- [ ] No CSP change for same-origin fetch + plain anchor navigation.
- [ ] `python3 -m pytest tests/ -q` green.

## Related

- [Silent fetch failure + CSP graceful-fail debugging](silent-fetch-failure-csp-graceful-fail-debugging.md) — debugging the special case of one client fetch disappearing.
- [Cross-repo admin via GitHub Contents API](cross-repo-admin-via-github-contents-api.md) — the write side of the `bucketlist.json` client-render precedent.
- [Marker-boundary content staleness](marker-boundary-content-staleness.md) — the server-side bootstrap rule this mirrors on the client.
- [Relative-time HTML defeats content-changed cache](relative-time-html-defeats-content-changed-cache.md) — interaction if the section emits `<time data-rel>` strings.
- [CSP unsafe-inline removal via script externalization](../security-issues/csp-unsafe-inline-removal-via-script-externalization.md) — why /now JS lives in `now/now.js`, not inline.
