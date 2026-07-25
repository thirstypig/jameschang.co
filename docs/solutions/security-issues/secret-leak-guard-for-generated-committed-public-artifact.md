---
title: "Guarding a generated, committed, public artifact against secret leaks — an enumerated keyword denylist is one rename away from a hole"
slug: secret-leak-guard-for-generated-committed-public-artifact
category: security-issues
tags: [secret-scanning, denylist, public-repo, leak-prevention, regex, false-negative, false-positive, generated-artifact, reproducibility, table-driven-tests, mutation-testing, admin-docs-hub, defense-in-depth]
symptom: "A secret-value guard on a committed, public index.json passed CI while missing four of the repo's real secrets; after hardening it false-positived on its own JSON structure; and the artifact it protected could not even be rebuilt from its own committed sources."
root_cause: "Three linked mistakes when a build script (bin/build-docs-index.py) emits a committed, public admin/docs/index.json and a find_secret_values() guard is the leak gate: (1) the guard matched an ENUMERATED list of compound keywords (client_secret, api_key, refresh_token) so any real secret under a name the list didn't spell out — PLEX_TOKEN, WHOOP_TOKEN_KEY, GCAL_ICAL_URL, a ghp_ PAT — sailed through; (2) the first false-positive fix exempted any lowercase-hyphenated value, which also exempted diceware passphrases (a real AES key shape in this repo); (3) index.json embeds the rendered HTML of two under-the-hood docs that were regenerated but left uncommitted, so the committed artifact was not reproducible from its own tracked sources — the guard was checking a phantom."
module: "bin/build-docs-index.py (find_secret_values), admin/docs/index.json, tests/test_docs_index.py, bin/refresh-docs.py"
date_solved: 2026-07-24
severity: high
---

# Guarding a generated, committed, public artifact against secret leaks

## Symptom

The admin docs hub is served from `admin/docs/index.json` — a manifest generated
by `bin/build-docs-index.py` and **committed to a public GitHub repo**. A guard,
`find_secret_values()`, is the automated gate that fails CI if the committed
manifest ever contains a real secret value. Over one feature branch, three
separate failure modes surfaced from the same small surface:

1. **False negatives.** The guard passed on the committed index, yet a direct
   probe showed it *missed* leaks of the repo's actual secrets:
   `PLEX_TOKEN=…`, `TLDR_FETCH_TOKEN=ghp_…`, `WHOOP_TOKEN_KEY=…`,
   `GCAL_ICAL_URL=https://…/ical/…` — all returned `[]` (publishable).
2. **False positive on its own output.** After hardening, regenerating the index
   tripped the guard on `"key": "site-engineering"` — a JSON *field name* `key`
   sitting next to a value that happened to be exactly the 16-char threshold.
3. **A non-reproducible artifact.** The committed `index.json` embeds the rendered
   HTML of `admin/docs/under-the-hood/{pm-review,stats}.md`. Those were
   regenerated but left uncommitted, so rebuilding the index from tracked sources
   produced a *different* file — the guard was validating content that no commit
   could reproduce.

## Investigation — what didn't work, and why

**Round 1 (the tempting fix): add the missing keyword.** The guard's first form
enumerated compound keywords: `client_secret|private_key|api_key|secret_key|refresh_token|password`.
When `PLEX_TOKEN` was found missing, the obvious move is to add `token`. Then a
review found `*_KEY` also uncovered, so add `key`. Then `*_SECRET`
(`APP_SECRET`, `JWT_SECRET`) — add `secret`. **Three review rounds, each adding
one word.** Every round the guard looked "fixed" and every round the *next* real
secret name evaded it. An enumerated denylist in a security gate is a standing bet
that you've imagined every future variable name — and a `git grep` of this repo's
own `CLAUDE.md` listed secret names the list had never spelled out.

**First false-positive fix (too broad): exempt lowercase-hyphenated values.**
To stop `"key": "site-engineering"` from firing, the instinct was
`_SLUG_LIKE_VALUE = ^[a-z]+(?:[-_][a-z]+)+$` — "slugs aren't secrets." Tested
against the repo's real secrets, this exempted **five of six** of them
(`a1b2c3d4e5f6g7h8i9j0k1l2` is lowercase-alphanumeric; it matched). It would have
gutted the guard to silence one cosmetic false positive.

