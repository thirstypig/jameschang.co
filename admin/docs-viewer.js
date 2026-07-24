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

    for (const section of INDEX.sections) {
      const docs = INDEX.docs
        .filter((d) => d.section === section.key && d.id !== PINNED_ID && matches(d, q))
        .sort((a, b) => a.title.localeCompare(b.title));
      if (!docs.length) continue;

      const head = el("div", "nb-docs-section-head");
      head.append(el("h2", "nb-docs-section-title", section.label));
      head.append(el("p", "nb-docs-section-blurb", section.blurb));
      sidebar.append(head);

      for (const d of docs) {
        shown++;
        sidebar.append(makeRow(d));
      }
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

    const path = el("p", "nb-docs-path", `admin/docs/${doc.path}`);

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
