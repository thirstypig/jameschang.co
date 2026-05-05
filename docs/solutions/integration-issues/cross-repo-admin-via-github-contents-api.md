---
category: integration-issues
title: Cross-repo admin via GitHub Contents API on plain GitHub Pages
problem_type: architecture-pattern
components:
  - bucketlist.json
  - bucketlist/index.html
  - bucketlist/bucketlist.js
  - now/now.js
  - docs/bucketlist-admin-spec.md
symptoms:
  - Want a non-developer-friendly admin for a small editable list on a static GitHub Pages site
  - Admin UI must live on a different static site (thirstypig.com/admin) than the data it manages (jameschang.co)
  - Plain HTML / Python-only tooling rule rules out Node-based CMSes (TinaCMS, etc.)
  - GitHub Pages can't host the OAuth gateway that git-based CMSes (Decap / Netlify CMS) need
root_cause: >
  Conventional CMSes assume the data, the renderer, and the admin all share infrastructure
  (one Node app, one OAuth provider, one origin). On a plain GitHub Pages site there is no
  shared infra to lean on — you have static asset hosting and that's it. The instinct to
  reach for TinaCMS / Decap fights the constraint instead of using it.
fix_summary: >
  Treat the GitHub Contents API itself as the backend. Store the editable data as a JSON
  file in the public repo. Let the existing admin on the sibling site (which already had a
  GitHub PAT + Contents API plumbing for its own hitlist) read and write the file via API.
  Render the public surfaces with client-side fetch of the same-origin JSON. No build step,
  no OAuth gateway, no SaaS, no new deployment target — and one fine-grained PAT covers
  multiple repos.
tags:
  - github-pages
  - github-contents-api
  - cms-alternative
  - cross-repo
  - static-site
  - admin-pattern
related:
  - docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md
date_solved: 2026-05-04
---

## The constraint

`jameschang.co` is plain static HTML on GitHub Pages. Per `CLAUDE.md`:

- No build step, no `package.json`, no framework.
- Python 3 is the only tooling dependency.
- Everything renders directly from files in the repo.

The ask was a "bucket list" feature: editable list of items, drag-reorder by priority, mark items done, all maintained from a phone-friendly admin UI. A second constraint emerged: the admin UI should live on `thirstypig.com/admin/` (which already manages a hitlist for that site), not on `jameschang.co` itself.

## What didn't fit

| Option | Rejection |
|--------|-----------|
| **TinaCMS** | Requires Node + a build step + TinaCloud (paid SaaS) or a self-hosted Tina backend. Violates the plain-static rule on multiple axes. |
| **Decap CMS** (formerly Netlify CMS) | No build step needed, but the GitHub OAuth flow needs a gateway — Netlify Identity, a self-hosted proxy, or git-gateway. GitHub Pages can't host the gateway, so this just moves the infrastructure problem somewhere else. |
| **Custom serverless function** | Pulls in a Vercel/Netlify/Workers deploy target alongside Pages. Same drift; one more thing to operate. |
| **Sync script + GitHub Action** | Works for read-mostly external feeds (WHOOP / Spotify pattern), but the admin needs interactive write — a cron isn't a UI. |

## The pattern that fit

```
┌──────────────────────────────┐         ┌────────────────────────────┐
│  thirstypig.com/admin/       │         │  jameschang.co (Pages)     │
│  (static page on Pages)      │         │                            │
│                              │  PUT    │  /bucketlist.json          │
│  - PAT in localStorage       │ ──────► │  /bucketlist/  (renderer)  │
│  - GitHub Contents API       │ via API │  /now/  (top-5 teaser)     │
│  - Drag-reorder + edit UI    │         │                            │
└──────────────────────────────┘         └────────────────────────────┘
              │                                      ▲
              │              GitHub                  │
              └─────────────► Contents API ──────────┘
                              (PUT writes to repo,
                               Pages auto-redeploys ~60s)
```

**Three pieces, no servers:**

