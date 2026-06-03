# /now Quotes Section — Design Spec

**Date:** 2026-06-02
**Status:** Approved (brainstorming → build)

## Summary

A new client-rendered section on `/now` that displays a curated collection of
external quotes as a grid of equal-size notebook cards. Clicking a card opens a
native `<dialog>` modal with the full quote, original-language text + translation
(for bilingual entries), source attribution, and a provenance note where relevant.

Data lives in a root `quotes.json` (`{ "items": [...] }`), rendered client-side by
`now/now.js` — the same pattern as the hitlist and bucket-list teasers. Array order
is display order.

## Placement & numbering

- New `<section id="quotes-section">` appended after `#bucketlist-section` in
  `now/index.html`.
- Client-rendered sections set their own number in JS: hitlist = `/10`,
  bucketlist = `/11`, so **quotes = `/12`**.
- Section title: `quotes` (lowercase, matching the notebook convention).
- Silent-fail: the IIFE `.remove()`s its section on fetch error or empty data
  (invisible on localhost / bad fetch), like the other client feeds.

## Data model — `quotes.json`

```json
{
  "items": [
    {
      "id": "art-never-finished",
      "text": "Art is never finished, only abandoned.",
      "original": "",
      "lang": "",
      "translation": "",
      "source": "Paul Valéry",
      "note": "Commonly misattributed to Leonardo da Vinci; from his 1933 essay on Le Cimetière marin.",
      "category": "literature"
    }
  ]
}
```

| Field | Required | Purpose |
|-------|----------|---------|
| `id` | yes | unique kebab-case slug |
| `text` | yes* | primary English quote (\*one of `text`/`original` required) |
| `original` | no | original-language source text (CJK / Latin / French) |
| `lang` | no | label for `original` (`zh` / `la` / `fr`) |
| `translation` | no | English gloss when `original` is the headline |
| `source` | no | attribution: person and/or work |
| `note` | no | provenance / commentary (e.g. "misattributed to…") |
| `category` | no | `idiom` / `film` / `literature` / `proverb` / `philosophy` / `latin` |

Renderer emits a DOM node only when a field is present. All text inserted via
`textContent` — never `innerHTML` — so CJK/Latin/quote characters and any stray
markup are inert (XSS-safe, matching the existing feeds).

## Card (collapsed) vs modal (expanded)

- **Card** = a `<button>` (keyboard-accessible) with the headline (CJK `original`
  if present, else `text`), line-clamped to ~3 lines, plus a small `source` line
  and a `+` expand affordance. Fixed `min-height` + `-webkit-line-clamp` keeps
  cards uniform across very short (4-char idiom) and long (Pascal) quotes.
- **Modal** = a single shared native `<dialog id="quote-modal">`, populated on
  click via `textContent`. Shows full `original` + `translation` + `text` +
  `source` + `note`. Closes on ESC, `::backdrop` click, and a close button;
  focus returns to the triggering card.

## Content (16 external quotes, attributions verified 2026-06-02)

Corrections applied from verification:
- #3 "Art is never finished, only abandoned" → **Paul Valéry** (not da Vinci).
- #9 → **Pres. Nemerov, *The Sum of All Fears* (2002)**, wording "These days…".
- #12 → **Elizabeth McCord, *Madam Secretary*** ("Madam", + "You must speak up").
- #16 "lazy person" → **Frank Gilbreth lineage** (not Bill Gates).
- #13 "go fast / go far" → African proverb, **origin uncertain** (note).
- #15 "greatest insult… indifference" → **source unknown** (no false attribution).
- #4 Veritas inlustrat → Latin maxim (no unverified institutional motto claim).
- #8 → Arabic proverb. #5 → Rikki Rogers (convention).

The personal-voice lines from the raw input ("I want to work for you but not as a
beggar…", "It's about being valued", etc.) are **excluded** — section is external
quotes only.

## Implementation obligations

1. `quotes.json` at repo root.
2. `<section id="quotes-section">` + `<dialog id="quote-modal">` placeholder in
   `now/index.html` (same commit as the JS).
3. New IIFE in `now/now.js` (fetch, render grid, wire modal). Hardcode `/12`.
4. CSS for `.nb-quote-grid`, `.nb-quote-card`, `.nb-quote-modal` in the
   appropriate stylesheet (notebook tokens).
5. Tests: `quotes.json` schema (unique ids, required fields) + e2e (render target
   + dialog present + now.js references `/quotes.json`).

No CSP change (same-origin fetch). No sitemap change (`/now` is already listed).
No print-stylesheet change (client-rendered, not on the homepage résumé).
