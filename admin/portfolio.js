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

  const render = async () => {
    const board = document.getElementById("portfolio-board");
    if (!board) return;
    let cfg, pf;
    try {
      [cfg, pf] = await Promise.all([
        fetch("/bin/projects-config.json").then((r) => r.json()),
        fetch("/admin/portfolio.json").then((r) => r.json()),
      ]);
    } catch (e) {
      board.replaceChildren(
        el("p", "nb-portfolio-error", "couldn't load the portfolio data."));
      return;
    }
    const notes = Object.fromEntries(pf.projects.map((p) => [p.slug, p]));
    const cards = [];
    for (const proj of cfg.projects) {
      const pm = notes[proj.slug];
      if (!pm) continue;
      const card = el("article", "nb-portfolio-card");

      const head = el("div", "nb-portfolio-head");
      const name = el("h3", "nb-portfolio-name");
      if (proj.url) name.append(link(proj.name || proj.slug, proj.url));
      else name.textContent = proj.name || proj.slug;
      head.append(name);
      head.append(el("span",
        `nb-portfolio-badge nb-portfolio-badge--${pm.pm_status}`,
        STATUS_LABEL[pm.pm_status] || pm.pm_status));
      card.append(head);

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
  };

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", render);
  else render();
})();