**Second false-positive fix (still too broad): exempt any slug value.** Narrowing
to a strict word-slug regex was better, but a **diceware passphrase** — e.g.
`WHOOP_TOKEN_KEY` set to a value like `correct-horse-battery-staple`, an actual
AES-key shape in this repo — is *also* a hyphen-joined lowercase word string, so it
stayed exempt. A value-shape exemption can't distinguish "section slug" from
"passphrase secret" because they look identical.

(Note: the code spans above deliberately separate the variable name from the
example value. Written as a single `NAME=value` assignment, this very doc would
trip the guard — its rendered HTML is indexed into the public `index.json`. See
the meta-check in Prevention.)

**On the artifact: "leave the drift out of the commit."** During the build the
two regenerated `under-the-hood` docs were repeatedly excluded from commits as
"unrelated drift." They are not unrelated — `index.json` *embeds their rendered
HTML*. Excluding them made every commit's `index.json` unbuildable from its own
tree.

## Root cause

Three facets of one situation: **a generated file is committed to a public repo,
and a regex guard is the last line before disclosure.**

1. **Enumerating what to catch inverts the safe default.** A denylist of specific
   secret *names* fails open: anything not on the list is published. The gate's
   whole job is to hold under *future* docs, where the names aren't known yet.

2. **An exemption applied at the wrong layer can't be safe.** "Is this value a
   slug or a secret?" is undecidable from the *value* alone — `site-engineering`
   and `correct-horse-battery-staple` are the same shape. The only reliable signal
   is the *keyword layer*: `"key": …` (a bare structural field name) is safe;
   `WHOOP_TOKEN_KEY = …` (a compound secret identifier) never is.

3. **A generated artifact that isn't reproducible from its commit is unverifiable.**
   If `index.json` embeds `pm-review.md`'s HTML but `pm-review.md` isn't committed,
   then "the guard passed on the committed index" is a statement about content that
   doesn't exist in the tree — a false sense of safety.

## Solution

### 1. Generalize the denylist to STEMS, and test the class, not instances

Stop enumerating compounds. Match a small set of bare **stems** with any
prefix/suffix, so every compound is subsumed without listing it:

```python
_SECRET_KEYWORD = (
    r"[a-z0-9_]*(?:secret|token|key|password|passphrase|credential)[a-z0-9_]*"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(" + _SECRET_KEYWORD + r")[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_\-./+]{16,})",
    re.IGNORECASE,
)
```

`PLEX_TOKEN`, `WHOOP_TOKEN_KEY`, `APP_SECRET`, `SIGNING_KEY`, `client_secret`,
`api_key` all match now — no enumeration. Add the shapes a name-based rule can't
express: GitHub PAT prefixes (self-identifying regardless of variable name) and
PEM headers (always a value):

```python
_GITHUB_PAT = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,})")
_PEM_HEADER = re.compile(r"-----BEGIN [A-Z ]*(PRIVATE KEY|CERTIFICATE)-----")
```

Then guard the **class** with a table-driven test so a future regression is a red
test, not a fourth review round:

```python
MUST_CATCH = ["APP_SECRET=<16+ chars>", "WHOOP_TOKEN_KEY=<diceware>",
              "PLEX_TOKEN=<opaque>", "SIGNING_KEY=<hex>", "<ghp_ PAT>", "<PEM header>", ...]
MUST_PASS  = ['"key": "site-engineering"', 'TOKEN_ENC = ".whoop-token.enc"',
              'TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"', ...]
```

### 2. Scope the false-positive exemption to the KEYWORD layer

The slug exemption only applies when the matched keyword is a **bare stem** (a
structural field name), never a compound secret identifier:

```python
_SLUG_LIKE_VALUE   = re.compile(r"^[a-z]+(?:[-_][a-z]+)+$")
_BARE_STEM_KEYWORD = re.compile(r"^(?:secret|token|key|password|passphrase|credential)$", re.IGNORECASE)

# inside find_secret_values(), on _SECRET_ASSIGNMENT matches only:
#   ...and not (_BARE_STEM_KEYWORD.match(m.group(1)) and _SLUG_LIKE_VALUE.match(m.group(2)))
```

