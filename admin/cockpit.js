// /admin/ cockpit sections — decide, portfolio, time, money estimate — rendered from
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
    const reds = d.projects.filter((p) => p.rag === "red").length;
    const ambers = d.projects.filter((p) => p.rag === "amber").length;
    meta.textContent =
      `${d.decisions.length} decision${d.decisions.length === 1 ? "" : "s"} · ` +
      (reds || ambers ? `${reds} red, ${ambers} amber · ` : "") +
      `${d.total_hours}h wall-clock · ${money(d.money.claude_total)} API-equivalent (not a bill) · ` +
      `last ${d.window_days} days · snapshot ${ago(d.generated)}` +
      (h > STALE_SNAPSHOT_H ? " — the Mac hasn't pushed since" : "");
    put("cockpit-meta", meta);
  };

  // Decision kinds in words — the letters meant nothing to a reader.
  const KIND = { G: "scope creep", A: "time allocation", B: "keep / park / kill", C: "unregistered work", D: "money" };

  // Open a collapsed section before jumping into it (the goals link from /01).
  const openSection = (key) => {
    const sec = document.querySelector(`details.nb-cockpit-sec[data-sec="${key}"]`);
    if (sec && !sec.open) sec.open = true;
  };

  const renderDecide = (d) => {
    if (!d.decisions.length) {
      put("cockpit-decide", el("p", "nb-cockpit-empty", "Nothing waiting — you're on plan."));
      return;
    }
    const list = el("ol", "nb-cockpit-decisions");
    for (const x of d.decisions) {
      const sev = x.severity === "high" ? "high" : "medium";
      const li = el("li", `nb-cockpit-decision nb-cockpit-decision--${sev}`);
      const body = el("div", "nb-cockpit-decision-body");
      const title = el("p", "nb-cockpit-decision-title");
      title.append(el("span", "nb-cockpit-kind", `${KIND[x.kind] || x.kind} · ${sev}`), document.createTextNode(x.title));
      body.append(title);
      if (x.detail) body.append(el("p", "nb-cockpit-decision-detail", x.detail));
      const act = el("p", "nb-cockpit-decision-actions");
      if (x.kind === "G") {
        const a = el("a", null, "review goals →");
        a.href = `#goals-${x.target}`;
        a.addEventListener("click", () => openSection("goals"));
        act.append(a, document.createTextNode(" · or accept it in the local cockpit"));
      } else {
        act.textContent = x.actions.map((a) => a.replace(/_/g, " ")).join(" · ") + " — decide in the local cockpit";
      }
      body.append(act);
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
      `${d.total_hours}h wall-clock · ${d.session_hours} session-hours (overlaps counted twice)`);
    put("cockpit-time", note, table);
  };

  const renderMoney = (d) => {
    const list = el("div", "nb-cockpit-money");
    const line = (label, value, cls) => {
      const r = el("div", "nb-cockpit-money-row" + (cls ? " " + cls : ""));
      r.append(el("span", null, label), el("span", "nb-cockpit-money-v", value));
      return r;
    };
    // real revenue + costs are the ledger above (admin/money.js); this is the estimate
    list.append(line(`Claude, API-equivalent — not a bill (${d.window_days}d)`, money(d.money.claude_total), "nb-cockpit-money-row--total"));
    if (d.money.fixed_total) list.append(line("fixed costs in the cockpit config / month", money(d.money.fixed_total)));
    for (const p of [...d.projects].filter((p) => p.spend > 0).sort((a, b) => b.spend - a.spend)) {
      const rate = p.hours ? ` · $${Math.round(p.spend / p.hours)}/h` : "";
      list.append(line(p.name, money(p.spend) + rate));
    }
    const note = el("p", "nb-cockpit-note", "API-equivalent is what the work would cost on the API, not your bill.");
    put("cockpit-money", list, note);
  };

  const idleDays = (iso) => (iso ? Math.floor((Date.now() - new Date(iso).getTime()) / 864e5) : null);
  const DEEP_DIVES = new Set(["aleph", "fantastic-leagues", "judge-tool"]);

  // Which portfolio groups the viewer collapsed — convenience only, may throw.
  const GROUPS_KEY = "jc-cockpit-groups-closed";
  let closedGroups = [];
  try { closedGroups = JSON.parse(localStorage.getItem(GROUPS_KEY) || "[]"); } catch (e) { closedGroups = []; }
  const saveGroups = () => {
    try { localStorage.setItem(GROUPS_KEY, JSON.stringify(closedGroups)); } catch (e) { /* convenience only */ }
  };

  // ▲/▼ against a week ago. upIsGood says which direction is green.
  const trend = (cur, prev, upIsGood) => {
    if (cur == null || prev == null) return el("span", "nb-trend nb-trend--flat", " –");
    const delta = Math.round(cur - prev);
    if (!delta) return el("span", "nb-trend nb-trend--flat", " –");
    const good = (delta > 0) === upIsGood;
    const t = el("span", `nb-trend nb-trend--${good ? "good" : "bad"}`, ` ${delta > 0 ? "▲" : "▼"} ${Math.abs(delta)}`);
    t.title = "change vs a week ago (points)";
    return t;
  };
  const td = (label, ...kids) => {
    const c = el("td");
    c.dataset.l = label;
    c.append(...kids);
    return c;
  };
  const sub = (text) => el("span", "nb-cockpit-sub", text);

  // /02 — every project: active first, then parked; each row expands to its notes.
  const PT_MONTH = () => new Date().toLocaleDateString("en-CA", { timeZone: "America/Los_Angeles" }).slice(0, 7);
  const netThisMonth = (ledger, slug) => {
    const m = (((ledger.projects || {})[slug] || {}).months || {})[PT_MONTH()];
    if (!m) return null;
    const sum = (xs) => (xs || []).reduce((a, x) => a + x.usd, 0);
    return sum(m.revenue) - sum(m.costs);
  };

  const renderTable = (d, cfg, pf, ledger) => {
    const conf = Object.fromEntries((cfg.projects || []).map((p) => [p.slug, p]));
    const notes = Object.fromEntries((pf.projects || []).map((p) => [p.slug, p]));
    // worst first — the table answers "what needs me" — then most hours, then most recent
    const RAG_RANK = { red: 0, amber: 1, green: 2, parked: 3, none: 4 };
    const byActivity = (a, b) => (RAG_RANK[a.rag || "none"] - RAG_RANK[b.rag || "none"]) || b.hours - a.hours ||
      (idleDays(a.last_activity) ?? 1e9) - (idleDays(b.last_activity) ?? 1e9);
    const groups = [
      ["active", d.projects.filter((p) => p.status === "active").sort(byActivity)],
      ["parked", d.projects.filter((p) => p.status !== "active").sort(byActivity)],
    ];

    const table = el("table", "nb-cockpit-table");
    const head = el("thead");
    const cols = el("tr");
    for (const [h, small, tip] of [
      ["project", "status · last touched", "Dot: red / amber / green — reason underneath"],
      ["on-goal", "prompts serving a goal", "Share of typed prompts that served a goal · how much of it major"],
      ["creep", "new asks off-goal", "Asks for new capability that served no goal"],
      ["time", "share / target", "Your hours here as a share of all project hours, vs the share you intended"],
      ["budget", "API-equivalent · $/h", "What the Claude usage would cost on the API — not a bill"],
    ]) {
      const th = el("th", null, h);
      th.title = tip;
      th.append(el("small", null, small));
      cols.append(th);
    }
    head.append(cols);
    table.append(head);

    for (const [group, rows] of groups) {
      if (!rows.length) continue;
      const body = el("tbody", `nb-cockpit-group nb-cockpit-group--${group}`);
      const gRow = el("tr", "nb-cockpit-grouprow");
      const gCell = el("td");
      gCell.colSpan = 5;
      const gBtn = el("button", "nb-cockpit-grouptoggle");
      gBtn.type = "button";
      const label = group === "active" ? "active" : "parked";
      const isOpen = () => !closedGroups.includes(group);
      const paint = () => {
        gBtn.textContent = `${isOpen() ? "▾" : "▸"} ${label} · ${rows.length}`;
        gBtn.setAttribute("aria-expanded", String(isOpen()));
        body.classList.toggle("is-collapsed", !isOpen());
      };
      gBtn.addEventListener("click", () => {
        closedGroups = isOpen() ? [...closedGroups, group] : closedGroups.filter((g) => g !== group);
        saveGroups();
        paint();
      });
      gCell.append(gBtn);
      gRow.append(gCell);
      body.append(gRow);

      for (const p of rows) {
        const a = p.alignment || {};
        const rag = p.rag || "none";  // an older snapshot has no rag — render a neutral dot
        const tr = el("tr", `nb-cockpit-row nb-cockpit-row--${p.status}`);

        const name = el("td", "nb-cockpit-proj");
        name.dataset.l = "";
        const dot = el("span", `nb-rag-dot nb-rag-dot--${rag}`);
        dot.title = rag;
        const idle = idleDays(p.last_activity);
        name.append(dot, el("strong", null, p.name),
          el("span", "nb-cockpit-pm", ` · ${p.status} · ${idle == null ? "no activity" : idle === 0 ? "today" : `${idle}d`}`));
        const reasons = p.rag_reasons || [];
        if (rag !== "none" && rag !== "parked")
          name.append(sub(reasons.length ? `${rag}: ${reasons.join("; ")}` : rag));
        const more = el("button", "nb-cockpit-more", "details ▸");
        more.type = "button";
        name.append(more);
        tr.append(name);

        const goalsN = (p.goals || []).length;
        const on = a.on_goal_pct;
        tr.append(td("on-goal",
          document.createTextNode(on == null ? (goalsN ? "—" : "no goals") : `${on}%`),
          trend(on, p.prev && p.prev.on_goal_pct, true),
          ...(on != null && a.on_goal_major_pct != null ? [sub(`${a.on_goal_major_pct}% major`)] : [])));
        tr.append(td("creep",
          document.createTextNode(a.creep_pct == null ? "—" : `${a.creep_pct}%`),
          trend(a.creep_pct, p.prev && p.prev.creep_pct, false),
          ...(a.new_scope ? [sub(`${a.creep} of ${a.new_scope}`)] : [])));
        tr.append(td("time",
          document.createTextNode(`${p.actual_share}% / ${p.target_share}%`),
          trend(p.actual_share, p.prev && p.prev.share, true), sub(`${p.hours}h`)));
        const net = netThisMonth(ledger, p.slug);
        tr.append(td("budget", document.createTextNode(
          p.spend ? `${money(p.spend)} · $${Math.round(p.spend / Math.max(p.hours, 0.1))}/h` : "—"),
          ...(net == null ? [] : [sub(`net ${net < 0 ? "−" : ""}${money(Math.abs(net))} this month`)])));
        body.append(tr);

        // details row: the old /04 project notes plus the PM fields
        const det = el("tr", "nb-cockpit-detail");
        det.hidden = true;
        const dc = el("td");
        dc.colSpan = 5;
        const dl = el("dl", "nb-cockpit-dl");
        const pm = notes[p.slug] || {}, c = conf[p.slug] || {};
        const item = (k, v, unsetOk) => {
          dl.append(el("dt", null, k));
          const dd = el("dd", v ? null : unsetOk ? "nb-cockpit-dim" : "nb-cockpit-unset", v || (unsetOk ? "—" : "not set"));
          dl.append(dd);
          return dd;
        };
        item("next", c.next_up, true);
        item("bet", pm.bet, true);
        item("notes", pm.notes, true);
        const st = item("stage", "", true);
        if (pm.stage) st.replaceChildren(el("span", `nb-portfolio-stage nb-portfolio-stage--${pm.stage}`, pm.stage));
        item("health", pm.pm_status ? pm.pm_status.replace("-", " ") : "", true);
        item("next decision", p.next_decision);
        item("stop criteria", p.stop_criteria);
        item("review by", p.review_by);
        const repo = (c.shipping_repos && c.shipping_repos[0]) || c.repo;
        const links = item("links", "", true);
        const ls = [];
        if (repo) ls.push(["repo", `https://github.com/${repo}`]);
        if (DEEP_DIVES.has(p.slug)) ls.push(["deep-dive", `/projects/${p.slug}/`]);
        if (c.url) ls.push(["site", c.url]);
        if (ls.length) {
          links.className = "";
          links.replaceChildren(...ls.flatMap(([t, href], i) => {
            const l = el("a", null, t);
            l.href = href;
            if (/^https?:/.test(href)) { l.target = "_blank"; l.rel = "noopener"; }
            return i ? [document.createTextNode(" · "), l] : [l];
          }));
        }
        dc.append(dl);
        det.append(dc);
        body.append(det);
        more.addEventListener("click", () => {
          det.hidden = !det.hidden;
          more.textContent = det.hidden ? "details ▸" : "details ▾";
        });
      }
      paint();
      table.append(body);
    }
    put("cockpit-table", table);
  };

  const render = async () => {
    let d, cfg, pf, ledger;
    try {
      // no-store: Pages caches for 10 min; the snapshot's own age is shown instead.
      [d, cfg, pf, ledger] = await Promise.all([
        window.jcAdminJSON("/admin/cockpit.json"),
        window.jcAdminJSON("/bin/projects-config.json").catch(() => ({})),
        window.jcAdminJSON("/admin/portfolio.json").catch(() => ({})),
        window.jcAdminJSON("/admin/money.json").catch(() => ({})),
      ]);
    } catch (e) {
      put("cockpit-meta", el("p", "nb-portfolio-error", "couldn't load the cockpit snapshot."));
      return;
    }
    renderMeta(d);
    renderDecide(d);
    renderTable(d, cfg, pf, ledger);
    renderTime(d);
    renderMoney(d);
  };

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", render);
  else render();
})();
