// /admin/ ideas (/07) — capture and triage ideas, and turn unregistered work the
// cockpit noticed (hours in folders that aren't a project) into ideas. Ideas live
// in admin/ideas.json (source of truth; the Mac's cockpit reads it too) and are
// committed through the shared GitHub Contents helper (admin/gh.js).
// PUBLIC: codenames, never client names. XSS-safe: textContent / DOM nodes only.
(() => {
  if (sessionStorage.getItem("jc-admin") !== "1") return;

  const PATH = "admin/ideas.json";
  const STATUSES = ["new", "exploring", "parked", "promoted", "dropped"];
  const OPEN = new Set(["new", "exploring", "parked"]);   // shown by default; the rest fold away
  const gh = window.jcGh;

  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const today = () => new Date().toLocaleDateString("en-CA", { timeZone: "America/Los_Angeles" });

  let doc = { seq: 0, ideas: [] };
  let snap = { projects: [], candidates: [] };
  let ops = [];
  let status = "";
  let editingAll = false;          // the section's edit toggle
  let editingId = null;            // one idea's inline form

  // ---- pure edits (ids never reused, like goals) ----
  const applyOp = (d, op) => {
    d.ideas ||= [];
    if (op.kind === "add") {
      const seq = Math.max(d.seq || 0, ...d.ideas.map((i) => +(/^i(\d+)$/.exec(i.id) || [0, 0])[1])) + 1;
      d.seq = seq;
      d.ideas.push({ id: `i${seq}`, text: op.text, project: op.project, status: op.status, added: today(),
        ...(op.source ? { source: op.source } : {}) });
    } else if (op.kind === "edit") {
      const i = d.ideas.find((x) => x.id === op.id);
      if (i) Object.assign(i, { text: op.text, project: op.project, status: op.status });
    } else {
      d.ideas = d.ideas.filter((x) => x.id !== op.id);
    }
  };
  const view = () => {
    const v = JSON.parse(JSON.stringify(doc));
    ops.forEach((op) => applyOp(v, op));
    return v;
  };

  // ---- form pieces ----
  const projectPicker = (value) => {
    const sel = el("select");
    sel.setAttribute("aria-label", "project");
    const none = el("option", null, "new project / none");
    none.value = "";
    sel.append(none);
    for (const p of snap.projects) {
      const o = el("option", null, p.name);
      o.value = p.slug;
      if (p.slug === value) o.selected = true;
      sel.append(o);
    }
    return sel;
  };
  const statusPicker = (value) => {
    const sel = el("select");
    sel.setAttribute("aria-label", "status");
    for (const s of STATUSES) {
      const o = el("option", null, s);
      o.value = s;
      if (s === value) o.selected = true;
      sel.append(o);
    }
    return sel;
  };
  const ideaForm = (init, submitLabel, onSubmit, onCancel) => {
    const form = el("form", "nb-idea-form");
    const text = el("input");
    text.value = init.text || "";
    text.placeholder = "the idea — public, codenames only";
    text.maxLength = 200;
    text.setAttribute("aria-label", "idea");
    const proj = projectPicker(init.project || "");
    const st = statusPicker(init.status || "new");
    const go = el("button", null, submitLabel);
    go.type = "submit";
    form.append(text, proj, st, go);
    if (onCancel) {
      const c = el("button", null, "cancel");
      c.type = "button";
      c.addEventListener("click", onCancel);
      form.append(c);
    }
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const t = text.value.trim();
      if (!t) { say("An idea needs some text."); return; }
      onSubmit({ text: t, project: proj.value, status: st.value });
    });
    return form;
  };

  // Validation messages update the status line in place — a full render would
  // rebuild the forms and wipe what was typed.
  const say = (msg) => {
    status = msg;
    const line = document.getElementById("ideas-status");
    if (line) line.textContent = msg; else render();
  };

  const render = () => {
    const host = document.getElementById("cockpit-ideas");
    if (!host) return;
    const v = view();
    const names = Object.fromEntries(snap.projects.map((p) => [p.slug, p.name]));
    const saved = new Set((doc.ideas || []).map((i) => i.id));
    const nodes = [];

    const top = el("div", "nb-money-cta-row");
    const add = el("button", "nb-money-cta", editingAll ? "done editing" : "+ add an idea");
    add.type = "button";
    add.addEventListener("click", () => { editingAll = !editingAll; editingId = null; status = ""; render(); });
    top.append(add);
    nodes.push(top);

    if (editingAll)
      nodes.push(ideaForm({}, "add idea", (f) => { ops.push({ kind: "add", ...f }); status = ""; render(); }));

    const row = (i) => {
      if (editingId === i.id) {
        return ideaForm(i, "done", (f) => { ops.push({ kind: "edit", id: i.id, ...f }); editingId = null; render(); },
          () => { editingId = null; render(); });
      }
      const li = el("div", `nb-idea nb-idea--${i.status}`);
      li.append(el("span", `nb-idea-status nb-idea-status--${i.status}`, saved.has(i.id) ? i.status : `${i.status} · unsaved`));
      const body = el("span", "nb-idea-body");
      body.append(el("span", null, i.text));
      const meta = [i.project ? names[i.project] || i.project : "", i.source || "", i.added || ""].filter(Boolean);
      if (meta.length) body.append(el("span", "nb-cockpit-sub", meta.join(" · ")));
      li.append(body);
      if (editingAll) {
        const ed = el("button", "nb-cockpit-goal-ed", "edit");
        ed.type = "button";
        ed.addEventListener("click", () => { editingId = i.id; render(); });
        const rm = el("button", "nb-cockpit-goal-rm", "remove");
        rm.type = "button";
        rm.addEventListener("click", () => { ops.push({ kind: "rm", id: i.id }); render(); });
        li.append(ed, rm);
      }
      return li;
    };

    const open = (v.ideas || []).filter((i) => OPEN.has(i.status)).sort((a, b) => STATUSES.indexOf(a.status) - STATUSES.indexOf(b.status));
    const closed = (v.ideas || []).filter((i) => !OPEN.has(i.status));
    open.forEach((i) => nodes.push(row(i)));
    if (!open.length && !editingAll) nodes.push(el("p", "nb-cockpit-empty", "No open ideas — add one."));
    if (closed.length) {
      const fold = el("details", "nb-idea-fold");
      fold.append(el("summary", null, `${closed.length} promoted or dropped`));
      closed.forEach((i) => fold.append(row(i)));
      nodes.push(fold);
    }

    // unregistered work the cockpit noticed — one click turns it into an idea
    const taken = new Set((v.ideas || []).map((i) => i.source).filter(Boolean));
    const cands = (snap.candidates || []).filter((c) => !taken.has(`unregistered: ${c.path}`));
    if (cands.length) {
      nodes.push(el("p", "nb-cockpit-note", "unregistered work — time spent in folders that aren't a project:"));
      for (const c of cands) {
        const base = c.path.replace(/\/+$/, "").split("/").pop();
        const li = el("div", "nb-idea nb-idea--candidate");
        li.append(el("span", "nb-idea-body", `${base} — ${c.hours}h · ${c.sessions} sessions`));
        const save = el("button", "nb-cockpit-goal-ed", "→ save as idea");
        save.type = "button";
        save.addEventListener("click", () => {
          ops.push({ kind: "add", text: `Explore ${base}`, project: "", status: "new", source: `unregistered: ${c.path}` });
          render();
        });
        li.append(save);
        nodes.push(li);
      }
    }

    if (ops.length || editingAll) {
      const bar = el("div", "nb-cockpit-goal-bar");
      if (!gh.token()) {
        const tok = el("input", "nb-cockpit-goal-token");
        tok.type = "password";
        tok.autocomplete = "off";
        tok.placeholder = "GitHub token (Contents read/write) — kept in this tab only";
        tok.id = "ideas-token";
        bar.append(tok);
      }
      const saveBtn = el("button", null, ops.length ? `save ${ops.length} change${ops.length === 1 ? "" : "s"}` : "save");
      saveBtn.type = "button";
      saveBtn.disabled = !ops.length;
      saveBtn.addEventListener("click", async () => {
        const t = gh.token() || (document.getElementById("ideas-token") || {}).value?.trim();
        if (!t) { say("Paste a token first."); return; }
        gh.setToken(t);
        status = "saving…"; render();
        try {
          doc = await gh.save(PATH, (fresh) => ops.forEach((op) => applyOp(fresh, op)), "chore(admin): update ideas from /admin/");
          ops = [];
          status = "Saved.";
        } catch (err) {
          status = err.message;
        }
        render();
      });
      bar.append(saveBtn);
      if (ops.length) {
        const discard = el("button", null, "discard");
        discard.type = "button";
        discard.addEventListener("click", () => { ops = []; editingId = null; status = ""; render(); });
        bar.append(discard);
      }
      const line = el("span", "nb-cockpit-note", status);
      line.id = "ideas-status";
      bar.append(line);
      nodes.push(bar);
    }
    host.replaceChildren(...nodes);
  };

  const load = async () => {
    try {
      [doc, snap] = await Promise.all([
        window.jcAdminJSON("/admin/ideas.json").catch(() => ({ seq: 0, ideas: [] })),
        window.jcAdminJSON("/admin/cockpit.json"),
      ]);
      doc.ideas ||= [];
    } catch (e) {
      const host = document.getElementById("cockpit-ideas");
      if (host) host.replaceChildren(el("p", "nb-portfolio-error", "couldn't load ideas."));
      return;
    }
    render();
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load);
  else load();
})();
