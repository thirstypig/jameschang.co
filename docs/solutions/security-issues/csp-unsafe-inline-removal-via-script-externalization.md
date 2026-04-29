---
title: "Removing CSP `'unsafe-inline'` from script-src on a static GitHub Pages site"
category: security-issues
tags: [csp, content-security-policy, ga4, googletagmanager, inline-scripts, github-pages, defense-in-depth, static-site]
symptom: "CSP `script-src 'unsafe-inline'` left the door open to arbitrary inline JS execution despite no live exploit; defense-in-depth was nominal"
root_cause: "Inline `<script>` blocks for GA4 init and a couple of `/now`-specific IIFEs (hitlist fetch + live-relative time upgrader) were originally written inline because (a) GA4's docs show inline init, and (b) externalization meant adding `<script src=…>` tags + tightening CSP across 16 duplicated HTML files with no templating layer. The friction was structural, not technical."
module: site-wide-csp
date_solved: 2026-04-28
severity: medium
---

# Removing CSP `'unsafe-inline'` from `script-src` on a static GitHub Pages site

## The Problem

`jameschang.co` is a static HTML/CSS/JS portfolio on GitHub Pages with 18 HTML pages (16 standard + 2 OAuth callbacks). All 16 standard pages had a Content-Security-Policy meta tag of the form:

```
default-src 'self';
script-src 'self' 'unsafe-inline' https://www.googletagmanager.com;
style-src 'self' 'unsafe-inline';
img-src 'self' data: https://www.google-analytics.com https://www.googletagmanager.com;
…
```

The `script-src 'unsafe-inline'` clause meant *any* inline `<script>` block in the page source — including, hypothetically, ones injected via a successful XSS — would execute. Combined with `connect-src` allowing `*.google-analytics.com` and `*.analytics.google.com`, an attacker who could land arbitrary HTML on the page could exfiltrate to those hosts. The img-src `googletagmanager.com` widening (added 2026-04-28 to fix silently-blocked GA4 measurement pixels — see *related docs*) gave them another exfiltration channel.

No live exploit existed. The site has no auth, no user input, no database. But the CSP's defense-in-depth posture was nominal: any successful HTML injection would have full inline-script execution.

A multi-agent code review (`/ce:review`) flagged this as a P3 hardening opportunity. This doc captures the migration pattern.

## Why the inline scripts existed

Three categories of inline `<script>` content existed across the 16 standard pages:

1. **GA4 init** (present on all 16, byte-identical, ~131 chars):
   ```html
   <script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag('js',new Date());gtag('config','G-B3HW5VBDB3')</script>
   ```
   Inline because Google's gtag.js setup docs (https://developers.google.com/analytics/devguides/collection/ga4) show inline init as the default.

2. **Page-specific IIFEs on `/now`** (2 blocks, ~3.6KB and ~970 chars):
   - Thirsty Pig hitlist fetch (CORS-locked to jameschang.co; silent-fail on fetch error)
   - Live-relative time upgrader (rewrites `<time data-rel>` elements every 60s)

3. **JSON-LD structured-data blocks** (`<script type="application/ld+json">…</script>`):
   - These look like inline scripts but **CSP `script-src` does not apply to `application/ld+json`** because browsers don't execute them. They are data, not code. No CSP change needed for these.

The OAuth callback pages (`/whoop/callback/`, `/spotify/callback/`) have a tighter `default-src 'none'` CSP with their own inline OAuth-code-display logic. They're out of scope for this fix — they're utility pages used once per OAuth flow and refactoring them would mean adding `'self'` to their `script-src` (loosening their `default-src 'none'` posture) for marginal real-world benefit.

## Root cause

Inline scripts existed because the friction to externalize was *structural*, not technical:

- 16 HTML pages with no templating layer — every change to `<head>` had to be replicated 16 times.
- The GA4 init was inherited verbatim from Google's docs.
- The two `/now`-specific scripts were "obvious-where-they-go" inline — they refer to DOM elements on that one page, so externalizing them meant making them path-aware or using `defer` to ensure DOM-ready timing.

None of these were hard problems. They were just *small piles of tedium that prevented a nice-to-have hardening from getting done.* A scoped pass with a small Python script flattened all of it.

## Working solution

### Step 1 — Inventory inline scripts

Audit which pages have inline blocks and what they contain:

```bash
for f in $(find . -maxdepth 4 -name "*.html" | grep -v ".git\|callback\|.playwright"); do
  count=$(python3 -c "
import re
with open('$f') as fh: s = fh.read()
matches = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', s, re.DOTALL)
print(len(matches))
")
  [ "$count" != "0" ] && echo "$f: $count"
done
```

