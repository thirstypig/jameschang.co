// /now-specific scripts — externalized from inline so the page CSP can drop 'unsafe-inline'.
// Two IIFEs: (1) Thirsty Pig hitlist fetch (CORS-locked to jameschang.co; silent-fail on localhost),
// (2) live-relative-time upgrader (rewrites .data-rel <time> elements every 60s).

// Hit list fetch from thirstypig.com — same pattern as live /now/.
    // Silent fail removes the section if no items / fetch error.
    (async function () {
      const container = document.getElementById('hitlist-section');
      if (!container) return;
      const LINK_LABELS = { yelp: 'Yelp', google: 'Map', instagram: 'IG', resy: 'Resy', opentable: 'OpenTable', website: 'Site' };
      try {
        const res = await fetch('https://thirstypig.com/places-hitlist.json');
        if (!res.ok) throw new Error(res.status);
        const data = await res.json();
        const items = (data.items || []).slice(0, 5);
        if (!items.length) { container.remove(); return; }

        const head = document.createElement('header');
        head.className = 'nb-section-head';
        const num = document.createElement('span');
        num.className = 'nb-section-num';
        num.textContent = '/10';
        const title = document.createElement('h2');
        title.className = 'nb-section-title';
        title.textContent = 'places i want to eat at';
        const rule = document.createElement('span');
        rule.className = 'nb-section-rule';
        head.append(num, title, rule);
        container.appendChild(head);

        const card = document.createElement('div');
        card.className = 'nb-card compact';
        const ul = document.createElement('ul');
        ul.style.margin = '0';
        ul.style.padding = '0';
        ul.style.listStyle = 'none';
        ul.style.display = 'grid';
        ul.style.gap = '8px';
        items.forEach(item => {
          const li = document.createElement('li');
          const name = document.createElement('strong');
          name.textContent = item.name;
          li.appendChild(name);
          const locText = (item.neighborhood ? item.neighborhood + ', ' : '') + (item.city || '');
          if (locText.trim().replace(/,\s*$/, '').length) {
            const loc = document.createElement('span');
            loc.style.color = 'var(--dim)';
            loc.textContent = ' — ' + locText.replace(/,\s*$/, '');
            li.appendChild(loc);
          }
          const linkEntries = Object.entries(item.links || {}).filter(([, url]) => url);
          if (linkEntries.length) {
            const linksSpan = document.createElement('span');
            linksSpan.style.fontSize = '11px';
            linksSpan.style.fontFamily = 'var(--mono)';
            linksSpan.appendChild(document.createTextNode(' · '));
            linkEntries.forEach(([key, url], i) => {
              if (i > 0) linksSpan.appendChild(document.createTextNode(' · '));
              const a = document.createElement('a');
              if (!/^https?:\/\//i.test(url)) return;
              a.href = url;
              a.textContent = LINK_LABELS[key] || key;
              a.target = '_blank';
              a.rel = 'noopener noreferrer';
              linksSpan.appendChild(a);
            });
            li.appendChild(linksSpan);
          }
          ul.appendChild(li);
        });
        card.appendChild(ul);
        const footerLink = document.createElement('a');
        footerLink.href = 'https://thirstypig.com/hitlist/';
        footerLink.textContent = 'See the full list →';
        footerLink.style.display = 'inline-block';
        footerLink.style.marginTop = '12px';
        footerLink.style.fontFamily = 'var(--mono)';
        footerLink.style.fontSize = '12px';
        card.appendChild(footerLink);
        container.appendChild(card);
      } catch (e) {
        console.warn('[hitlist]', e);
        container.remove();
      }
    })();

// Bucket list — top 5 todos rendered from /bucketlist.json (same-origin, no CORS issue).
// Silent fail removes the section if no items / fetch error.
    (async function () {
      const container = document.getElementById('bucketlist-section');
      if (!container) return;
      try {
        const res = await fetch('/bucketlist.json', { cache: 'reload' });
        if (!res.ok) throw new Error(res.status);
        const data = await res.json();
        const PRI_RANK = { high: 0, medium: 1, low: 2 };
        const todos = (data.items || [])
          .filter(i => i.status === 'todo')
          .slice()
          .sort((a, b) => (PRI_RANK[a.priority] ?? 99) - (PRI_RANK[b.priority] ?? 99))
          .slice(0, 5);
        if (!todos.length) { container.remove(); return; }

        const head = document.createElement('header');
        head.className = 'nb-section-head';
        const num = document.createElement('span');
        num.className = 'nb-section-num';
        num.textContent = '/11';
        const title = document.createElement('h2');
        title.className = 'nb-section-title';
        title.textContent = 'bucket list';
        const rule = document.createElement('span');
        rule.className = 'nb-section-rule';
        head.append(num, title, rule);
        container.appendChild(head);

        const eyebrow = document.createElement('p');
        eyebrow.className = 'nb-section-eyebrow';
        eyebrow.textContent = 'top ' + todos.length + ' · highest priority';
        container.appendChild(eyebrow);

        const card = document.createElement('div');
        card.className = 'nb-card compact';
        const ol = document.createElement('ol');
        ol.style.margin = '0';
        ol.style.padding = '0 0 0 20px';
        ol.style.display = 'grid';
        ol.style.gap = '8px';
        todos.forEach(item => {
          const li = document.createElement('li');
          const name = document.createElement('strong');
          name.textContent = item.title;
          li.appendChild(name);
          if (item.note) {
            const note = document.createElement('span');
            note.style.color = 'var(--dim)';
            note.textContent = ' — ' + item.note;
            li.appendChild(note);
          }
          ol.appendChild(li);
        });
        card.appendChild(ol);
        const footerLink = document.createElement('a');
        footerLink.href = '/bucketlist/';
        footerLink.textContent = 'See the full list →';
        footerLink.style.display = 'inline-block';
        footerLink.style.marginTop = '12px';
        footerLink.style.fontFamily = 'var(--mono)';
        footerLink.style.fontSize = '12px';
        card.appendChild(footerLink);
        container.appendChild(card);
      } catch (e) {
        console.warn('[bucketlist]', e);
        container.remove();
      }
    })();

// Quotes — collected external quotes rendered from /quotes.json (same-origin).
// Each quote is an equal-size card; clicking opens the shared #quote-modal
// <dialog> with the full text + attribution. Silent-fail removes the section.
    (async function () {
      const container = document.getElementById('quotes-section');
      if (!container) return;
      const modal = document.getElementById('quote-modal');
      const modalBody = modal && modal.querySelector('.nb-quote-modal-body');

      // textContent-only node builder — keeps CJK/Latin/quote chars inert (no innerHTML).
      function el(tag, cls, text, lang) {
        const node = document.createElement(tag);
        if (cls) node.className = cls;
        if (text != null) node.textContent = text;
        if (lang) node.lang = lang;
        return node;
      }

      function openModal(q) {
        if (!modal || !modalBody || !modal.showModal) return;
        modalBody.replaceChildren();
        modal.scrollTop = 0;
        if (q.title) modalBody.appendChild(el('p', 'nb-quote-modal-title', q.title));
        if (q.entries && q.entries.length) {
          // Collection (many quotes) or poem (stanzas) — one box, expanded list.
          const isPoem = q.category === 'poem';
          const list = document.createElement(isPoem ? 'div' : 'ol');
          list.className = isPoem ? 'nb-quote-poem' : 'nb-quote-list';
          q.entries.forEach(function (entry) {
            list.appendChild(el(isPoem ? 'p' : 'li',
              isPoem ? 'nb-quote-poem-stanza' : 'nb-quote-list-item', entry));
          });
          modalBody.appendChild(list);
        } else if (q.original) {
          modalBody.appendChild(el('p', 'nb-quote-modal-original', q.original, q.lang));
          const gloss = q.translation || q.text;
          if (gloss) modalBody.appendChild(el('blockquote', 'nb-quote-modal-text', gloss));
        } else {
          modalBody.appendChild(el('blockquote', 'nb-quote-modal-text', q.text));
        }
        if (q.source) modalBody.appendChild(el('p', 'nb-quote-modal-source', '— ' + q.source));
        if (q.note) modalBody.appendChild(el('p', 'nb-quote-modal-note', q.note));
        // Optional external link (e.g. a clip). Only render http/https URLs.
        if (q.link && q.link.url && /^https?:\/\//i.test(q.link.url)) {
          const a = document.createElement('a');
          a.className = 'nb-quote-modal-link';
          a.href = q.link.url;
          a.textContent = q.link.label || 'Watch ↗';
          a.target = '_blank';
          a.rel = 'noopener noreferrer';
          modalBody.appendChild(a);
        }
        modal.showModal();
      }

      // Close when the backdrop (outside the dialog content) is clicked.
      if (modal) {
        modal.addEventListener('click', function (e) {
          if (e.target === modal) modal.close();
        });
      }

      try {
        const res = await fetch('/quotes.json', { cache: 'reload' });
        if (!res.ok) throw new Error(res.status);
        const data = await res.json();
        const items = (data.items || []).filter(q => q && (q.text || q.original));
        if (!items.length) { container.remove(); return; }

        const head = document.createElement('header');
        head.className = 'nb-section-head';
        const num = el('span', 'nb-section-num', '/12');
        const title = el('h2', 'nb-section-title', 'quotes');
        const rule = el('span', 'nb-section-rule');
        head.append(num, title, rule);
        container.appendChild(head);

        container.appendChild(el('p', 'nb-section-eyebrow', items.length + ' collected · tap a card to expand'));

        const grid = document.createElement('div');
        grid.className = 'nb-quote-grid';
        items.forEach(q => {
          const btn = document.createElement('button');
          btn.className = 'nb-quote-card';
          btn.type = 'button';
          if (q.title) btn.classList.add('nb-quote-card--collection');
          const headline = q.title || q.original || q.text;
          btn.appendChild(el('span', 'nb-quote-card-text', headline, (!q.title && q.original) ? q.lang : ''));
          // Collections/poems carry a title; show the quote text as a teaser line beneath it.
          if (q.title && q.text) btn.appendChild(el('span', 'nb-quote-card-teaser', q.text));
          if (q.source) btn.appendChild(el('span', 'nb-quote-card-source', q.source));
          btn.appendChild(el('span', 'nb-quote-card-expand', '+', null));
          btn.setAttribute('aria-haspopup', 'dialog');
          btn.addEventListener('click', function () { openModal(q); });
          grid.appendChild(btn);
        });
        container.appendChild(grid);
      } catch (e) {
        console.warn('[quotes]', e);
        container.remove();
      }
    })();

// Detail cards (people i follow + off the clock) — each .nb-detail-trigger button
// opens the shared #detail-modal, populated by CLONING the card's <template> content
// (preserves links/<em>, XSS-safe, no innerHTML). CSP forbids inline handlers, so the
// wiring lives here.
    (function () {
      const modal = document.getElementById('detail-modal');
      const body = modal && modal.querySelector('.nb-quote-modal-body');
      if (!modal || !body || !modal.showModal) return;
      modal.addEventListener('click', function (e) { if (e.target === modal) modal.close(); });
      document.querySelectorAll('.nb-detail-trigger').forEach(function (btn) {
        btn.addEventListener('click', function () {
          const card = btn.closest('.nb-detail-card');
          const tpl = card && card.querySelector('template');
          if (!tpl) return;
          body.replaceChildren(tpl.content.cloneNode(true));
          modal.scrollTop = 0;
          modal.showModal();
        });
      });
    })();

// Auto-prune past calendar entries — removes any .nb-cal-card with a
// data-cal-end (or .nb-target li with a single <time datetime>) whose
// date is strictly before today (local). Cards covering today or a
// future day stay. Runs once at load; nothing rebuilds the DOM after.
    (function () {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      function isPast(iso) {
        if (!iso) return false;
        const d = new Date(iso);
        if (isNaN(d)) return false;
        d.setHours(23, 59, 59, 999); // Treat the whole event-day as "today"
        return d < today;
      }
      document.querySelectorAll('.nb-cal-card[data-cal-end]').forEach(function (el) {
        if (isPast(el.getAttribute('data-cal-end'))) el.remove();
      });
      document.querySelectorAll('.nb-target li').forEach(function (li) {
        const t = li.querySelector('time[datetime]');
        if (t && isPast(t.getAttribute('datetime'))) li.remove();
      });
      // If a .nb-target list ends up empty after pruning, hide the whole block.
      document.querySelectorAll('.nb-target').forEach(function (block) {
        const ul = block.querySelector('ul');
        if (ul && !ul.children.length) block.style.display = 'none';
      });
    })();

// Live-relative timestamps — same upgrader as live /now/.
    (function () {
      function fmt(ms) {
        var m = Math.floor(ms / 60000);
        if (m < 1) return 'just now';
        if (m < 60) return m + 'm ago';
        var h = Math.floor(m / 60);
        if (h < 24) return h + 'h ago';
        var d = Math.floor(h / 24);
        if (d === 1) return 'yesterday';
        if (d < 7) return d + 'd ago';
        var w = Math.floor(d / 7);
        if (w < 5) return w + 'w ago';
        return Math.floor(d / 30) + 'mo ago';
      }
      function tick() {
        var now = Date.now();
        document.querySelectorAll('time[data-rel]').forEach(function (el) {
          var t = Date.parse(el.getAttribute('datetime'));
          if (!isNaN(t)) el.textContent = fmt(now - t);
        });
      }
      if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', tick);
      else tick();
      setInterval(tick, 60000);
    })();
