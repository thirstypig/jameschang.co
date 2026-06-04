// now/project-cards.js
// JS data layer for project cards on /now.
// Description, status, maturity, and next-up live here (editorial).
// Shipped items come from the cron — this file doesn't touch them.
//
// To activate: add <script src="/now/project-cards.js" defer></script>
// before </body> in now/index.html. Call renderAll() from the browser
// console to preview without activating auto-render.

(function () {
  'use strict';

  // ── Tabler outline icons (MIT) ────────────────────────────────────────
  // Inlined to avoid CDN dependency; only the 4 paths needed for badges.
  const ATTR = 'class="nb-proj-badge-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"';
  const ICON = {
    code:  `<svg ${ATTR}><path d="M7 8l-4 4 4 4"/><path d="M17 8l4 4-4 4"/><path d="M14 4l-4 16"/></svg>`,
    globe: `<svg ${ATTR}><circle cx="12" cy="12" r="9"/><path d="M3.6 9h16.8M3.6 15h16.8M11.5 3a17 17 0 0 0 0 18M12.5 3a17 17 0 0 1 0 18"/></svg>`,
    lock:  `<svg ${ATTR}><path d="M5 13a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-6z"/><circle cx="12" cy="16" r="1"/><path d="M8 13V7a4 4 0 0 1 8 0v6"/></svg>`,
    clock: `<svg ${ATTR}><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 15"/></svg>`,
  };

  function getBadgeIcon(status, maturity) {
    if (status === 'live' && maturity === 'private') return ICON.lock;
    if (status === 'live') return ICON.globe;
    if (status === 'blocked') return ICON.clock;
    return ICON.code;
  }

  function getBadgeLabel(status, maturity) {
    const s = status[0].toUpperCase() + status.slice(1);
    return maturity ? `${s} &middot; ${maturity[0].toUpperCase() + maturity.slice(1)}` : s;
  }

  // ── Safe escaping helper ──────────────────────────────────────────────
  // Use escapeHtml() on ANY value that comes from outside this file
  // (p.shipped, p.shippedUrl) before inserting it into HTML strings.
  // p.description / p.nextUp are your own prose — still good practice.
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // ── TODO: implement renderProjectCard(project) ─────────────────────────
  //
  // project = {
  //   slug:        string   — matches TLDR-{slug} markers in the HTML
  //   name:        string
  //   url:         string
  //   domain:      string   — display domain, e.g. "alephco.io"
  //   status:      "shipping" | "live" | "blocked"
  //   maturity:    "alpha" | "beta" | "public" | "private"
  //   description: string   — one sentence
  //   nextUp:      string
  //   shipped?:    string   — most recent commit/PR title (optional)
  //   shippedUrl?: string
  //   shippedTime?: string  — relative, e.g. "3h ago"
  // }
  //
  // Returns: HTML string for <article class="nb-proj-card">...</article>
  //
  // Things to handle:
  //   - Badge: getBadgeIcon(p.status, p.maturity) + getBadgeLabel(...)
  //   - Activity-first order: activity box BEFORE description
  //   - Empty activity state: if !p.shipped, use nb-proj-activity--empty
  //   - XSS: use escapeHtml() (defined above) on p.shipped and p.shippedUrl
  //     before inserting them. p.description / p.nextUp are your prose, but
  //     still safer to escape. href attributes need escapeHtml() too —
  //     a "javascript:" URL in p.shippedUrl would execute without it.
  //
  function renderProjectCard(p) {
    const badge = `<span class="nb-proj-badge nb-proj-badge--${p.status}">`
      + getBadgeIcon(p.status, p.maturity)
      + getBadgeLabel(p.status, p.maturity)
      + `</span>`;

    const safeHref = p.shippedUrl && p.shippedUrl.startsWith('https://')
      ? escapeHtml(p.shippedUrl) : null;
    const activity = p.shipped && safeHref
      ? `<div class="nb-proj-activity">
            <span class="nb-proj-activity-label">&#8593; shipped</span>
            <div class="nb-proj-activity-body">
              <a href="${safeHref}" rel="noopener" target="_blank">${escapeHtml(p.shipped)}</a>
              ${p.shippedTime ? `&middot; <time>${escapeHtml(p.shippedTime)}</time>` : ''}
            </div>
          </div>`
      : `<div class="nb-proj-activity nb-proj-activity--empty">
            <span class="nb-proj-activity-label">no recent activity</span>
          </div>`;

    return `<article class="nb-proj-card">
          <div class="nb-proj-head">
            <div class="nb-proj-title">
              <h3 class="nb-proj-name"><a href="${escapeHtml(p.url)}">${escapeHtml(p.name)}</a></h3>
              <span class="nb-proj-domain">${escapeHtml(p.domain)} &#8599;</span>
            </div>
            ${badge}
          </div>
          <!-- TLDR-${p.slug}-START -->
          ${activity}
          <p class="nb-proj-desc">${escapeHtml(p.description)}</p>
          <p class="nb-proj-next">
            <span class="nb-proj-next-label">next up</span>
            ${escapeHtml(p.nextUp)}
          </p>
          <!-- TLDR-${p.slug}-END -->
        </article>`;
  }

  // ── Project data ──────────────────────────────────────────────────────
  // Update status/maturity/description/nextUp here; shipped items come from cron.
  const ACTIVE = [
    {
      slug: 'jameschang-co',
      name: 'jameschang.co',
      url: 'https://jameschang.co',
      domain: 'jameschang.co',
      status: 'live',
      maturity: 'public',
      description: 'This site — plain HTML/CSS/JS on GitHub Pages, auto-updating from 8 data feeds.',
      nextUp: 'Keep shipping features; keep resume.pdf in sync.',
    },
    {
      slug: 'aleph',
      name: 'Aleph',
      url: 'https://alephco.io',
      domain: 'alephco.io',
      status: 'shipping',
      maturity: 'beta',
      description: 'The compliance platform for US importers — CPSIA, Prop 65, PFAS, and FSVP in one place.',
      nextUp: 'Line up the first paying customers.',
    },
    {
      slug: 'fantastic-leagues',
      name: 'The Fantastic Leagues',
      url: 'https://thefantasticleagues.com',
      domain: 'thefantasticleagues.com',
      status: 'shipping',
      maturity: 'beta',
      description: 'AI-powered fantasy baseball for serious keeper leagues — live for OGBA this season.',
      nextUp: 'Tighten in-season standings accuracy and daily stat lines.',
    },
  ];

  const BACKBURNER = [
    {
      slug: 'bahtzang-trader',
      name: 'Bahtzang Trader',
      url: 'https://bahtzang.com',
      domain: 'bahtzang.com',
      status: 'live',
      maturity: 'private',
      description: 'AI trading experiment — Claude makes buy/sell/hold calls against a paper-trading Alpaca account.',
      nextUp: '6 more paper trades to gate the Phase G live-trading switch.',
    },
    {
      slug: 'tastemakers',
      name: 'Tastemakers',
      url: 'https://tastemakersapp.com',
      domain: 'tastemakersapp.com',
      status: 'shipping',
      maturity: 'beta',
      description: 'Social dining discovery app — Laravel backend live on Railway, iOS/Android clients dormant.',
      nextUp: 'Migrate production DB from Namecheap MySQL to Railway.',
    },
    {
      slug: 'judge-tool',
      name: 'The Judge Tool',
      url: 'https://thejudgetool.com',
      domain: 'thejudgetool.com',
      status: 'blocked',
      maturity: 'alpha',
      description: 'Digital scoring platform for KCBS BBQ competitions — replaces clipboards and carbon copies.',
      nextUp: 'Build a real-DB test setup ahead of piloting at a sanctioned competition.',
    },
    {
      slug: 'ktv-singer',
      name: 'KTV Singer',
      url: 'https://ktvsinger.com',
      domain: 'ktvsinger.com',
      status: 'blocked',
      maturity: 'alpha',
      description: 'AI-assisted home karaoke system — phones pair with Apple TV over Socket.IO, YouTube-backed queue.',
      nextUp: 'Make end-to-end pairing reliable enough for friends without babysitting.',
    },
    {
      slug: 'tabledrop',
      name: 'TableDrop',
      url: 'https://tabledrop.com',
      domain: 'tabledrop.com',
      status: 'blocked',
      maturity: 'alpha',
      description: 'Marketplace for hard-to-get Taipei restaurant reservations — scraper + Stripe storefront.',
      nextUp: 'Get one full listing-to-purchase flow working with real data.',
    },
    {
      slug: 'thirsty-pig',
      name: 'The Thirsty Pig',
      url: 'https://thirstypig.com',
      domain: 'thirstypig.com',
      status: 'live',
      maturity: 'public',
      description: 'My food blog from 2007–present — 1,639 posts and 1,400+ mapped LA restaurants.',
      nextUp: 'Continue venue tag rollout, then launch the Bold Red Poster redesign.',
    },
  ];

  // ── Render ─────────────────────────────────────────────────────────────
  // NOTE: renderAll() replaces cron-generated card HTML inside #proj-active
  // and #proj-backburner. Cron-written shipped timestamps will be lost until
  // the next cron run rewrites the markers.  Call from the browser console
  // to preview, or activate by removing the guard below.
  function renderAll() {
    const active = document.getElementById('proj-active');
    const back   = document.getElementById('proj-backburner');
    if (active) active.innerHTML = ACTIVE.map(renderProjectCard).join('');
    if (back)   back.innerHTML   = BACKBURNER.map(renderProjectCard).join('');
  }

  // Expose for console use; remove the guard below to auto-render on load.
  window.__renderProjectCards = renderAll;
  // document.addEventListener('DOMContentLoaded', renderAll);
}());
