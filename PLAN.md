# jameschang.co — Redesign Plan

A best-practices plan for a personal résumé site. Optimized for: clarity for recruiters/hiring managers, low maintenance, fast load, good SEO, and a long shelf-life (no framework churn).

---

## Enhancement summary

**Deepened on:** 2026-04-14
**Sources:** best-practices researcher, simplicity reviewer, WCAG/performance research, SEO research, GitHub Pages docs (live), LinkedIn profile fetch.

### Key changes vs. first draft
1. **Simplicity cuts**: dropped the manual dark-mode toggle, scroll-spy nav, section fade-in animations, custom 404, contact form, analytics, and the `data.json` future-refactor note. All ceremony with near-zero payoff for a one-page résumé.
2. **2026 standards updates**: WCAG 2.1 → **2.2 AA**, FID → **INP** (<200ms), A records **plus IPv6 AAAA records** for GitHub Pages, AI-bot allowances in `robots.txt`.
3. **Design direction overhaul**: moved from "neutral + muted accent" to **editorial / serif-display H1 + sans body + warm off-white** — the move that reads "2026" rather than "2019 portfolio template."
4. **Case studies promoted** from Phase 3 into the v1 ship — they're the only reason someone visits the site instead of LinkedIn. Kept tight: 2–3 prose blocks ~250 words each with a "what I'd do differently" beat.
5. **Hero pattern**: shifted from generic spec to **"immediate value" pattern** — lead with what you shipped, not your name.
6. **Proof strip** added between hero and About (three top-line metrics or company logos) — biggest single 2024+ conversion pattern for senior IC sites.
7. **Print stylesheet promoted** from afterthought to its own section — the PDF the site generates is how you actually reach recruiters via email/ATS.
8. **Content pulled from live LinkedIn** (see `CONTENT_SOURCES.md`) — headline, summary, current projects, new certifications, current positioning all updated.

