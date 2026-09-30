// /admin/ portfolio board — the operator's strategic view of every project.
// Renders only when the sessionStorage unlock flag is set (admin.js bounces
// otherwise). Public-safe editorial only (public repo behind a curtain).
// XSS-safe: textContent / DOM nodes, never innerHTML.
(() => {
  if (sessionStorage.getItem("jc-admin") !== "1") return;

  const DEEP_DIVES = new Set(["aleph", "fantastic-leagues", "judge-tool"]);
  const STATUS_LABEL = {
    "on-track": "on track", "exploring": "exploring",
    "stalled": "stalled", "blocked": "blocked", "shipped": "shipped",
  };

  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const link = (label, href) => {
    const a = el("a", "nb-portfolio-link", label);
    a.href = href;
    if (/^https?:/.test(href)) { a.target = "_blank"; a.rel = "noopener"; }
    return a;
  };
  const labelled = (label, value) => {
    const row = el("p", "nb-portfolio-row");
    row.append(el("span", "nb-portfolio-label", label));
    row.append(document.createTextNode(" " + value));
    return row;
  };

  // One mono line of cockpit numbers: status · last activity · hours · share vs target · spend.
  const statLine = (st) => {
    const row = el("p", `nb-cockpit-stat nb-cockpit-stat--${st.status}`);
    const days = st.last_activity
      ? Math.floor((Date.now() - new Date(st.last_activity).getTime()) / 864e5) : null;
    const parts = [st.status, days == null ? "no activity" : days === 0 ? "today" : `${days}d ago`,
      `${st.hours}h / 28d`];
    if (st.target_share || st.actual_share) parts.push(`${st.actual_share}% of ${st.target_share}%`);
    if (st.spend) parts.push(st.spend >= 1000 ? `$${(st.spend / 1000).toFixed(1)}k` : `$${Math.round(st.spend)}`);
    row.textContent = parts.join(" · ");
    return row;
  };

  const render = async () => {
    const board = document.getElementById("portfolio-board");
    if (!board) return;
    let cfg, pf, cp;
    try {
      // no-store: GitHub Pages caches static assets for 10 min, but this is an
      // admin view of hand-edited data — always fetch the latest so edits to
      // portfolio.json show on the next load, not 10 minutes later.
      [cfg, pf, cp] = await Promise.all([
        fetch("/bin/projects-config.json", { cache: "no-store" }).then((r) => r.json()),
        fetch("/admin/portfolio.json", { cache: "no-store" }).then((r) => r.json()),
        fetch("/admin/cockpit.json", { cache: "no-store" }).then((r) => r.json()).catch(() => null),
      ]);
    } catch (e) {
      board.replaceChildren(
        el("p", "nb-portfolio-error", "couldn't load the portfolio data."));
      return;
    }
    const notes = Object.fromEntries(pf.projects.map((p) => [p.slug, p]));
    const live = Object.fromEntries(((cp && cp.projects) || []).map((p) => [p.slug, p]));
    const cards = [];
    const counts = {};
    for (const proj of cfg.projects) {
      const pm = notes[proj.slug];
      if (!pm) continue;
      counts[pm.pm_status] = (counts[pm.pm_status] || 0) + 1;
      const card = el("article", "nb-portfolio-card");

      const head = el("div", "nb-portfolio-head");
      const name = el("h3", "nb-portfolio-name");
      if (proj.url) name.append(link(proj.name || proj.slug, proj.url));
      else name.textContent = proj.name || proj.slug;
      head.append(name);
      head.append(el("span",
        `nb-portfolio-badge nb-portfolio-badge--${pm.pm_status}`,
        STATUS_LABEL[pm.pm_status] || pm.pm_status));
      // Lifecycle stage chip (idea → building → shipping → back-burner → done).
      if (pm.stage)
        head.append(el("span", `nb-portfolio-stage nb-portfolio-stage--${pm.stage}`, pm.stage));
      card.append(head);

      const st = live[proj.slug];
      if (st) card.append(statLine(st));

      card.append(labelled("bet", pm.bet));
      if (proj.next_up) card.append(labelled("next", proj.next_up));
      card.append(labelled("notes", pm.notes));

      const links = el("div", "nb-portfolio-links");
      const repo = (proj.shipping_repos && proj.shipping_repos[0]) || proj.repo;
      if (repo) links.append(link("repo", `https://github.com/${repo}`));
      if (DEEP_DIVES.has(proj.slug))
        links.append(link("deep-dive", `/projects/${proj.slug}/`));
      if (links.childNodes.length) card.append(links);

      cards.push(card);
    }
    board.replaceChildren(...cards);

    // At-a-glance status summary strip.
    const summary = document.getElementById("portfolio-summary");
    if (summary) {
      const order = ["on-track", "exploring", "stalled", "blocked", "shipped"];
      const parts = [`${cards.length} projects`];
      for (const s of order) {
        if (counts[s]) parts.push(`${counts[s]} ${STATUS_LABEL[s]}`);
      }
      summary.textContent = parts.join("  ·  ");
    }
  };

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", render);
  else render();
})();
