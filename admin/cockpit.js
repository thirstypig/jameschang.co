// /admin/ cockpit sections — decide, time, money, ideas — rendered from
// /admin/cockpit.json, a snapshot the private cockpit (~/Projects/cockpit)
// pushes from James's Mac via `python3 -m cockpit.publish`. The transcripts it
// is computed from live only on that Mac, so this page is read-only: it shows
// the latest snapshot and says how old it is.
// Published as-is by decision (2026-09-30): hours, spend, folder names, ideas.
// XSS-safe: textContent / DOM nodes, never innerHTML.
(() => {
  if (sessionStorage.getItem("jc-admin") !== "1") return;

  const STALE_SNAPSHOT_H = 26; // the publisher runs every few hours; a day+ means the Mac stopped pushing

  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const money = (usd) => (usd >= 1000 ? `$${(usd / 1000).toFixed(1)}k` : `$${Math.round(usd)}`);
  const ago = (iso) => {
    const h = (Date.now() - new Date(iso).getTime()) / 36e5;
    if (h < 1) return `${Math.max(1, Math.round(h * 60))}m ago`;
    if (h < 48) return `${Math.round(h)}h ago`;
    return `${Math.round(h / 24)}d ago`;
  };
  const put = (id, ...nodes) => {
    const host = document.getElementById(id);
    if (host) host.replaceChildren(...nodes);
  };

  const renderMeta = (d) => {
    const h = (Date.now() - new Date(d.generated).getTime()) / 36e5;
    const meta = el("p", "nb-cockpit-meta" + (h > STALE_SNAPSHOT_H ? " nb-cockpit-meta--stale" : ""));
    meta.textContent =
      `${d.decisions.length} decision${d.decisions.length === 1 ? "" : "s"} · ` +
      `${d.total_hours}h wall-clock · ${money(d.money.claude_total)} API-eq · ` +
      `last ${d.window_days} days · snapshot ${ago(d.generated)}` +
      (h > STALE_SNAPSHOT_H ? " — the Mac hasn't pushed since" : "");
    put("cockpit-meta", meta);
  };

  const renderDecide = (d) => {
    if (!d.decisions.length) {
      put("cockpit-decide", el("p", "nb-cockpit-empty", "Nothing waiting — you're on plan."));
      return;
    }
    const list = el("ol", "nb-cockpit-decisions");
    for (const x of d.decisions) {
      const li = el("li", "nb-cockpit-decision");
      li.append(el("span", "nb-cockpit-kind", x.kind));
      const body = el("div", "nb-cockpit-decision-body");
      body.append(el("p", "nb-cockpit-decision-title", x.title));
      if (x.detail) body.append(el("p", "nb-cockpit-decision-detail", x.detail));
      body.append(el("p", "nb-cockpit-decision-actions",
        x.actions.map((a) => a.replace(/_/g, " ")).join(" · ") + " — decide in the local cockpit"));
      li.append(body);
      list.append(li);
    }
    put("cockpit-decide", list);
  };

  const renderTime = (d) => {
    const rows = d.allocation.filter((a) => a.target > 0 || a.actual > 0);
    const table = el("div", "nb-cockpit-alloc");
    for (const a of rows) {
      const row = el("div", "nb-cockpit-alloc-row");
      row.append(el("span", "nb-cockpit-alloc-name", a.slug === "_other" ? "other" : a.name));
      const bars = el("span", "nb-cockpit-bars");
      const target = el("span", "nb-cockpit-bar nb-cockpit-bar--target");
      target.style.width = `${Math.min(100, a.target)}%`;
      const actual = el("span", "nb-cockpit-bar nb-cockpit-bar--actual");
      actual.style.width = `${Math.min(100, a.actual)}%`;
      bars.append(target, actual);
      row.append(bars);
      row.append(el("span", "nb-cockpit-alloc-num", `${a.actual}% / ${a.target}%`));
      table.append(row);
    }
    const note = el("p", "nb-cockpit-note",
      `${d.total_hours}h wall-clock · ${d.session_hours} session-hours · grey = target, colored = actual`);
    put("cockpit-time", note, table);
  };

  const renderMoney = (d) => {
    const list = el("div", "nb-cockpit-money");
    const line = (label, value, cls) => {
      const r = el("div", "nb-cockpit-money-row" + (cls ? " " + cls : ""));
      r.append(el("span", null, label), el("span", "nb-cockpit-money-v", value));
      return r;
    };
    list.append(line(`Claude, API-equivalent (${d.window_days}d)`, money(d.money.claude_total), "nb-cockpit-money-row--total"));
    list.append(line("fixed costs / month", d.money.fixed_total ? money(d.money.fixed_total) : "not entered"));
    for (const p of [...d.projects].filter((p) => p.spend > 0).sort((a, b) => b.spend - a.spend)) {
      const rate = p.hours ? ` · $${Math.round(p.spend / p.hours)}/h` : "";
      list.append(line(p.name, money(p.spend) + rate));
    }
    const note = el("p", "nb-cockpit-note", "API-equivalent is what the work would cost on the API, not your bill.");
    put("cockpit-money", list, note);
  };

  // RAG thresholds for the portfolio table — mirror the cockpit's own rules.
  const CREEP_RED = 50, CREEP_AMBER = 25, SHARE_GAP_AMBER = 10;
  const idleDays = (iso) => (iso ? Math.floor((Date.now() - new Date(iso).getTime()) / 864e5) : null);
  const cell = (text, cls) => el("td", cls, text);

  // /02 — one row per project: who it is, then scope, time and budget side by side.
  const renderTable = (d, cfg, pf) => {
    const next = Object.fromEntries((cfg.projects || []).map((p) => [p.slug, p.next_up || ""]));
    const pm = Object.fromEntries((pf.projects || []).map((p) => [p.slug, p.pm_status]));
    const order = { active: 0, idea: 1, parked: 2, killed: 3 };
    const rows = [...d.projects].sort((a, b) =>
      (order[a.status] ?? 9) - (order[b.status] ?? 9) || b.hours - a.hours ||
      (idleDays(a.last_activity) ?? 1e9) - (idleDays(b.last_activity) ?? 1e9));

    const table = el("table", "nb-cockpit-table");
    const head = el("thead");
    const groups = el("tr", "nb-cockpit-groups");
    for (const [label, span] of [["", 1], ["scope", 1], ["time", 2], ["budget", 1]]) {
      const th = el("th", null, label);
      th.colSpan = span;
      groups.append(th);
    }
    const cols = el("tr");
    for (const h of ["project", "goals · creep", "28d · share / target", "last", "spend · $/h"])
      cols.append(el("th", null, h));
    head.append(groups, cols);
    const body = el("tbody");

    for (const p of rows) {
      const tr = el("tr", `nb-cockpit-row nb-cockpit-row--${p.status}`);
      const name = el("td", "nb-cockpit-proj");
      name.append(el("span", `nb-cockpit-status nb-cockpit-status--${p.status}`, p.status), el("span", null, " " + p.name));
      if (pm[p.slug]) name.append(el("span", "nb-cockpit-pm", ` · ${pm[p.slug].replace("-", " ")}`));
      tr.append(name);

      const a = p.alignment || {};
      const goalsN = (p.goals || []).length;
      let scope = goalsN ? `${goalsN} goal${goalsN === 1 ? "" : "s"}` : "no goals";
      let scopeCls = goalsN ? "" : "nb-rag-amber";
      if (goalsN && a.new_scope) {
        scope += ` · ${a.creep_pct}% creep (${a.creep}/${a.new_scope})`;
        scopeCls = a.creep_pct >= CREEP_RED ? "nb-rag-red" : a.creep_pct >= CREEP_AMBER ? "nb-rag-amber" : "nb-rag-green";
      }
      if (p.status !== "active" && !goalsN) scopeCls = "";
      tr.append(cell(scope, scopeCls));

      const gap = Math.abs((p.actual_share || 0) - (p.target_share || 0));
      tr.append(cell(`${p.hours}h · ${p.actual_share}% / ${p.target_share}%`, gap >= SHARE_GAP_AMBER ? "nb-rag-amber" : ""));
      const idle = idleDays(p.last_activity);
      tr.append(cell(idle == null ? "—" : idle === 0 ? "today" : `${idle}d`));
      tr.append(cell(p.spend ? `${money(p.spend)} · $${Math.round(p.spend / Math.max(p.hours, 0.1))}/h` : "—"));
      body.append(tr);
      // next-up on its own full-width line: prose doesn't fit a 2/3-width column
      if (next[p.slug]) {
        const sub = el("tr", `nb-cockpit-subrow nb-cockpit-row--${p.status}`);
        const td = el("td", "nb-cockpit-next");
        td.colSpan = 5;
        td.append(el("span", "nb-portfolio-label", "next "), document.createTextNode(next[p.slug]));
        sub.append(td);
        body.append(sub);
      }
    }
    table.append(head, body);
    const legend = el("p", "nb-cockpit-note",
      `creep = new-scope asks that serve no goal · red ≥ ${CREEP_RED}% · amber ≥ ${CREEP_AMBER}% · ` +
      `time amber when share is ${SHARE_GAP_AMBER}+ pts off target · budget = Claude API-equivalent`);
    put("cockpit-table", table, legend);
  };

  const renderIdeas = (d) => {
    const nodes = [];
    for (const i of d.ideas) nodes.push(el("p", "nb-portfolio-row", i.text || String(i)));
    for (const c of d.candidates)
      nodes.push(el("p", "nb-portfolio-row", `unregistered: ${c.path} — ${c.hours}h · ${c.sessions} sessions`));
    if (!nodes.length) nodes.push(el("p", "nb-cockpit-empty", "Nothing captured, no unregistered work."));
    put("cockpit-ideas", ...nodes);
  };

  const render = async () => {
    let d, cfg, pf;
    try {
      // no-store: Pages caches for 10 min; the snapshot's own age is shown instead.
      [d, cfg, pf] = await Promise.all([
        window.jcAdminJSON("/admin/cockpit.json"),
        window.jcAdminJSON("/bin/projects-config.json").catch(() => ({})),
        window.jcAdminJSON("/admin/portfolio.json").catch(() => ({})),
      ]);
    } catch (e) {
      put("cockpit-meta", el("p", "nb-portfolio-error", "couldn't load the cockpit snapshot."));
      return;
    }
    renderMeta(d);
    renderDecide(d);
    renderTable(d, cfg, pf);
    renderTime(d);
    renderMoney(d);
    renderIdeas(d);
  };

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", render);
  else render();
})();
