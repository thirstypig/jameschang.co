---
title: "Silent graceful-fail hid stacked CSP, URL, and JSON shape bugs in /now hitlist fetch"
category: integration-issues
tags: [csp, fetch, graceful-fail, cross-origin, static-site, debugging]
symptom: "section doesn't appear on page"
root_cause: "Three stacked bugs (CSP connect-src missing thirstypig.com, wrong fetch path /places-wishlist.json vs /places-hitlist.json, wrong JSON shape data.toVisit vs data.items) all masked by a try/catch that silently removed the container on any failure"
module: now-page-hitlist-fetch
date_solved: 2026-04-16
severity: medium
---

# Silent fetch failure — debugging stacked configuration bugs behind a graceful-fail

## The Problem

The `/now` page on a static site includes a dynamically-rendered "places to visit" section populated by a client-side script that fetches a JSON feed from a cross-origin endpoint.

**Symptom:** The user reported *"I don't see the section."* Nothing else. No red console errors visible at a glance, no network panel alarms, no visible failure — the `<section>` was simply absent from the rendered page as if it had never been coded.

- The container element was present in the static HTML source (verified via View Source).
- The `<script>` tag was present.
- The deployment had succeeded.
- Yet the `<section>` did not appear in the live DOM.

This is the worst class of bug: **silent, symptomless, and invisible to casual inspection.**

## Investigation Steps

1. **Confirm the script ran at all.** Dumped the post-JavaScript DOM using headless Chrome:
   ```
   chrome --headless --disable-gpu --dump-dom https://jameschang.co/now/
   ```
   The `<section id="hitlist-section">` was missing from the rendered DOM but present in the static HTML — confirming the script had executed and had reached the `container.remove()` graceful-fail branch.

2. **Unmask the silent failure.** Re-ran Chrome with verbose logging to stderr:
   ```
   chrome --headless --disable-gpu \
     --enable-logging=stderr --v=1 \
     --dump-dom https://jameschang.co/now/ 2> chrome.log
   ```
   Grepped for security-layer keywords:
   ```
   grep -iE 'csp|blocked|refused|cors' chrome.log
   ```
   Found: `Access to fetch at 'https://thirstypig.com/places-wishlist.json' from origin 'https://jameschang.co' has been blocked by CORS policy...`

3. **Fix CSP, re-dump DOM.** Added `https://thirstypig.com` to `connect-src` in the `<meta http-equiv="Content-Security-Policy">` tag. Re-ran the DOM dump. Section was **still** removed.

4. **Check the endpoint directly.**
   ```
   curl -sI https://thirstypig.com/places-wishlist.json
   # HTTP/2 404
   ```
   The URL itself was wrong.

5. **Find the correct endpoint.** Tried several plausible alternates (`/hitlist.json`, `/wishlist/`, `/places.json`) — all 404. Searched the upstream Astro source tree at `~/projects/thirstypig/src/pages/` and found `places-hitlist.json.ts` — the actual generator route.

6. **Fix URL, re-dump DOM.** Section was **still** removed.

7. **Inspect the JSON shape.**
   ```
   curl -s https://thirstypig.com/places-hitlist.json | python3 -m json.tool
   ```
   Top-level key was `items`, not `toVisit`. The script's `data.toVisit || []` was silently defaulting to `[]`, hitting the "no items" branch, and calling `container.remove()`.

8. **Fix shape, re-dump DOM.** Section finally rendered with the expected 5 restaurants.

## Root Cause

The surface bugs were three stacked misconfigurations:
- CSP `connect-src` didn't include the new origin.
- The URL path referenced a deprecated prototype name (`/places-wishlist.json` vs the actual `/places-hitlist.json`).
- The JSON response shape had been refactored from `toVisit` to `items`.

The **meta-problem** — the reason a single bad character wasn't a five-minute fix — was a `try { fetchAndRender() } catch { container.remove() }` pattern wrapping the entire pipeline. Every one of the three failures threw, was caught, and was silently hidden by removing the container.

**Why this pattern is correct in production.** A static personal site shouldn't show a broken half-section or a raw error message to a stranger who stumbled in from Google. Graceful degradation — "if the data isn't available, just don't render this block" — is the right user-facing behavior. Progressive enhancement orthodoxy is sound.

**Why this pattern is hostile to debugging.** The catch block discards the one piece of information the developer needs — *which* failure mode occurred. After the first fix, the section was still missing, so the developer naturally assumes the CSP fix didn't take. The symptom is identical across all three bugs. Without external instrumentation, you cannot distinguish "CSP blocked" from "404" from "shape mismatch" from "network offline." Each fix looks like it didn't work.

The lesson: `catch { hide() }` should log the caught error to `console.warn` (or a structured telemetry sink) *before* hiding. The end user never sees the warning; the developer always does. Silent catches are a dev-experience footgun regardless of how graceful the UX is.

## Solution

### Bug 1 — CSP meta tag

```html
<meta http-equiv="Content-Security-Policy" content="
  ...
  connect-src 'self'
    https://thirstypig.com
    https://www.google-analytics.com
    https://*.analytics.google.com
    https://*.googletagmanager.com;
  ...
">
```

### Bug 2 — fetch URL

