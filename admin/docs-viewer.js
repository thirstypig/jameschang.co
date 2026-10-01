// Docs board viewer for /admin/docs/. Gated by the jc-admin flag (same curtain as
// the rest of /admin/). Reads the Python-built manifest admin/docs/index.json —
// metadata + pre-rendered HTML — and displays a search + sidebar + content pane.
// Public-safe content only (public repo behind a curtain).
(() => {
  if (sessionStorage.getItem("jc-admin") !== "1") {
    window.location.replace("/");
    return;
  }

  const STATUS_ORDER = ["draft", "active", "locked", "done", "deprecated"];
  let INDEX = null;
  let currentId = null;

  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };

  const matches = (doc, q) => {
    if (!q) return true;
    const hay = `${doc.title} ${doc.id} ${doc.path}`.toLowerCase();
    return hay.includes(q);
  };

  const PINNED_ID = "DOC-PM-REVIEW"; // the cockpit — pinned on top, landing view

  const makeRow = (d) => {
    const row = el("button", "nb-docs-row");
    row.type = "button";
    if (d.id === currentId) row.classList.add("is-active");
    const t = el("span", "nb-docs-row-title", d.title);
    t.title = `${d.title} · ${d.project}`;
    row.append(t);
    if (d.status) {
      row.append(el("span", `nb-docs-badge nb-docs-badge--${d.status}`, d.status));
    }
    row.addEventListener("click", () => showDoc(d.id));
    return row;
  };

  // Which project groups are open — a per-viewer convenience, so storage may be
  // missing or throw (private window, blocked site data); the nav works without it.
  const OPEN_KEY = "jc-docs-open";
  const loadOpen = () => {
    try { return new Set(JSON.parse(localStorage.getItem(OPEN_KEY) || "[]")); }
    catch (e) { return new Set(); }
  };
  const saveOpen = (set) => {
    try { localStorage.setItem(OPEN_KEY, JSON.stringify([...set])); }
    catch (e) { /* convenience only */ }
  };
  const openGroups = loadOpen();

  const sectionRank = (key) => {
    const i = INDEX.sections.findIndex((s) => s.key === key);
    return i < 0 ? INDEX.sections.length : i;
  };

  const renderSidebar = (q) => {
    const sidebar = document.getElementById("docs-sidebar");
    sidebar.replaceChildren();
    let shown = 0;

    // Pinned cockpit at the very top.
    const pinned = INDEX.docs.find((d) => d.id === PINNED_ID);
    if (pinned && matches(pinned, q)) {
      const head = el("div", "nb-docs-section-head");
      head.append(el("h2", "nb-docs-section-title", "★ Cockpit"));
      head.append(el("p", "nb-docs-section-blurb",
        "what needs your decision, across every project"));
      sidebar.append(head);
      sidebar.append(makeRow(pinned));
      shown++;
    }

    // One collapsible group per project. A group opens when the viewer left it
    // open, when it holds the doc on screen, or when a search matches inside it.
    for (const group of INDEX.projects) {
      const docs = INDEX.docs
        .filter((d) => d.project === group.slug && d.id !== PINNED_ID && matches(d, q))
        .sort((a, b) => sectionRank(a.section) - sectionRank(b.section)
          || a.title.localeCompare(b.title));
      if (!docs.length) continue;

      const box = el("details", "nb-docs-group");
      box.open = Boolean(q) || openGroups.has(group.slug)
        || docs.some((d) => d.id === currentId);
      const summary = el("summary", "nb-docs-group-head");
      summary.append(el("span", "nb-docs-group-title", group.label));
      summary.append(el("span", "nb-docs-group-count", String(docs.length)));
      box.append(summary);
      for (const d of docs) {
        shown++;
        box.append(makeRow(d));
      }
      // Remember only deliberate toggles, not the ones search forces open.
      box.addEventListener("toggle", () => {
        if (q) return;
        if (box.open) openGroups.add(group.slug); else openGroups.delete(group.slug);
        saveOpen(openGroups);
      });
      sidebar.append(box);
    }
    if (!shown) {
      sidebar.append(el("p", "nb-docs-empty", "No docs match."));
    }
  };

  const showDoc = (id) => {
    const doc = INDEX.docs.find((d) => d.id === id);
    const pane = document.getElementById("docs-content");
    if (!doc) {
      pane.replaceChildren(el("p", "nb-docs-empty", "Not found."));
      return;
    }
    currentId = id;

    const meta = el("p", "nb-docs-meta");
    meta.append(el("span", "nb-docs-meta-id", doc.id || doc.type));
    const bits = [doc.type, doc.project, doc.status, ...(doc.tags || [])]
      .filter(Boolean).join(" · ");
    meta.append(document.createTextNode("  " + bits));

    const bodyWrap = el("div", "nb-doc-content");
    // doc.html is built by bin/build-docs-index.py, which HTML-escapes all doc
    // text before assembling tags — safe to inject as our own trusted markup.
    bodyWrap.innerHTML = doc.html;

    const path = el("p", "nb-docs-path", doc.path);

    pane.replaceChildren(meta, bodyWrap, path);
    pane.scrollTop = 0;
    renderSidebar(document.getElementById("docs-search").value.trim().toLowerCase());
  };

  const render = async () => {
    try {
      INDEX = await fetch("/admin/docs/index.json", { cache: "no-store" })
        .then((r) => r.json());
    } catch (e) {
      document.getElementById("docs-sidebar").replaceChildren(
        el("p", "nb-docs-empty", "couldn't load the docs index."));
      return;
    }
    // Stable section order per the manifest; docs within already sorted server-side.
    void STATUS_ORDER;
    renderSidebar("");

    // Land on the cockpit — the PM review — so the board opens on "what needs me".
    if (INDEX.docs.some((d) => d.id === PINNED_ID)) showDoc(PINNED_ID);

    const search = document.getElementById("docs-search");
    search.addEventListener("input", () =>
      renderSidebar(search.value.trim().toLowerCase()));

    const out = document.querySelector(".nb-admin-signout");
    if (out) {
      out.addEventListener("click", () => {
        sessionStorage.removeItem("jc-admin");
        window.location.href = "/";
      });
    }
  };

  const boot = () => {
    document.getElementById("docs-root").hidden = false;
    render();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