1. **Data as a committed file.** `bucketlist.json` at the repo root. Order in `items[]` IS the priority order — drag-reorder = rewrite the array. Schema documented in `docs/bucketlist-admin-spec.md`.
2. **The admin is just a GitHub API client.** It reads with `GET /repos/:owner/:repo/contents/bucketlist.json` (carries `sha`), edits in memory, writes with `PUT` (carries the same `sha` + base64 content + commit message). A fine-grained PAT scoped `Contents: Read/Write` on both repos is the only credential.
3. **Public render is client-side fetch of a same-origin JSON.** `/bucketlist/bucketlist.js` and `/now/now.js` both `fetch('/bucketlist.json')` — no CORS, no API key on the public side. CSP `connect-src 'self'` covers it without a token.

**Why this works on plain GitHub Pages:**

- Pages doesn't need to know anything — it serves a static JSON file.
- The GitHub Contents API is already a "backend that accepts authenticated PUTs" — you don't have to host one.
- Pages auto-redeploys within ~60s of the push, so admin saves are live almost immediately.
- The fine-grained PAT lets one admin app manage data across N repos for the cost of one credential.

## What the consumer-side test suite locks down

The contract is enforced from the data side, even though writes happen from a different repo. `tests/test_site_e2e.py::TestBucketList` (9 tests) validates:

- `bucketlist.json` parses and has `items` + `last_updated`.
- Every item has `id`, `title`, `note`, `status`, `completed_date`. `status` is `todo` or `done`. Todos don't have a stray `completed_date`. Titles aren't empty.
- Item IDs are unique (admin uses them to target rows for edit/delete — duplicate IDs would let the admin update the wrong row).
- `/now` has the `<section id="bucketlist-section">` render target.
- `now/now.js` links to `/bucketlist/` (the only path in is the teaser; no top-nav link by design).
- No top-nav across any page links to `/bucketlist/` — preserves the "discovery only via /now" choice.
- The renderer script and page resolve (no 404).

This means the admin can ship freely; if it writes a malformed file, CI fails on this side and the bad write doesn't silently corrupt the public surface.

## When to reach for this pattern again

Use it when **all** of the following are true:

- The data is small (a list of ≤ N hundred items, JSON-serializable, edits are infrequent).
- The site is plain static (GitHub Pages, S3, any CDN-of-static-files).
- You either (a) already have an admin app somewhere that has GitHub API access, or (b) you're willing to build a single-purpose static admin page that stores a PAT in `localStorage`.
- Edits are by a single trusted user (or a small known set). The "auth" is the PAT itself; there's no per-user authorization layer.

Reach for something else when:

- You need multi-user auth with roles (use a real CMS).
- Edits are high-volume or latency-sensitive (~60s Pages redeploy is the floor).
- The data is large or relational (use a database).

## Prevention / future-proofing

- **Document the schema as a contract**, not just a hint. `docs/bucketlist-admin-spec.md` lists the keys, valid values, and the "every save must update `last_updated`" rule. The admin is a separate codebase — without a written contract, drift is inevitable.
- **Test the schema on the renderer side.** Validates the contract from where the data is consumed, not where it's written.
- **Order in the array IS priority.** Resist adding a separate `priority` field — two sources of truth means they will eventually disagree.
- **Same-origin fetch only.** Putting the JSON in a different repo than the renderer would force CORS handling and is rarely worth it.
- **No top-nav link if discovery should be intentional.** A test enforces this so a future "let me just add a link" PR doesn't quietly violate the design choice.

## Cross-references

- `docs/bucketlist-admin-spec.md` — the contract the admin reads from.
- `docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md` — adjacent pattern: managing API auth on a static site without a backend (encrypted token committed to the repo, decrypted at runtime in CI).
- thirstypig.com hitlist (`thirstypig.com/places-hitlist.json` + `thirstypig.com/admin/`) — predecessor pattern, single-repo. The bucket list generalizes it to cross-repo.