```js
// before
const res = await fetch('https://thirstypig.com/places-wishlist.json');
// after
const res = await fetch('https://thirstypig.com/places-hitlist.json');
```

### Bug 3 — JSON shape

```js
// before
const items = (data.toVisit || []).slice(0, 5);
// after
const items = (data.items || []).slice(0, 5);
```

### Recommended catch block going forward

Add a `console.warn` and a DEBUG escape hatch keyed on hostname so localhost surfaces the error and production stays silent:

```js
(async () => {
  const container = document.getElementById('hitlist-section');
  if (!container) return;
  try {
    const res = await fetch('https://thirstypig.com/places-hitlist.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!Array.isArray(data.items)) throw new Error('shape: expected data.items[]');
    const items = data.items.slice(0, 5);
    if (!items.length) throw new Error('empty items');
    render(items);
  } catch (err) {
    console.warn('[hitlist] hidden:', err);
    if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
      const note = document.createElement('pre');
      note.style.color = '#c00';
      note.textContent = `hitlist error: ${err.message}`;
      container.appendChild(note);
    } else {
      container.remove();
    }
  }
})();
```

The `console.warn` costs nothing in production and is the single breadcrumb that saves the next debugging session. The hostname-based DEBUG branch turns localhost into a loud failure mode without any build flag or env var.

## The Debugging Technique

**Unmasking a silent fetch failure when the page's own console is swallowed by design:**

1. **Dump the post-JS DOM** to confirm the script ran and reached a failure branch:
   ```
   chrome --headless --disable-gpu --dump-dom <URL>
   ```
   If the container is present in View Source but absent from the dumped DOM, a catch-and-hide path ran.

2. **Enable verbose browser logging** — the critical step most developers don't know:
   ```
   chrome --headless --disable-gpu \
     --enable-logging=stderr --v=1 \
     --dump-dom <URL> 2> chrome.log
   ```
   Chrome's internal security-layer messages (CSP refusals, CORS blocks, mixed-content warnings) are written even when JavaScript catches the resulting exception. They appear in stderr regardless of whether any `console.error` ran.

3. **Grep for the canonical keywords:**
   ```
   grep -iE 'csp|cors|blocked|refused|mixed content|net::' chrome.log
   ```
   These terms cover nearly every silent-fetch-failure class.

4. **After each fix, re-dump the DOM.** Don't trust a fix because *something* changed — verify the section actually reappears. Stacked bugs produce identical symptoms; only the logs differentiate them.

5. **Test the endpoint independently of the browser.** `curl -sI <URL>` for status, `curl -s <URL> | python3 -m json.tool` for shape. Bypassing the browser eliminates CSP / CORS / cache as variables and tells you whether the server and payload are themselves correct.

General principle: when in-page instrumentation is swallowed by design, move instrumentation **out of the page** — to the browser process's own stderr, and to direct transport-layer tools like `curl`.

## Prevention Strategies

Run this checklist *before* writing the fetch call:

- **CSP allow-list audit.** Open the deployed `<meta http-equiv="Content-Security-Policy">` tag and confirm `connect-src` includes the exact origin you're about to hit — scheme, host, and port. Remember `connect-src` falls back to `default-src`, so with `default-src 'self'` tightened, new origins must be added explicitly. Do this first — CSP violations only surface in the console and are invisible to your `catch` block.
- **Pin the URL and shape as a fixture.** Before writing client code, `curl` the endpoint and save the response to `fixtures/hitlist.json` (or paste it into a comment). Write the renderer against the fixture first, then swap in the live fetch. This catches "wrong URL path" and "wrong JSON shape" before they stack with CSP bugs.
- **Log in the catch block.** The graceful-fail pattern should never be `catch {}` alone. Minimum viable catch is `console.warn` with the error and a feature prefix.
- **Document the contract.** A three-line comment above the fetch stating the expected URL, expected top-level key, and expected item shape is cheap insurance.

## When Silent Graceful-Fail Is The Right Choice

- Third-party APIs with real downtime risk (GitHub API, weather, analytics embeds).
- Nice-to-have content (blogroll, "now reading," CMS feeds) where the page's purpose survives without it.
- Reputational concerns — you don't want readers to see "our dependency is broken."

## When It's The Wrong Choice

- Active development — use a DEBUG branch (hostname check) that renders the error.
- Load-bearing content — render a static fallback or an explicit "temporarily unavailable" message, not nothing.
- Endpoints you don't control — log to an error tracker (Sentry, a pixel endpoint, `navigator.sendBeacon` to your own logger) so you learn about outages independent of user reports.

## Related

### Existing solution docs (topically adjacent)
- [`oauth2-refresh-token-rotation-encrypted-committed-file.md`](./oauth2-refresh-token-rotation-encrypted-committed-file.md) — WHOOP OAuth2 sync on the same static GitHub Pages site. Same "stacked-bug, multi-layer silent-fail" class (Cloudflare UA filtering, wrong token endpoint auth method, wrong API version path). Closest prior art.

### Related todos
- `todos/006-complete-p2-add-content-security-policy.md` — defines the site's strict meta CSP that directly constrained this fetch.

### External references
- [MDN — CSP `connect-src`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/connect-src)
- [MDN — Using Fetch](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch)
- [MDN — CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [web.dev — CSP guide](https://web.dev/articles/content-security-policy)
