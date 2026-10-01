// /admin/ money ledger (/06) — revenue and costs per project per month, entered by
// hand and committed to admin/money.json through the shared GitHub Contents helper
// (admin/gh.js). The file is PUBLIC (readable without the curtain), so revenue is a
// number plus a type from a closed vocab — there is no free-text field where a
// client name could land — and costs carry only a short vendor name.
// XSS-safe: textContent / DOM nodes, never innerHTML.
(() => {
  if (sessionStorage.getItem("jc-admin") !== "1") return;

  const PATH = "admin/money.json";
  const REVENUE_TYPES = ["client work", "subscription", "one-off", "other"];
  const MONTHS_SHOWN = 4;          // this month + the 3 before it
  const MAX_USD = 10000000;
  const gh = window.jcGh;

  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const usd = (n) => `${n < 0 ? "−" : ""}$${Math.abs(n).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
  const thisMonth = () => new Date().toLocaleDateString("en-CA", { timeZone: "America/Los_Angeles" }).slice(0, 7);
  const monthsBack = (n) => {
    const [y, m] = thisMonth().split("-").map(Number);
    return Array.from({ length: n }, (_, i) => {
      const d = new Date(Date.UTC(y, m - 1 - i, 1));
      return d.toISOString().slice(0, 7);
    });
  };
  const parseUsd = (raw) => {
    const n = Math.round(Number(String(raw).replace(/[$,\s]/g, "")) * 100) / 100;
    return Number.isFinite(n) && n > 0 && n <= MAX_USD ? n : null;
  };

  let doc = { projects: {} };
  let snap = { projects: [] };
  let ops = [];
  let status = "";
  const editing = new Map();       // slug -> month being edited

  // ---- pure edits, replayed onto a fresh copy on save ----
  const applyOp = (d, op) => {
    d.projects ||= {};
    const entry = (d.projects[op.slug] ||= { months: {} });
    const m = (entry.months[op.month] ||= {});
    if (op.kind === "rev") (m.revenue ||= []).push({ type: op.type, usd: op.usd });
    else if (op.kind === "cost") (m.costs ||= []).push({ vendor: op.vendor, usd: op.usd });
    else if (op.kind === "rm") {
      const list = m[op.list] || [];
      const i = list.findIndex((x) => x.usd === op.usd && (op.list === "revenue" ? x.type === op.label : x.vendor === op.label));
      if (i >= 0) list.splice(i, 1);
      if (!list.length) delete m[op.list];
    }
    if (!Object.keys(m).length) delete entry.months[op.month];
    if (!Object.keys(entry.months).length) delete d.projects[op.slug];
  };
  const view = () => {
    const v = JSON.parse(JSON.stringify(doc));
    ops.forEach((op) => applyOp(v, op));
    return v;
  };
  const totals = (m) => {
    const revenue = (m && m.revenue || []).reduce((a, x) => a + x.usd, 0);
    const costs = (m && m.costs || []).reduce((a, x) => a + x.usd, 0);
    return { revenue, costs, net: revenue - costs };
  };

  // ---- rendering ----
  const amountInput = (label) => {
    const i = el("input");
    i.inputMode = "decimal";
    i.placeholder = "$";
    i.setAttribute("aria-label", label);
    i.maxLength = 12;
    return i;
  };

  const editor = (p, months) => {
    const slug = p.slug;
    const month = editing.get(slug);
    const box = el("div", "nb-money-editor");
    const pick = el("input");
    pick.type = "month";
    pick.value = month;
    pick.setAttribute("aria-label", "month");
    pick.addEventListener("change", () => { if (pick.value) { editing.set(slug, pick.value); render(); } });
    box.append(pick);

    const m = months[month] || {};
    const list = el("ul", "nb-money-entries");
    for (const [kind, label] of [["revenue", "type"], ["costs", "vendor"]]) {
      for (const x of m[kind] || []) {
        const li = el("li", null, `${kind === "revenue" ? "+" : "−"} ${usd(x.usd)} · ${x[label]}`);
        const rm = el("button", "nb-cockpit-goal-rm", "remove");
        rm.type = "button";
        rm.addEventListener("click", () => {
          ops.push({ kind: "rm", slug, month, list: kind, label: x[label], usd: x.usd });
          render();
        });
        li.append(rm);
        list.append(li);
      }
    }
    if (!list.childNodes.length) list.append(el("li", "nb-cockpit-note", `Nothing entered for ${month}.`));
    box.append(list);

    const revForm = el("form", "nb-money-form");
    const type = el("select");
    type.setAttribute("aria-label", "revenue type");
    for (const t of REVENUE_TYPES) { const o = el("option", null, t); o.value = t; type.append(o); }
    const revAmt = amountInput("revenue amount");
    const addRev = el("button", null, "add revenue");
    addRev.type = "submit";
    revForm.append(type, revAmt, addRev);
    revForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const n = parseUsd(revAmt.value);
      if (!n) { status = "Enter an amount above $0."; render(); return; }
      ops.push({ kind: "rev", slug, month, type: type.value, usd: n });
      status = "";
      render();
    });

    const costForm = el("form", "nb-money-form");
    const vendor = el("input");
    vendor.placeholder = "vendor — e.g. Vercel (public, no client names)";
    vendor.maxLength = 40;
    vendor.setAttribute("aria-label", "vendor");
    const costAmt = amountInput("cost amount");
    const addCost = el("button", null, "add cost");
    addCost.type = "submit";
    costForm.append(vendor, costAmt, addCost);
    costForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const v = vendor.value.trim(), n = parseUsd(costAmt.value);
      if (!v || !n) { status = "A cost needs a vendor and an amount above $0."; render(); return; }
      ops.push({ kind: "cost", slug, month, vendor: v, usd: n });
      status = "";
      render();
    });
    box.append(revForm, costForm);
    return box;
  };

  const render = () => {
    const host = document.getElementById("money-ledger");
    if (!host) return;
    const v = view();
    const shown = monthsBack(MONTHS_SHOWN);
    const now = shown[0];
    const nodes = [];

    // this month across every project
    const all = Object.values(v.projects || {}).map((e) => totals(e.months[now]));
    const sum = all.reduce((a, t) => ({ revenue: a.revenue + t.revenue, costs: a.costs + t.costs, net: a.net + t.net }),
      { revenue: 0, costs: 0, net: 0 });
    const head = el("p", "nb-money-total");
    head.textContent = sum.revenue || sum.costs
      ? `${now}: revenue ${usd(sum.revenue)} · costs ${usd(sum.costs)} · net ${usd(sum.net)}`
      : `${now}: no revenue or costs entered yet`;
    nodes.push(head);

    const hours = Object.fromEntries(snap.projects.map((p) => [p.slug, p.hours]));
    const projects = [...snap.projects].sort((a, b) => (a.status === "active" ? 0 : 1) - (b.status === "active" ? 0 : 1));
    for (const p of projects) {
      const months = ((v.projects || {})[p.slug] || {}).months || {};
      const has = shown.some((m) => months[m]);
      if (!has && !editing.has(p.slug)) continue;
      const box = el("div", "nb-money-project");
      const h = el("p", "nb-cockpit-goalset-head");
      h.append(el("strong", null, p.name));
      const toggle = el("button", "nb-cockpit-goal-toggle", editing.has(p.slug) ? "done editing" : "edit");
      toggle.type = "button";
      toggle.addEventListener("click", () => {
        if (editing.has(p.slug)) editing.delete(p.slug); else editing.set(p.slug, now);
        status = "";
        render();
      });
      h.append(toggle);
      box.append(h);

      const table = el("table", "nb-money-table");
      const tr0 = el("tr");
      for (const c of ["month", "revenue", "costs", "net"]) tr0.append(el("th", null, c));
      table.append(tr0);
      for (const m of shown) {
        if (!months[m]) continue;
        const t = totals(months[m]);
        const tr = el("tr");
        tr.append(el("td", null, m), el("td", null, usd(t.revenue)), el("td", null, usd(t.costs)),
          el("td", t.net < 0 ? "nb-money-neg" : null, usd(t.net)));
        table.append(tr);
      }
      if (table.rows.length > 1) box.append(table);
      const cur = totals(months[now]);
      if ((cur.revenue || cur.costs) && hours[p.slug])
        box.append(el("p", "nb-cockpit-note",
          `≈ ${usd(cur.net / hours[p.slug])}/h this month (net ÷ last 28 days' ${hours[p.slug]}h — rough, the windows don't line up)`));
      if (editing.has(p.slug)) box.append(editor(p, months));
      nodes.push(box);
    }

    // every project is reachable: pick one to start entering money for it
    const pickRow = el("p", "nb-money-pick");
    const sel = el("select");
    sel.setAttribute("aria-label", "add money for a project");
    const first = el("option", null, "add revenue / costs for…");
    first.value = "";
    sel.append(first);
    for (const p of projects) {
      if (editing.has(p.slug)) continue;
      const o = el("option", null, p.name);
      o.value = p.slug;
      sel.append(o);
    }
    sel.addEventListener("change", () => { if (sel.value) { editing.set(sel.value, now); status = ""; render(); } });
    pickRow.append(sel);
    nodes.push(pickRow);

    if (ops.length || editing.size) {
      const bar = el("div", "nb-cockpit-goal-bar");
      if (!gh.token()) {
        const tok = el("input", "nb-cockpit-goal-token");
        tok.type = "password";
        tok.autocomplete = "off";
        tok.placeholder = "GitHub token (Contents read/write) — kept in this tab only";
        tok.id = "money-token";
        bar.append(tok);
      }
      const saveBtn = el("button", null, ops.length ? `save ${ops.length} change${ops.length === 1 ? "" : "s"}` : "save");
      saveBtn.type = "button";
      saveBtn.disabled = !ops.length;
      saveBtn.addEventListener("click", async () => {
        const t = gh.token() || (document.getElementById("money-token") || {}).value?.trim();
        if (!t) { status = "Paste a token first."; render(); return; }
        gh.setToken(t);
        status = "saving…"; render();
        try {
          doc = await gh.save(PATH, (fresh) => ops.forEach((op) => applyOp(fresh, op)),
            "chore(admin): update money ledger from /admin/");
          ops = [];
          status = "Saved — live on the next page load (Pages caches up to 10 min).";
        } catch (err) {
          status = err.message;
        }
        render();
      });
      bar.append(saveBtn);
      if (ops.length) {
        const discard = el("button", null, "discard");
        discard.type = "button";
        discard.addEventListener("click", () => { ops = []; status = ""; render(); });
        bar.append(discard);
      }
      if (status) bar.append(el("span", "nb-cockpit-note", status));
      nodes.push(bar);
    }
    host.replaceChildren(...nodes);
  };

  const load = async () => {
    try {
      [doc, snap] = await Promise.all([
        window.jcAdminJSON("/admin/money.json").catch(() => ({ projects: {} })),
        window.jcAdminJSON("/admin/cockpit.json"),
      ]);
      doc.projects ||= {};
    } catch (e) {
      const host = document.getElementById("money-ledger");
      if (host) host.replaceChildren(el("p", "nb-portfolio-error", "couldn't load the money ledger."));
      return;
    }
    render();
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load);
  else load();
})();
