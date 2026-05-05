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