Categorize each block as: GA4 init / page-specific JS / JSON-LD (skip). For the hashing-vs-externalization decision, **prefer externalization** — externalized scripts are cacheable, easier to audit, and don't bloat the HTML. Hashes are a fallback when externalization isn't feasible (e.g., third-party widgets that require inline init).

### Step 2 — Externalize the universal GA4 init

```bash
mkdir -p assets/js
cat > assets/js/gtag-init.js <<'JSEOF'
// GA4 init — externalized from inline to allow CSP `script-src 'self'` without 'unsafe-inline'.
// Loaded as `<script src="/assets/js/gtag-init.js"></script>` on all 16 standard pages.
window.dataLayer = window.dataLayer || [];
function gtag() { dataLayer.push(arguments); }
gtag('js', new Date());
gtag('config', 'G-B3HW5VBDB3');
JSEOF
```

Note GA4's `gtag.js` script (`<script async src="https://www.googletagmanager.com/gtag/js?id=…"></script>`) **must remain** — it's the GA4 library itself. The CSP already allows `https://www.googletagmanager.com` in `script-src`, so this works without `'unsafe-inline'`.

### Step 3 — Externalize page-specific IIFEs

For `/now`, combine the two IIFEs into `now/now.js`:

```javascript
// now/now.js — externalized from inline so the page CSP can drop 'unsafe-inline'.
// Two IIFEs: hitlist fetch + live-relative time upgrader.

(async function () {
  const container = document.getElementById('hitlist-section');
  if (!container) return;
  // … hitlist fetch logic …
})();

(function () {
  function fmt(ms) { /* … */ }
  // … relative-time upgrader …
})();
```

Both IIFEs already self-bootstrap via `getElementById` — they exit early if the target isn't on the page, so the file is safe to load on any page that imports it.

### Step 4 — Bulk-replace across all standard pages

Python script for the 16-file find-replace (one pass, atomic):

```python
import re
from pathlib import Path

ROOT = Path('.')
GTAG_INLINE_RE = re.compile(
    r"<script>window\.dataLayer=window\.dataLayer\|\|\[\];function gtag\(\)\{dataLayer\.push\(arguments\)\}"
    r"gtag\('js',new Date\(\)\);gtag\('config','G-B3HW5VBDB3'\)</script>"
)
GTAG_REPLACEMENT = '<script src="/assets/js/gtag-init.js"></script>'

CSP_OLD = "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com;"
CSP_NEW = "script-src 'self' https://www.googletagmanager.com;"

for f in ROOT.rglob('*.html'):
    rel = str(f.relative_to(ROOT))
    if any(skip in rel for skip in ['.git/', 'callback/', 'node_modules/', '.playwright-mcp/']):
        continue
    text = f.read_text()
    new = GTAG_INLINE_RE.sub(GTAG_REPLACEMENT, text)
    new = new.replace(CSP_OLD, CSP_NEW)
    if new != text:
        f.write_text(new)
```

For `/now` specifically, also drop the two IIFE inline blocks and add `<script src="/now/now.js" defer></script>` before `</body>`.

### Step 5 — Verify

1. **HTTP-level smoke test**: `curl -sI http://localhost:8787/assets/js/gtag-init.js` → 200 OK.
2. **Browser-level CSP check**: load each affected page in headless Chrome via Playwright; assert `console.errors.length === 0` (or only the documented localhost-only CORS errors).
3. **E2E test addition** — pin the new CSP so it can't drift back. See *Prevention* below.

## Prevention strategies

### Test 1: assert `'unsafe-inline'` is not in script-src on standard pages

Already added in this session as `TestStructuralParity::test_csp_homogeneous_across_15_pages` (which asserts byte-equality of CSP across the 15 non-`/now` pages). To make the *specific* `'unsafe-inline'` removal a sticky invariant, extend the test:

```python
def test_no_unsafe_inline_in_script_src_on_standard_pages(self):
    """Standard pages externalize all inline JS so script-src can drop
    'unsafe-inline'. Callback pages are intentionally exempt — they have
    a stricter default-src 'none' CSP with their own inline OAuth logic."""
    failures = []
    for f in self.HOMOGENEOUS_CSP_PAGES:  # 15 non-/now pages
        _, body = fetch(f)
        m = re.search(r'script-src ([^;]+);', body)
        if m and "'unsafe-inline'" in m.group(1):
            failures.append(f)
    assert not failures, "'unsafe-inline' reappeared in script-src:\n" + "\n".join(failures)
```

### Test 2: assert no inline `<script>` blocks (other than JSON-LD) on standard pages

