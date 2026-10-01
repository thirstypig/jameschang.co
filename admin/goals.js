// /admin/ goals panel (/03) — read AND write.
// Goals live in admin/goals.json (the source of truth; the Mac's cockpit reads it on
// every publish and scores typed prompts against it). Edits here are committed to
// that file through the shared GitHub Contents helper (admin/gh.js — token pasted
// once per tab, sessionStorage only, never logged). Prompt counts per goal come from the cockpit snapshot and
// refresh on the Mac's next publish (every 3h).
// Goal text + keywords are PUBLIC (this repo is public): no customer names.
// XSS-safe: textContent / DOM nodes, never innerHTML.
(() => {
  if (sessionStorage.getItem("jc-admin") !== "1") return;

  const PATH = "admin/goals.json";
  const gh = window.jcGh;

  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };

  let doc = { projects: {} };   // goals.json as last loaded or saved
  let snap = { projects: [] };  // cockpit.json — names, status, per-goal counts
  let ops = [];                 // unsaved edits, replayed onto a fresh doc on conflict
  let status = "";
  let editing = null;           // {slug, id} of the goal whose inline edit form is open
  const editingProjects = new Set(); // projects whose edit toggle is on (read-only otherwise)

  // Goal tiers mirror cockpit/rules.py GOAL_TIERS; a goal without one is major.
  const TIERS = ["major", "minor"];
  const tierOf = (g) => (TIERS.includes(g.tier) ? g.tier : "major");
  const tierPicker = (value) => {
    const sel = el("select", "nb-cockpit-goal-tier");
    sel.setAttribute("aria-label", "tier");
    for (const t of TIERS) {
      const o = el("option", null, t);
      o.value = t;
      if (t === value) o.selected = true;
      sel.append(o);
    }
    return sel;
  };

  // ---- pure edits (mirror cockpit/goals.py: text + ≥1 keyword, ids never reused) ----
  const today = () => new Date().toLocaleDateString("en-CA", { timeZone: "America/Los_Angeles" });
  const entryFor = (d, slug) => (d.projects[slug] ||= { seq: 0, goals: [] });
  const applyOp = (d, op) => {
    const e = entryFor(d, op.slug);
    if (op.kind === "add") {
      const seq = Math.max(e.seq || 0, ...e.goals.map((g) => +(/^g(\d+)$/.exec(g.id) || [0, 0])[1])) + 1;
      e.seq = seq;
      e.goals.push({ id: `g${seq}`, text: op.text, keywords: op.keywords, set: today(), tier: op.tier || "major" });
    } else if (op.kind === "edit") {
      // same id, so the goal keeps its prompt counts and history
      const g = e.goals.find((x) => x.id === op.id);
      if (g) { g.text = op.text; g.keywords = op.keywords; g.tier = op.tier || tierOf(g); }
    } else {
      e.goals = e.goals.filter((g) => g.id !== op.id);
    }
  };
  const parseKeywords = (raw) =>
    [...new Set(raw.split(",").map((k) => k.trim().toLowerCase()).filter(Boolean))];

  const save = async () => {
    doc = await gh.save(PATH, (fresh) => {
      fresh.projects ||= {};
      ops.forEach((op) => applyOp(fresh, op));
    }, "chore(admin): update goals from /admin/");
    ops = [];
  };

  // ---- rendering ----
  // Inline edit form for one goal: text + keywords prefilled; "done" stages an edit op.
  const editRow = (slug, g) => {
    const li = el("li", "nb-cockpit-goal-editing");
    const form = el("form", "nb-cockpit-goal-form");
    const text = el("input");
    text.value = g.text;
    text.maxLength = 160;
    text.setAttribute("aria-label", "goal");
    const kws = el("input");
    kws.value = g.keywords.join(", ");
    kws.maxLength = 300;
    kws.setAttribute("aria-label", "keywords that serve it");
    const tier = tierPicker(tierOf(g));
    const done = el("button", null, "done");
    done.type = "submit";
    const cancel = el("button", null, "cancel");
    cancel.type = "button";
    cancel.addEventListener("click", () => { editing = null; render(); });
    form.append(text, kws, tier, done, cancel);
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const t = text.value.trim(), k = parseKeywords(kws.value);
      if (!t || !k.length) { say("A goal needs text and at least one keyword."); return; }
      if (t !== g.text || k.join(",") !== g.keywords.join(",") || tier.value !== tierOf(g))
        ops.push({ kind: "edit", slug, id: g.id, text: t, keywords: k, tier: tier.value });
      editing = null;
      status = "";
      render();
    });
    li.append(form);
    setTimeout(() => text.focus(), 0);
    return li;
  };

  // Validation messages update the status line in place — a full render would
  // rebuild the forms and wipe what was typed.
  const say = (msg) => {
    status = msg;
    const line = document.getElementById("goals-status");
    if (line) line.textContent = msg; else render();
  };

  const render = () => {
    const host = document.getElementById("cockpit-goals");
    if (!host) return;
    const view = JSON.parse(JSON.stringify(doc));
    ops.forEach((op) => applyOp(view, op));
    const nodes = [];

    // Every project, active first — goals can be set for parked ones too.
    const projects = [...snap.projects].sort((a, b) => (a.status === "active" ? 0 : 1) - (b.status === "active" ? 0 : 1));
    for (const p of projects) {
      const box = el("div", `nb-cockpit-goalset nb-cockpit-goalset--${p.status}`);
      box.id = `goals-${p.slug}`;
      const a = p.alignment || {};
      const isEditing = editingProjects.has(p.slug);
      const head = el("p", "nb-cockpit-goalset-head");
      head.append(el("strong", null, p.name));
      if (p.status !== "active") head.append(el("span", "nb-cockpit-pm", ` · ${p.status}`));
      if (a.new_scope)
        head.append(el("span", "nb-cockpit-note",
          ` · ${a.creep} of ${a.new_scope} new-scope asks served no goal · ${a.total} typed prompts scored`));
      const toggle = el("button", "nb-cockpit-goal-toggle", isEditing ? "done editing" : "edit");
      toggle.type = "button";
      toggle.addEventListener("click", () => {
        if (isEditing) { editingProjects.delete(p.slug); if (editing && editing.slug === p.slug) editing = null; }
        else editingProjects.add(p.slug);
        status = "";
        render();
      });
      head.append(toggle);
      box.append(head);

      const counts = Object.fromEntries((a.goals || []).map((g) => [g.id, g.prompts]));
      const goals = [...((view.projects[p.slug] || {}).goals || [])]
        .sort((x, y) => TIERS.indexOf(tierOf(x)) - TIERS.indexOf(tierOf(y)));  // major first
      const saved = new Set(((doc.projects[p.slug] || {}).goals || []).map((g) => g.id));
      const list = el("ul", "nb-cockpit-goallist");
      for (const g of goals) {
        const li = el("li", `nb-cockpit-goal--${tierOf(g)}`);
        if (editing && editing.slug === p.slug && editing.id === g.id) {
          list.append(editRow(p.slug, g));
          continue;
        }
        // unsaved, or saved but not yet scored by the Mac
        const edited = ops.some((o) => o.kind === "edit" && o.slug === p.slug && o.id === g.id);
        const label = !saved.has(g.id) ? "new" : edited ? "edit" : g.id in counts ? String(counts[g.id]) : "—";
        const n = el("span", "nb-cockpit-goal-n", label);
        n.title = "typed prompts that served this goal, last 28 days";
        li.append(n);
        const body = el("span", "nb-cockpit-goal-body");
        body.append(el("span", "nb-cockpit-goal-text", g.text));
        if (tierOf(g) === "minor") body.append(el("span", "nb-cockpit-goal-tiertag", "minor"));
        if (isEditing) body.append(el("span", "nb-cockpit-goal-kw", g.keywords.join(", ")));
        li.append(body);
        if (isEditing) {
          const ed = el("button", "nb-cockpit-goal-ed", "edit");
          ed.type = "button";
          ed.addEventListener("click", () => { editing = { slug: p.slug, id: g.id }; status = ""; render(); });
          const rm = el("button", "nb-cockpit-goal-rm", "remove");
          rm.type = "button";
          rm.addEventListener("click", () => { ops.push({ kind: "rm", slug: p.slug, id: g.id }); render(); });
          li.append(ed, rm);
        }
        list.append(li);
      }
      if (!goals.length) list.append(el("li", "nb-cockpit-note", "No goals yet."));
      box.append(list);

      if (isEditing) {
        const form = el("form", "nb-cockpit-goal-form");
        const text = el("input");
        text.placeholder = "goal — e.g. Get 5 companies beyond the pilots active";
        text.maxLength = 160;
        const kws = el("input");
        kws.placeholder = "keywords that SERVE it, comma separated — public, no names";
        kws.maxLength = 300;
        const tier = tierPicker("major");
        const add = el("button", null, "add goal");
        add.type = "submit";
        form.append(text, kws, tier, add);
        form.addEventListener("submit", (e) => {
          e.preventDefault();
          const t = text.value.trim(), k = parseKeywords(kws.value);
          if (!t || !k.length) { say("A goal needs text and at least one keyword."); return; }
          ops.push({ kind: "add", slug: p.slug, text: t, keywords: k, tier: tier.value });
          status = "";
          render();
        });
        box.append(form);
      }
      nodes.push(box);
    }
    if (editingProjects.size) {
      nodes.push(el("p", "nb-cockpit-note",
        "Major = the point of the project; minor = worth doing, not the point. " +
        "Keywords mark prompts that serve a goal — phrase goals as what you want, not what to avoid: " +
        "a \"no more SEO\" goal keyed on \"seo\" would count SEO work as on-goal."));
    }

    // save bar
    const bar = el("div", "nb-cockpit-goal-bar");
    const token = gh.token();
    const wantsBar = ops.length || editingProjects.size;  // read-only view stays clean
    if (wantsBar && (ops.length || !token)) {
      if (!token) {
        const tok = el("input", "nb-cockpit-goal-token");
        tok.type = "password";
        tok.autocomplete = "off";
        tok.placeholder = "GitHub token (Contents read/write) — kept in this tab only";
        tok.id = "goal-token";
        bar.append(tok);
      }
      const saveBtn = el("button", null, ops.length ? `save ${ops.length} change${ops.length === 1 ? "" : "s"}` : "save");
      saveBtn.type = "button";
      saveBtn.disabled = !ops.length;
      saveBtn.addEventListener("click", async () => {
        const t = gh.token() || (document.getElementById("goal-token") || {}).value?.trim();
        if (!t) { say("Paste a token first."); return; }
        gh.setToken(t);
        status = "saving…"; render();
        try {
          await save();
          status = "Saved. Prompt counts refresh on the Mac's next publish (within 3h).";
        } catch (err) {
          status = err.message;
        }
        render();
      });
      bar.append(saveBtn);
      if (ops.length) {
        const discard = el("button", null, "discard");
        discard.type = "button";
        discard.addEventListener("click", () => { ops = []; editing = null; status = ""; render(); });
        bar.append(discard);
      }
    }
    if (token && wantsBar) {
      const forget = el("button", "nb-cockpit-goal-forget", "forget token");
      forget.type = "button";
      forget.addEventListener("click", () => { gh.forgetToken(); render(); });
      bar.append(forget);
    }
    const line = el("span", "nb-cockpit-note", status);
    line.id = "goals-status";
    bar.append(line);
    nodes.push(bar);
    host.replaceChildren(...nodes);
  };

  const load = async () => {
    try {
      [doc, snap] = await Promise.all([
        window.jcAdminJSON("/admin/goals.json"),
        window.jcAdminJSON("/admin/cockpit.json"),
      ]);
      doc.projects ||= {};
    } catch (e) {
      const host = document.getElementById("cockpit-goals");
      if (host) host.replaceChildren(el("p", "nb-portfolio-error", "couldn't load goals."));
      return;
    }
    render();
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load);
  else load();
})();