### Resolved 2026-04-14
- **"FSVP Pro" → Aleph Co.** (James's founding vehicle; alephco.io = Aleph Compliance, a SaaS for US importers)
- **Current framing**: founder/operator at Aleph Co., running a portfolio of products (Aleph Compliance, Bahtzang Trader, TableDrop, Tastemakers, Fantastic Leagues, Judge Tool, KTV Singer, Thirsty Pig rebuild) — see `CONTENT_SOURCES.md`
- **Case studies**: Gannett Scheduling + Aleph Compliance (founding story) + The Thirsty Pig
- **Education**: USC MBA only (2012, CSULA BS cut)
- **Headshot**: reuse current site's
- **Email**: jimmychang316@gmail.com

### Still open (all have defaults I'll use if you don't want to decide)
See §16. Top decision: **Senior PM framing vs. Operator-Builder framing** (default: duality — "PM by training, operator by practice"). Smaller: Thirsty Pig case-study angle, Aleph case-study angle, Chinese American Museum board footer line, accent color.

---

## 1. Goals & constraints

**Goals**
- Read as a credible, modern résumé at a glance (≤10 seconds to "who, what, why hire")
- Own the canonical version of James Chang's professional profile (supersede builder site + Drive PDFs)
- Rank for "James Chang product manager" and related queries — and show up in LLM-powered search (ChatGPT, Perplexity, Claude)
- Easy to update in ~5 minutes when a new role / cert / project lands

**Constraints**
- Plain HTML/CSS/JS — no build step, no framework
- Single-page site (with deep-linkable sections)
- Hosted free on GitHub Pages at custom domain `jameschang.co`
- No trackers, no ad networks, no analytics

### Research insights
- **User's explicit constraint:** "don't want to spend too much time on this." This is the tiebreaker when best-practice advice pushes scope.
- In 2026, LLM crawlers (ChatGPT, Perplexity, Claude) are the *second* audience after Google. Structured data and a clean, semantic page are now how you reach them too.

---

## 2. Information architecture

**Reduce five builder pages → one scroll with anchors.** Page-per-section for a single résumé is 2010s builder-thinking; modern recruiter UX is a single scrollable page.

Proposed section order (top to bottom, reflecting priority for recruiters and prospects):

1. **Hero / intro** — name, current positioning (founder/operator at Aleph Co. + senior PM), location, 3 CTAs (email, LinkedIn, résumé PDF)
2. **Proof strip** — 3 top-line metrics. Immediately below hero, above About.
3. **About** — 2–3 sentences in warm first person. The supply-chain-to-SaaS throughline.
4. **Current projects** — compact grid, **7 cards**: Aleph Compliance, Bahtzang Trader, TableDrop, The Fantastic Leagues, The Judge Tool, Tastemakers (paused), The Thirsty Pig. One-line descriptions + outbound links + small status tag where relevant ("paused", "experiment"). Signals "operator, not just résumé."
5. **Selected case studies** — 3 narrative blocks (~250 words each): context → judgment call → outcome → "what I'd do differently". Picks: **Gannett Scheduling** (shipped at scale) + **Aleph Compliance** (why I founded this, leveraging my import background) + **The Thirsty Pig** (long-term operator)
6. **Experience** — reverse-chronological; roles >5 years old collapsed into native `<details>` element labeled "Earlier experience (1996–2015)"
7. **Education** — USC MBA only (CSULA BS cut per James's decision) + certifications
8. **Skills** — grouped, short, not a logo grid
9. **Footer** — email (JS-revealed), LinkedIn, GitHub, Chinese American Museum board line (community signal), copyright, last-updated date

**Cut from current site:**
- Sports interests section — not a hiring signal, just cut
- Duplicate "More" nav dropdown
- Two separate Google Drive résumé links (replace with one PDF in-repo)

### Research insights
- **Why a proof strip:** the single biggest 2024–2026 shift in senior IC sites. Brittany Chiang, Lee Robinson, Lenny Rachitsky all do some version. Closes the credibility gap in the first viewport.
- **Skills go below Experience, not between it and Education.** Senior recruiters skim Experience → Projects → Skills (ATS keywords). Education is a footer item for someone with 10+ years experience.
- **Use native `<details>` / `<summary>`** for collapsible earlier experience — accessible, keyboard-operable, prints open automatically (print stylesheet matters for this).

---

## 3. Content standards

**Résumé bullet writing — XYZ formula (tighter than STAR):**

> **Accomplished [X] as measured by [Y] by doing [Z].**
> *"Shipped Scheduling 0→1 in 9 months, reaching 4,900 free + 400 paid accounts in year one, by sequencing SMS/calendar integrations ahead of AI features."*

Every bullet should answer one of three questions:
- **(a) what did you ship?**
- **(b) what did it move?** (numbers)
- **(c) what did you decide that others wouldn't have?** *(← this is the senior differentiator)*

Junior PMs describe features; senior PMs describe judgment calls. At least half your bullets should include a "by prioritizing X over Y" phrase or equivalent.

**Person/voice conventions:**
- **Hero + About**: warm first person ("I lead 0→1 PM work on…")
- **Experience bullets**: verb-led, implicit first-person ("Shipped…", "Led…", "Cut churn 40% by…"). Don't write "I" inside bullets.
- **Case studies**: first-person prose.

**Dates everywhere** — recruiters filter by tenure. Current site is missing graduation years for both degrees. Get these.

**One canonical résumé** — the PDF generated from the print stylesheet of `index.html` IS the résumé. Don't maintain a separate Google Doc.

### Research insights
- **"What I'd do differently" section** in each case study — this is the highest-signal senior-IC pattern to emerge in the last 2 years (Lenny Rachitsky, Shreyas Doshi school). Signals self-awareness + learning orientation + confidence.
- LinkedIn summary currently says "7+ years experience in 0→1 product development, B2B SaaS, and AI-Native solutions" — use this as the positioning spine; it's already tight.

---

## 4. Design system

**Direction:** editorial, not corporate. Think The Browser Company careers page, Linear about page, Every.to author pages — not Stripe or Vercel clones.

**Typography**
- **Body:** system stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`) — zero network cost, no GDPR issues, looks great. OR self-hosted **Geist** / **Inter Tight** if you want a distinctive sans (skip default Inter — overexposed).
- **Display H1 (hero only):** one serif accent — **Instrument Serif** or **Fraunces** (both free, open-source, can be subset). One serif headline on an otherwise sans page is *the* 2024–2026 move for personal sites.
- **Type scale:** 1.125 ratio. Base 16–18px. **H1 at 64–80px on desktop** (bigger than the original plan — hero should feel confident, not polite). Scales down on mobile.
- **Line-height** 1.5 body, 1.15 headings. Max line length ~65ch.

**Color**
- **Background**: warm off-white `#faf8f5` or `#f5f1ea` (not pure white — reads editorial, not bureaucratic)
- **Text**: near-black (`#1a1a1a`), not pure black
- **Accent**: one restrained color used *only* for links and focus rings. NOT blue (template tell). Deep terracotta, forest green, or a warm oxide red all work. Or stay fully neutral and use weight/underline for emphasis.
- **Dark mode**: via `@media (prefers-color-scheme: dark)` only. **No manual toggle.** Recruiters open your page at 2pm on a work laptop — a toggle is ceremony.
- **Browser chrome**: add `<meta name="color-scheme" content="light dark">` so scrollbars/controls match.
- **Contrast**: 4.5:1 body text / 3:1 large text (WCAG 2.2 AA).

**Layout**
- Body content: **max-width ~640–680px** (tighter than the original 720px — reads more editorial)
- Hero and section headers can break out wider (~960px) for asymmetric grid feel
- Generous whitespace. Section breaks via spacing and type weight, not rules or dividers.
- **No sticky header.** One light top nav with 4 anchor links; it scrolls with the page.

**Imagery**
- One professional headshot — served as **AVIF** with WebP fallback (browser support is universal in 2026, ~15KB at 400px width)
- Put the headshot in **About**, not the hero. Photo-in-hero skews "actor's headshot"; photo-in-about is "human context."
- One OG image (1200×630 PNG) reusing the headshot — don't design a bespoke card

**Motion**
- Essentially none. Smooth scroll on anchor nav (via CSS `scroll-behavior: smooth`), nothing else. Respect `prefers-reduced-motion` and disable even that.

### Research insights — 2026 anti-patterns to avoid
1. Glassmorphism / frosted blur (2020 artifact)
2. Gradient text H1 (Stripe invented it; now template tell)
3. "Hi, I'm James 👋" + waving emoji (2019 bootcamp cliché)
4. Skills as a logo grid (React/Figma/etc. logos) — reads junior
5. Typewriter / rotating "I build ___" text
6. Scroll-jacked parallax hero
7. Lottie / Rive illustrations (performance-hostile, taste-conservative)
8. Dark-mode-as-default (was 2022 dev-portfolio signal; 2026 is light-mode-first)
9. Three-column "What I do" icon grid (Strategy / Design / Development — generic agency trope)
10. "Let's work together!" CTA when you're hireable, not a freelancer
11. A blog you won't update (worse than no blog)

---

## 5. Hero section — the 5-second test

> **Lead with what you shipped, not your name. Your name is the URL bar.**

**Pattern — "Immediate value" (updated with Aleph Co. positioning):**

```
[Founder, Aleph Co. · Senior PM]   ← small pill/eyebrow

I build 0→1 products at the    ← display serif H1, 64–80px
intersection of supply chain,
SaaS, and AI — most recently
Aleph Compliance for US importers.

Currently operating three products at Aleph Co.
from Los Angeles. Previously shipped Scheduling 0→1
at Gannett/USA Today Network (4,900 signups in Y1).
                                ← warm positioning line, 18–20px

[ Email me ] [ Résumé PDF ] [ LinkedIn ]   ← three text-link CTAs, not buttons
```

**Why this framing works:**
- Leads with **founder** — the strongest 2026 signal available, and it's true
- Supply-chain → SaaS → AI arc is the most differentiated line on the site; nobody else has this combo
- Dropped the "exploring my next PM role" availability pitch — James is not between roles, he's operating. The site should reflect that. If the narrative later shifts to "open to senior PM roles alongside Aleph," we can add it back.

- Name appears in `<title>`, JSON-LD, and the About section — not as the visual H1
- **CTA hierarchy: Email > Résumé PDF > LinkedIn.** Email is the conversion.
- **"Currently" line** is the highest-ROI element on a senior IC site — recruiters cold-read for availability signals
- No headshot here (moves to About)

### Research insights
- Three hero patterns were considered: Editorial (Brittany Chiang), Business Card (Josh Comeau), and Immediate Value (Julian Shapiro, Nat Eliason). For a senior PM selling judgment + outcomes, Immediate Value outperforms.
- If you feel the positioning is too project-specific, fallback is: *"I build 0→1 products at the intersection of SaaS, mobile, and AI."*

---

## 6. Case studies — the differentiator vs. LinkedIn

Write **2–3 case studies**, ~250 words each. Without these, the site is a LinkedIn export. With them, it's a portfolio of judgment.

**Structure per case study:**

```markdown
### Project name — Company, Year
One-line framing.

**Context** (1 short para)
The problem, the constraint, what "good" looked like.

**What I did** (1 short para)
The 2–3 judgment calls you made and why. Not a feature list.
"The team wanted to build X. I argued for Y because [insight]."

**Outcome** (2–3 bolded metrics)
With context: "4,900 free + 400 paid in Y1 (vs. plan of 2,500)."

**What I'd do differently** (1–2 sentences)
Senior signal. Juniors hide trade-offs; seniors own them.
```

**Visual treatment**: each case study is a standalone `<article>`. Pull one metric out at display-type size (e.g., `4,900 signups` at 48–64px). Type hierarchy, not card boxes.

**Anti-patterns**: screenshots / mockups (either confidential or boring, often both); long intro paragraphs; feature bullets.

**Selected subjects (confirmed with James):**
- **Gannett Scheduling** (2022–2024) — 0→1 at scale. 4,900 free + 400 paid in Y1. Judgment call: prioritized calendar/SMS integrations ahead of AI features.
- **Aleph Compliance** (2025–) — founder/operator. Judgment call: built a compliance SaaS for US importers because I was a US importer for 15 years (YETI, Cheng Loong, AT&T Wireless, Cobalt Skys) and watched $100K+ enforcement penalties get normalized. The market doesn't need another horizontal SaaS; it needs vertical tooling from someone who's done the work. *This is the highest-judgment case study on the site — write it first.*
- **The Thirsty Pig** (2008–) — long-term 0→1 operator. 16,000+ monthly pageviews at 2013 peak. Judgment calls: expanded to Shanghai in Q1 2010, migrated Blogger → WordPress, built distribution via PR/restaurateur collaborations ahead of algorithmic plays.

**Not selected as case studies (live on the "Current projects" strip instead):**
- The Judge Tool (thejudgetool.com) — one-liner + outbound link
- The Fantastic Leagues (thefantasticleagues.com) — one-liner + outbound link
- Aleph Compliance link also appears here (case study + project card is fine — they serve different reader intents)

---

## 7. Technical architecture

```
jameschang.co/
├── index.html            # single-page résumé (can inline CSS for single-file send)
├── styles.css            # or inlined — your call
├── script.js             # ~15 lines: email reveal. That's it.
├── resume.pdf            # generated from print stylesheet
├── assets/
│   ├── headshot.avif     # + .webp fallback
│   ├── og-image.png      # 1200×630 social preview (reuse headshot)
│   └── favicon.svg
├── CNAME                 # contains: jameschang.co (auto-generated by GitHub UI)
├── .nojekyll             # disables Jekyll processing
├── robots.txt            # 15 lines; AI-bot allowances
├── sitemap.xml           # 10 lines; single URL
├── llms.txt              # emerging convention for LLM crawlers
├── CONTENT_SOURCES.md    # working doc (not deployed content)
├── PLAN.md               # this file
└── README.md             # how to edit, deploy
```

**Semantic HTML** — `<header>`, `<main>`, `<section>` with headings, `<article>` per role/case study, `<time datetime="...">` for dates, `<nav>`, `<footer>`. Screen readers and SEO both reward this.

**Progressive enhancement** — site works with JS disabled. JS only adds: email reveal on click.

**No frameworks, no jQuery, no npm.** Entire site should be under **50KB gzipped** including headshot — achievable targets per `joshwcomeau.com` / `brittanychiang.com` benchmarks.

**Consider single-file HTML** — inline all CSS in a `<style>` block in `index.html`. Eliminates one request, still trivially editable. Viable because this is one page.

### Research insights
- `view-transition-name` CSS (2024+ native browser feature, zero JS) can add smooth section navigation transitions for ~10 lines of CSS if you want a little extra polish.
- If you ever want server headers (CSP, HSTS), put Cloudflare in front of GitHub Pages — free, adds free Web Analytics as a bonus. Not needed for v1.

---

## 8. Accessibility — WCAG 2.2 AA

Upgrade target from 2.1 AA (original plan) to **2.2 AA** (current standard since 2023).

**Baseline**
- `<html lang="en">`
- Skip-to-main-content link as first focusable element
- Every image has meaningful alt text
- Semantic HTML over ARIA
- Form labels explicitly associated with inputs (if/when forms exist)
- Heading hierarchy: H1 → H2 → H3, no skips
- Link underlines (WCAG 2.2 requirement — links must be visually distinct from surrounding text beyond color alone)

**WCAG 2.2 new criteria that apply here**
- **2.4.11 Focus Not Obscured** — sticky elements must not hide the focus ring. Fix: don't use a sticky header.
- **2.5.5 / 2.5.8 Target Size** — interactive targets ≥24×24 CSS pixels. Nav links, theme-aware icons, CTA links: pad to at least 44×44 comfortable target, 24×24 absolute minimum.

**Focus rings** — use `:focus-visible`, not `:focus` (shows only on keyboard nav, not mouse clicks):

```css
:focus-visible {
  outline: 3px solid currentColor;
  outline-offset: 2px;
  border-radius: 2px;
}
```

**Reduced motion**
```css
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Check before ship**: run axe DevTools; target zero critical/serious issues. Don't chase Lighthouse decimal points — "passes axe clean" is the real bar.

---

## 9. Performance targets

**Core Web Vitals (2026 thresholds)**
- **LCP** < 2.5s "good" — we'll hit <1.0s on GitHub Pages CDN
- **INP** < 200ms "good" *(replaced FID in March 2024)* — trivial with ~15 lines of JS
- **CLS** < 0.1 "good" — target <0.05 (reserve space for images with explicit width/height)
- **TTFB** < 600ms — GitHub Pages CDN typically delivers <200ms

**Page weight target: under 50KB total gzipped.** Brittany Chiang and Josh Comeau benchmarks. A résumé site should be smaller than most favicons bundles.

**Practices**
- Preload the headshot (`<link rel="preload" as="image" fetchpriority="high">`)
- Self-host any custom fonts (avoid Google Fonts CDN — GDPR, round-trip cost)
- Use AVIF for images with WebP fallback
- Defer or avoid all JS
- `loading="lazy"` for anything below the fold (probably just the OG/share image, if visible anywhere)

---

## 10. SEO & metadata

**Complete `<head>` block** — paste-ready starting point:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">

  <title>James Chang — Senior Product Manager</title>
  <meta name="description" content="Senior Product Manager building 0→1 products in B2B SaaS, mobile, and AI-native tools. MBA (USC Marshall), CSPO. Based in Los Angeles.">

  <link rel="canonical" href="https://jameschang.co/">

  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:title" content="James Chang — Senior Product Manager">
  <meta property="og:description" content="Senior PM building 0→1 products. Most recently: Scheduling at USA Today Network (4,900 signups Y1).">
  <meta property="og:url" content="https://jameschang.co/">
  <meta property="og:image" content="https://jameschang.co/assets/og-image.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="James Chang, Senior Product Manager">
  <meta property="og:site_name" content="James Chang">
  <meta property="og:locale" content="en_US">

  <!-- Twitter/X Card -->
  <meta name="twitter:card" content="summary_large_image">

  <!-- Favicons -->
  <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">

  <!-- Structured data: WebSite + Person -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        "url": "https://jameschang.co",
        "name": "James Chang"
      },
      {
        "@type": "Person",
        "name": "James Chang",
        "jobTitle": "Senior Product Manager",
        "url": "https://jameschang.co",
        "image": "https://jameschang.co/assets/headshot.avif",
        "sameAs": [
          "https://www.linkedin.com/in/jimmychang316",
          "https://github.com/thirstypig"
        ],
        "alumniOf": {
          "@type": "CollegeOrUniversity",
          "name": "USC Marshall School of Business"
        },
        "knowsAbout": ["Product Management", "0 to 1 Product Development", "B2B SaaS", "Mobile Apps", "AI-Native Tools"],
        "workLocation": {
          "@type": "Place",
          "address": {
            "@type": "PostalAddress",
            "addressLocality": "Los Angeles",
            "addressRegion": "CA",
            "addressCountry": "US"
          }
        }
      }
    ]
  }
  </script>

  <link rel="stylesheet" href="/styles.css">
</head>
```

**`robots.txt`** — allow AI crawlers explicitly in 2026:

```
User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

# Block scrape-for-resale bots
User-agent: AhrefsBot
Disallow: /

User-agent: SemrushBot
Disallow: /

Sitemap: https://jameschang.co/sitemap.xml
```

**`sitemap.xml`** — one URL:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://jameschang.co/</loc>
    <lastmod>2026-04-14</lastmod>
  </url>
</urlset>
```

**`llms.txt`** (emerging 2026 convention — plain-text summary of the site's content for LLM crawlers; costs nothing):

```
# James Chang
Senior Product Manager based in Los Angeles.
7+ years building 0→1 products in B2B SaaS, mobile, and AI-native tools.
MBA, USC Marshall School of Business. CSPO certified.

Current projects: TableDrop (restaurant reservations, Taipei), The Judge Tool (KCBS judging), KTV Singer (multi-platform karaoke).

Most recent role: Senior Product Manager at Gannett/LocaliQ (2022–2024), shipping the Scheduling product (4,900 free + 400 paid accounts in Y1).

Contact: see https://jameschang.co/
```

**Resolve www. vs apex** — canonical URL points to `https://jameschang.co/`. Set up `www.` as a 301 redirect to apex at the registrar / via GitHub's auto-redirect.

### Research insights
- **og:type** — use `website` not `profile` in 2026. Works universally on LinkedIn, iMessage, Slack.
- **LinkedIn has no proprietary meta tags** — just reads Open Graph. No special `linkedin:*` tags needed.
- **Debate on JSON-LD:** "James Chang" is a common name; you won't out-rank the actors. But JSON-LD cost is low (~30 lines), and it's increasingly how LLM search surfaces identify people. Include the basic version; don't over-engineer.

---

## 11. Privacy

- **Email obfuscation** — no plain `mailto:` in HTML (scraped in days). Use JS to build the `mailto:` on click. ~10 lines.
- **No analytics.** What decision would traffic data drive on a résumé site? None. Skip it.
- **No Google Fonts CDN** — self-host or use system stack. (Post-Schrems II GDPR concern.)
- **No cookies** = no cookie banner needed. Feature.

---

## 12. Hosting & deployment

**GitHub Pages setup:**
1. Push code to `main` branch of `thirstypig/jameschang.co`
2. Settings → Pages: source = **Deploy from branch** → `main` / `/` (root)
3. Custom domain field: enter `jameschang.co` (creates the CNAME file automatically)
4. **Enforce HTTPS** — check the box after DNS verifies

**DNS at your registrar** (jameschang.co):

| Type | Host | Value |
|------|------|-------|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| AAAA | @ | 2606:50c0:8000::153 |
| AAAA | @ | 2606:50c0:8001::153 |
| AAAA | @ | 2606:50c0:8002::153 |
| AAAA | @ | 2606:50c0:8003::153 |
| CNAME | www | thirstypig.github.io |

*AAAA (IPv6) records verified from GitHub docs on 2026-04-14 — were not in the original plan.*

- Let's Encrypt cert provisions automatically once DNS resolves (5–15 min typically, up to 24h worst case)
- Propagation: typically 1–6h, up to 48h
- `.co` TLDs are fully supported; no special handling

**Deploy flow** = `git push`. No CI, no build, no webhooks.

---

## 13. Print stylesheet — the detail that matters most

Your PDF résumé is how recruiters actually reach you (email attachments, ATS uploads). The website is the discovery surface; the PDF is the deliverable. Invest here up front.

```css
@media print {
  @page { size: letter; margin: 0.5in; }

  /* Strip navigation, CTAs, theme affordances */
  nav, .cta-row, .hero .availability,
  footer .social, .og-share { display: none; }

  /* Neutral typography for print */
  body {
    font-size: 10.5pt;
    color: #000;
    background: #fff;
    font-family: Georgia, "Times New Roman", serif;
  }

  /* Inline URLs after links for print */
  a { color: #000; text-decoration: none; }
  a[href^="http"]::after {
    content: " (" attr(href) ")";
    font-size: 9pt;
    color: #444;
  }

  /* Never split a role mid-page */
  section, article { page-break-inside: avoid; break-inside: avoid; }
  h2, h3 { page-break-after: avoid; }

  /* Force-expand any collapsed earlier experience */
  details[open], details { display: block; }
  details summary { display: none; }
  details > *:not(summary) { display: revert; }

  /* Strip hero to just name + contact */
  .hero h1 { font-size: 22pt; margin-bottom: 4pt; }
  .hero .positioning { display: none; }
  .headshot { display: none; } /* or max-width: 1in; */
}
```

**Test protocol:** `Cmd-P → Save as PDF`. Output should be a 1–2 page PDF you'd email a recruiter without editing. Commit the generated PDF as `resume.pdf`. The PDF and page stay in sync because the PDF IS the page.

---

## 14. Maintenance model

- **Content lives in `index.html`.** One file. That's it.
- **Update the last-updated timestamp in the footer** every time you push. Small, signals freshness.
- **Regenerate `resume.pdf`** every time you update experience. Print → Save as PDF → commit.
- **Local preview**: `python3 -m http.server` in the repo directory, visit `localhost:8000`.
- **When LinkedIn changes, site changes too** — pick LinkedIn or the site as source of truth and sync within a few days. (Recommendation: site is canonical, LinkedIn mirrors.)

---

## 15. Phased rollout

Collapsed from 3 phases → **2 phases.** Old Phase 3 ("Extras") was where this project would die; its contents were either cut (analytics, contact form) or promoted into v1 ship (case studies).

### Phase 1 — Ship v1 (one sitting, ~3–4 hours)
- Scaffold files, inline CSS is fine
- Hero with "immediate value" pattern
- Proof strip (3 metrics or 3 logos)
- About section with headshot
- **2–3 case studies** as prose blocks (promoted from Phase 3)
- Experience with `<details>` for pre-2015 roles
- Education with grad years + certifications
- Skills (short, grouped)
- Footer with email-reveal, LinkedIn, GitHub, last-updated
- Full `<head>` block with OG + JSON-LD
- `robots.txt`, `sitemap.xml`, `llms.txt`
- **Print stylesheet** (don't defer this)
- WCAG 2.2 checks (run axe)
- Deploy to GitHub Pages + DNS cutover
- ✅ **Goal**: jameschang.co serves from GitHub, reads as 2026, prints to a clean PDF. **Done.**

### Phase 2 — Optional polish (only if something actually bugs you after living with v1)
- Self-host Instrument Serif / Geist if the system stack doesn't feel right
- Add `view-transition-name` CSS for section transitions
- Add Cloudflare in front for security headers + free Web Analytics (if you later decide you want stats)
- Refine case study copy based on what recruiters ask about
- ✅ **Goal**: iterate based on real signal, not speculation.

**Old Phase 3 (cut/absorbed):**
- ~~Analytics~~ — cut. What decision does it drive?
- ~~Contact form~~ — cut. mailto with JS reveal is strictly better.
- ~~Privacy policy page~~ — cut. No cookies, no need.
- ~~Custom 404~~ — cut. One-page site; default is fine.
- Case studies → promoted to v1.

---

## 16. Open questions

### Resolved (2026-04-14)

| # | Question | Resolution |
|---|----------|------------|
| 1 | "FSVP Pro" headline | → Replace with **Aleph Co.** (James's founding vehicle; FSVP was a product-line acronym) |
| 2 | Employment framing | → **Founder/operator at Aleph Co.**, running 3 products: Aleph Compliance, The Judge Tool, The Fantastic Leagues |
| 3 | Case study picks | → Gannett Scheduling + **Aleph Compliance** (founding story) + The Thirsty Pig |
| 4 | CSULA BS | → **Cut.** USC MBA only on the education section. |

### Resolved (2026-04-14, round 2)

| # | Question | Resolution |
|---|----------|------------|
| 5 | USC MBA graduation year | → **2012** |
| 6 | Headshot | → Reuse the current jameschang.co headshot |
| 7 | Contact email | → Keep `jimmychang316@gmail.com` |

### Resolved (2026-04-14, round 3)

| # | Question | Resolution |
|---|----------|------------|
| 9 | Current-projects strip count | → **7 cards** (James: "6 is fine. but add the Judge Tool also. so 7") |
| 10 | What is Tastemakers | → iOS restaurant-review app, **currently paused/down**. Include with honest status label. |
| 11 | Bahtzang Trader public reference | → **Yes, but keep it vague — frame as a paper-trading experiment, not real-money.** Suggested card copy: *"AI trading-decision experiment using Claude Sonnet. Paper-trading sandbox, not a live trading service."* |

### Still open

8. **Positioning framing** — Senior PM (hireable) / Operator-Builder / "PM by training, operator by practice" (duality). **With a 7-card current-projects strip, option (a) Senior-PM-first will read inconsistent — the page will obviously show an operator.** Recommend (c) duality, default to that if no answer.

12. **Thirsty Pig case-study angle** — blog-as-audience-build (2008–) OR the 2026 rebuild-from-Wayback data-engineering story. I can write either; default will be the rebuild angle because it's more distinctive and recent.

13. **Aleph Compliance case study angle** — founding narrative / product pitch / judgment call. Default: founding narrative.

14. **Chinese American Museum board role** — one-line "Community" item in footer? Default: yes.

15. **Accent color** — terracotta / forest green / warm oxide red / other? Default: warm oxide red (`#a03623` area), with light off-white background `#faf8f5`.