Catches the *cause* of the regression rather than just the symptom:

```python
def test_no_executable_inline_scripts_on_standard_pages(self):
    failures = []
    for f in STANDARD_PAGES:
        _, body = fetch(f)
        # Find <script> tags WITHOUT src= AND WITHOUT type="application/ld+json"
        bare = re.findall(
            r'<script(?![^>]*\bsrc=)(?![^>]*type="application/ld\+json")[^>]*>',
            body,
        )
        if bare:
            failures.append(f"{f}: {len(bare)} inline executable script(s)")
    assert not failures, "Inline JS reappeared:\n" + "\n".join(failures)
```

### Guideline: when adding new client-side JS

Document in `CLAUDE.md`:

> **No new inline `<script>` blocks on standard pages.** Externalize to `assets/js/` (site-wide) or `<page>/<page>.js` (page-specific). The CSP forbids `'unsafe-inline'` for `script-src` on the 16 standard pages and the e2e suite enforces this. JSON-LD `<script type="application/ld+json">` is fine — CSP doesn't apply to non-executable scripts.

### Why callback pages are intentionally exempt

`/whoop/callback/` and `/spotify/callback/` have `default-src 'none'` (stricter than the standard `default-src 'self'`) plus their own per-callback inline OAuth-code-display logic. Externalizing would require:

- Loosening `default-src 'none'` → adding `'self'` to script-src.
- Per-callback `.js` files (the OAuth code-display logic varies by callback).

For utility pages used once per OAuth flow with no real-world XSS surface, this is more invasive than the marginal hardening warrants. The exemption is documented inline in each callback page's CSP rationale.

## Investigation steps that didn't apply

- **Subresource Integrity (SRI)**: SRI hashes the *bundled* `<script src=…>` content, useful for CDN-delivered scripts. Not relevant for `'self'`-served files where the path itself is the trust boundary.

- **Nonce-based CSP** (`script-src 'self' 'nonce-…';`): would let inline scripts stay inline by stamping each block with a server-generated nonce. Requires HTTP response headers to deliver the nonce per-request, which **GitHub Pages does not support** (CSP is meta-tag-only there; nonces would have to be statically embedded, defeating their purpose).

- **`script-src 'sha256-…';`** (hash-based CSP): the static-site equivalent of nonces. Each unique inline block's sha256 hash gets added to the directive. Works on GitHub Pages (meta-tag CSP supports hash sources) but creates a maintenance burden — every inline script edit means recomputing the hash and updating the CSP across 16 files. Externalization is cleaner for this use case.

## Related docs

- **`docs/solutions/integration-issues/silent-fetch-failure-csp-graceful-fail-debugging.md`** (2026-04-16) — same project, prior CSP issue: `connect-src` was missing `thirstypig.com` and the failure was silently swallowed by a graceful-fail `try/catch`. The debugging technique there (`chrome --headless --enable-logging=stderr` and grep `csp|cors|blocked|refused`) applies to this work too — the GA4 `img-src` widening that immediately preceded this hardening was found via that exact pattern.

- **`todos/006-complete-p2-add-content-security-policy.md`** (initial CSP injection across 12 pages, defining the `default-src 'self'` baseline)
- **`todos/072-complete-p3-csp-hardening.md`** (defense-in-depth: added `object-src 'none'` site-wide)
- **`todos/082-complete-p2-csp-byte-equality-e2e-test.md`** (the e2e parity test that locks current CSP)
- **`todos/086-complete-p3-unsafe-inline-replace-with-hashes.md`** (the todo this work resolves)

## Lessons

1. **Prefer externalization over hashes for static sites.** Hashes work but every inline-script edit triggers a CSP recomputation. Externalization is cleaner and gives you HTTP-level caching for free.

2. **Don't migrate utility/callback pages just for CSP parity.** Their attack surface is fundamentally different (used once per OAuth, not public-facing). Document the exemption and move on.

3. **JSON-LD `<script>` blocks are not subject to `script-src`.** `application/ld+json` is data, not executable. Don't conflate them when auditing inline content.

4. **Add an e2e regression test the same day.** With 16 duplicated HTML files and no templating layer, *anything not enforced by a test will drift on the next edit.* The session also added `TestStructuralParity::test_csp_homogeneous_across_15_pages` and would benefit from the two additional asserts in *Prevention* above.

5. **The friction to externalize was 100% tedium, not engineering.** A 30-line Python script + `mkdir -p assets/js` + `cat > assets/js/gtag-init.js` was the entire fix. When a hardening keeps not getting done, ask whether the obstacle is structural — and if it is, write the small script.