So `"key": "site-engineering"` (bare `key` + slug) is exempt, while a compound
name like `WHOOP_TOKEN_KEY` assigned that same slug-shaped diceware value is caught
even though the value looks slug-like. A parallel `_FILENAME_LIKE_VALUE` exemption
(`.enc`/`.json`/`.md`/…) handles `TOKEN_ENC = ".whoop-token.enc"` — but is applied
**only** to assignment matches, never to `_SECRET_URL`, so a `.ics`-suffixed
calendar-URL secret is still caught.

**Declined a plausible widening with evidence.** A reviewer suggested adding bare
`_url` to `_SECRET_URL` so `PLEX_URL=https://…plex.direct…` is caught. Testing it
produced a false positive on `TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"`
— a public OAuth endpoint documented in another solution doc. `PLEX_URL` is logged
as an accepted known gap rather than encoded as intent.

### 3. Make the artifact reproducible, and prove it

`bin/refresh-docs.py` regenerates `pm-review.md`, `stats.md`, `costs.md`, the
README status block, **and** `index.json` at one timestamp. Commit *all* of them
together — never the generated index while excluding a source it embeds. Prove it
before committing:

```bash
cp admin/docs/index.json /tmp/committed.json
python3 bin/build-docs-index.py >/dev/null
python3 - <<'PY'
import json
a={d['path']:d for d in json.load(open('/tmp/committed.json'))['docs']}
b={d['path']:d for d in json.load(open('admin/docs/index.json'))['docs']}
print("REPRODUCIBLE" if a==b else "NOT REPRODUCIBLE")
PY
```

## Prevention

- **A leak gate must fail closed.** Prefer matching secret *shapes* (stems, PAT
  prefixes, PEM headers, high-entropy assigned values) over enumerating known
  *names*. Any name-list bets you enumerated the future; you didn't.
- **When a guard misses three times for the same structural reason, stop patching
  instances — fix the class.** Then add a table-driven `MUST_CATCH`/`MUST_PASS`
  test so the class is pinned. Enumerated lists in a security check are a smell.
- **Mutation-test the guard's own tests.** For each new `MUST_CATCH` row, delete
  the alternation branch it depends on and confirm the row goes red. A row that
  can't fail is decoration.
- **Exempt at the layer where the distinction is decidable.** If two categories
  are indistinguishable by value (slug vs passphrase), move the exemption to a
  layer where they differ (the field name). Never silence a false positive with a
  rule that also silences a true positive — test the exemption against real
  secrets before shipping it.
- **A committed generated artifact must be reproducible from its committed
  sources.** If `X.json` embeds `Y.md`'s output, `Y.md` is a build input; commit
  them together, and assert reproducibility in the pipeline. "The guard passed on
  the committed file" means nothing if the file can't be rebuilt.
- **Never `return` early past a guard on a missing input.** The guard test
  originally `return`ed if `index.json` was absent — a silent no-op on the most
  load-bearing check. Assert the file exists first; a missing artifact should fail
  loud.
- **Meta-check: docs that live inside the indexed tree get scanned too.** This
  very write-up sits in `docs/solutions/`, which the hub indexes — so its rendered
  HTML lands in the public `index.json`. Written naively, its example
  `NAME=value` secret shapes tripped its own guard (three real hits on the first
  draft). Vet any doc destined for the index against the guard before regenerating:
  `python3 -c "import importlib.util as u; m=u.module_from_spec(s:=u.spec_from_file_location('b','bin/build-docs-index.py')); s.loader.exec_module(m); print(m.find_secret_values(open('<doc>').read()))"`.
  Illustrate secret shapes by separating the name from the value, not as a live
  assignment.

## Related

- [[oauth2-refresh-token-rotation-encrypted-committed-file]] — the `.enc` pattern
  the guard's filename exemption references; the values themselves live encrypted,
  never in the index.
- [[feed-heartbeat-on-noop-path-hides-upstream-api-failure]] — same family of bug:
  a safety mechanism (heartbeat / guard) that reports "fine" on a path it can't
  actually vouch for. Both fixed by making the mechanism reflect real success.
- [[csp-unsafe-inline-removal-via-script-externalization]] — the other
  security-issues doc; both are about a public static site's disclosure surface.
- `docs/superpowers/specs/2026-07-24-site-engineering-docs-in-hub-design.md`
  (gitignored, local) — the feature that surfaced these traps; `admin/docs/` is
  public-safe content only.
