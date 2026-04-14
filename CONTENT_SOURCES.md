# Content sources — working notes

This file tracks the current-best content for the site, pulled from LinkedIn, the old jameschang.co site, and user input. It's a working document for content accuracy; not part of the final site.

## From LinkedIn (linkedin.com/in/jimmychang316, fetched 2026-04-14)

**Headline:** FSVP Pro  
✅ *Resolved 2026-04-14: "FSVP Pro" is James's placeholder/abbreviation from his Aleph Co. work — FSVP = FDA's Foreign Supplier Verification Program, which Aleph Co. handles. Replace with "**Aleph Co.**" on the site. James confirmed Aleph Co. is his founding vehicle / current primary work.*

**Location:** Los Angeles, California  
**Followers:** 1K | **Connections:** 500+

**About/Summary:**
> Senior Product Manager with 7+ years experience in 0→1 product development, B2B SaaS, and AI-Native solutions.

**Current Role:** Aleph Co. (founder/operator) — Los Angeles County, CA

**Aleph Co. products (live, fetched 2026-04-14):**

1. **Aleph Compliance** (alephco.io) — "**Product Compliance, Handled**"
   - SaaS for US importers managing FDA FSVP, CPSIA/CPC (children's products), CA Prop 65, and multi-state PFAS regulations
   - Problem framing: $100K+ enforcement penalties, fragmented records, overlapping regulations
   - Modules: FSVP, CPSIA/CPC (with lab test linking), Prop 65 (warning label generation), PFAS disclosure tracking
   - Positioning quotes: "No legal jargon. Plain-language questionnaires, pre-populated chemical..." / "Every feature is designed around the workflows of US importers..."
   - **Why this matters for the site narrative**: leverages James's own supply-chain/sourcing background at YETI, Cheng Loong, AT&T — he is *exactly* the user he's building for

2. **The Judge Tool** (thejudgetool.com) — "**Stop losing score cards. Start winning competitions.**"
   - Digital KCBS BBQ competition judging platform
   - Replaces pen-and-paper scoring with real-time tabulation + audit trails
   - User roles: Organizers, Judges, Table Captains
   - KCBS-compliant (valid scores 1, 2, 5, 6, 7, 8, 9), one-click category advancement (Chicken → Ribs → Pork → Brisket), CSV/JSON export

3. **The Fantastic Leagues** (thefantasticleagues.com) — "**the only fantasy platform with league-context AI**"
   - AI-powered fantasy baseball platform (Rotisserie, H2H Categories, H2H Points)
   - Powered by Google Gemini + Anthropic Claude (8 AI features)
   - Auction engine with real-time bidding + AI bid recommendations
   - Pricing: Free / Pro $29/season / Commissioner $49/season per league
   - Data: real-time MLB + FanGraphs + Statcast
   - 2026 season: free for all users during Pro/Commissioner "Coming Soon" period

---

## Full project portfolio (from ~/projects/ + GitHub, scanned 2026-04-14)

This is substantially larger than the 3 Aleph Co. products initially surfaced. James is running a portfolio of ~7–8 active products across native mobile, web, and API services.

### Live / launched
1. **Aleph Compliance** (alephco.io) — "Product Compliance, Handled." Compliance SaaS for US importers (FSVP, CPSIA/CPC, Prop 65, PFAS). Formerly branded "FSVP Pro" — rebrand to Aleph Co. happened in 2025/2026. *(Public www repo `alephco.io-www` HTML; private app `alephco.io-app` TypeScript; legacy `fsvppro`, `fsvppro-www`, `fsvppro.com` repos still exist.)*

2. **Bahtzang Trader** (bahtzang.com, public repo `bahtzang-trader`) — AI trading experiment using Claude Sonnet for buy/sell/hold evaluation. **Paper-trading only / not-real-cash** per James — positioned publicly as an experiment, not a live trading service. Dark-themed Next.js 14 dashboard + FastAPI Python backend. Integrations: Schwab, Alpaca, Alpha Vantage, Supabase Postgres, Slack notifier. 13 user pages + 9 admin pages. Guardrails + kill switch. Railway hosted.
   - **Site framing (from James):** keep it a little vague; indicate it's an experiment, not real-money trading
   - **Suggested card copy:** *"AI trading-decision experiment using Claude Sonnet. Paper-trading sandbox, not a live trading service."*

3. **TableDrop** (local dir, private repo) — "Restaurant reservation marketplace. Sellers list hard-to-get reservations, buyers purchase them." Next.js + Prisma/Neon Postgres + Clerk auth + Stripe + BullMQ + Playwright scraper. Originally positioned for Taipei per LinkedIn.

4. **Tastemakers** (multi-repo) — **iOS restaurant review app, currently down/paused** per James. Cross-platform investment: iOS (Swift, private), Android (Kotlin + Jetpack Compose, private), web (Next.js + TypeScript, public `tastemakers-web`), WordPress marketing site, JS backend. Past/paused, not actively live.
   - **Suggested card copy:** *"iOS restaurant-review app. Cross-platform build (iOS, Android, web); currently paused."* — honest about status, still surfaces the engineering range

5. **The Fantastic Leagues / FBST** (thefantasticleagues.com) — "Fantasy baseball league management tool for the OGBA league." React + Vite + TypeScript client + Express + TypeScript server + Prisma/PostgreSQL + Supabase auth. **15 domain feature modules** (auth, leagues, teams, players, roster, standings, trades, waivers, transactions, auction, keeper-prep, commissioner, admin, archive, periods). AI via Google Gemini + Anthropic Claude. Freemium pricing ($29/$49 tiers coming).

6. **The Judge Tool** (thejudgetool.com) — "Digital KCBS BBQ competition judging platform." Public static marketing site; private app TypeScript. Related local dir `bbq-judge`. 3 user roles (Organizers, Judges, Table Captains), KCBS-compliant scoring, real-time tabulation, audit trails.

7. **KTV Singer** (local dir + 8 GitHub repos, all private except none public) — "YouTube-powered karaoke system with real-time device pairing, synced lyrics, and shared song queue." Sub-projects: `ktv-singer-shared` (Drizzle ORM + Socket.IO types), `ktv-singer-server` (Express REST + Socket.IO), `ktv-singer-app` (Expo React Native iOS/Android/web), `ktv-singer-tvos` (native SwiftUI + AVPlayer), `ktv-singer-docs`, `ktv-singer-infra`, `ktv-singer-web`. Uses yt-dlp. Supabase PostgreSQL.

8. **The Thirsty Pig** (thirstypig.com, public repo `thirstypig-blog`) — His long-running food/travel blog, but the 2026 rebuild is a **major archival engineering project**: **923 blog posts** recovered from Wayback Machine across 3 domains (thirstypig.com, thethirstypig.com, blog.thethirstypig.com), **1,649 Instagram posts** imported from data export, **7,500+ images, 213 videos, 2,900+ pages, 1,000+ addresses geocoded via Foursquare Places API**. Stack: Astro + Tailwind v4 + Tina CMS + Vercel + Python (Wayback scraper + Instagram importer). This alone is a case-study-worthy data/engineering project.

### Lower signal / experimental
- **TrustDeskFinance** (local) — Python script + Excel financial model (`TrustDesk_Startup_Financials_v2.4.xlsx`). Likely internal finance tooling.
- **cooper-stack3** (local + private repo) — unknown purpose
- **productschoolcoding** (private repo) — Product School coursework

### Final "Current projects" strip — 7 cards (confirmed by James 2026-04-14)

Order recommendation (left-to-right, top-to-bottom — biggest / most distinctive first):

1. **Aleph Compliance** — compliance SaaS for US importers; your founder-operator headliner
2. **Bahtzang Trader** — Claude-powered trading-decision experiment (paper, not real-money)
3. **TableDrop** — restaurant reservation marketplace
4. **The Fantastic Leagues** — AI fantasy baseball platform (15 feature modules)
5. **The Judge Tool** — KCBS BBQ judging platform
6. **Tastemakers** — iOS restaurant-review app (paused)
7. **The Thirsty Pig** — food/travel blog (2007–); 2026 rebuild from Wayback + Instagram archive, 923 posts + 2,900 pages

Each card: name + one-liner + outbound link + optional tech/status tag. No screenshots.

**Education (LinkedIn):**
- University of Southern California — Marshall School of Business
- ⚠️ *Note: old jameschang.co site also listed Cal State LA (BS Business Admin). LinkedIn doesn't show it in fetched data but may be hidden behind auth. Confirm both degrees with James.*

**Licenses & Certifications (most recent first):**
1. Toggl Hire Product Development Skill Test Certificate — Nov 2024
2. Data-Driven Product Management (LinkedIn) — Oct 2024
3. Product Management: Building a Product Roadmap (LinkedIn) — Oct 2024
4. Technology for Product Managers (LinkedIn) — Oct 2024
5. Appcues Basics Certified — Aug 2023
6. Jasper Certified 2023 — Aug 2023
7. Certified Scrum Product Owner (CSPO), Scrum Alliance — Mar 2019
8. Product Management Certificate, Product School — Mar 2018

**Languages:**
- English — Native or bilingual proficiency
- Chinese — Full professional proficiency

**Volunteer:**
- Board Member — Chinese American Museum (Feb 2026–Present)

---

## From old jameschang.co (fetched 2026-04-14) — to merge with LinkedIn

**Experience (reverse chronological):**
- Gannett / LocaliQ / ReachLocal — Senior Product Manager, Woodland Hills CA (2022–2024)
  - Managed Scheduling product from conception to deployment
  - Calendar integrations + SMS notifications
  - 4,900+ free users, 400+ paid post-launch
  - Product managed SEO offerings and GenAI tools
- Sunrise Integration — Project Manager, LA (2020)
  - TeeLaunch, SAFIOsolutions clients
  - Led WarehouseConnector SaaS launch
- Movley — Operations/Product Manager, LA (Remote, 2019)
- MEDL Mobile — Product/Project Manager, Irvine CA (May–Dec 2018)
- MOMENTS Furniture — Social Media Specialist (Dec 2017–May 2018)
- Marquis Organic Energy — Ecommerce Consultant (Dec 2017–May 2018)
- The Thirsty Pig — Founder & Blogger (Nov 2008–current)
- YETI Coolers — Advanced Sourcing Agent, Packaging (Nov 2016–Jul 2017)
- My Wireless AT&T — Supply Chain Manager (May–Dec 2015)
- Cheng Loong Corporation — Manager, Global Marketing, Shanghai (Apr 2010–Apr 2015)
- Cobalt Skys — Sourcing Consultant, LA (Mar 2007–Jan 2010)
- Spray Technologies — Manager, Purchasing/Sourcing (Dec 2003–Feb 2007)
- Breeze Digital Technology / Breeze Home Products — Manager/BD, Taipei/Shenzhen (2001–2003)
- Alorica — Parts Mgmt Sales, Project Coordinator, Irvine (1998–2000)
- Emagine Studios — Intern (1996–1998)

**Education (old site):**
- USC Marshall School of Business — MBA, Class President
- California State University, Los Angeles — BS Business Administration
- ⚠️ *No dates listed on old site; need from James.*

**Skills/software stack (old site):**
Slack, SmartSheet, Jira, Trello, Basecamp, Zeplin, Invision, Marvel, Firebase, Google Suite, MS Office, SAP, Hootsuite, Buffer, Survey Monkey, MailChimp, Google Analytics. Development: iOS, Android, web responsive.

**Other:**
- Startup Weekend Santa Monica Fall 2018 — 2nd place

---

## Resolutions from James (2026-04-14)

| # | Question | Resolution |
|---|----------|------------|
| 1 | "FSVP Pro" headline meaning | → Replace with **Aleph Co.** (his founding vehicle). FSVP is a compliance acronym from Aleph's first product. |
| 2 | Current employment framing | → **Founder/operator at Aleph Co., building alephco.io + thejudgetool.com + thefantasticleagues.com simultaneously** |
| 3 | Case study picks | → Gannett Scheduling + one 2026 project + Thirsty Pig ← *my default recommendation, confirmed* |
| 4 | CSULA BS on site | → **Cut.** Only USC MBA on the education section. |

## Still open (lower priority)

- **Education dates** — USC MBA graduation year
- **Headshot** — new high-res, or reuse current site's
- **Contact email** — still `jimmychang316@gmail.com`?
- **Chinese American Museum board** — include in a "Community" footer line?
- **Case study narrative angle for Aleph Co.** — founding story? product pitch? judgment call (why this market)?
- **3 or 4 projects displayed?** — With Aleph Co. story front and center, the 3 Aleph products (Aleph Compliance, Judge Tool, Fantastic Leagues) might warrant their own short "Current projects" strip rather than being case studies. Consider structure:
  - **Case studies** (long-form, 250 words each): Gannett Scheduling + one Aleph deep-dive + Thirsty Pig
  - **Current projects** (short strip, 1–2 lines each + link): Aleph Compliance, Judge Tool, Fantastic Leagues
- **Supply-chain-to-SaaS narrative** — recommend leaning into this HARD. The through-line from YETI/Cheng Loong sourcing → FSVP compliance tool is the best single story on this résumé.

---

## Verified technical facts (2026-04-14, from GitHub official docs)

- **GitHub Pages apex A records**: 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 ✓
- **GitHub Pages AAAA records (IPv6)**: 2606:50c0:8000::153, 2606:50c0:8001::153, 2606:50c0:8002::153, 2606:50c0:8003::153 ✓ *(new since earlier plan — add these)*
- **CNAME file**: auto-created by GitHub when custom domain configured via Settings UI for branch-based deploys. Not required/ignored for Actions-based deploys.
