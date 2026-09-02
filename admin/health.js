// /admin/ health strip — "is anything broken or about to break?"
// Feed freshness from .feeds-heartbeat.json (already public) + the expiry
// doorbell (bare counts) from admin/status.json. Renders only behind the
// sessionStorage unlock flag (admin.js bounces otherwise). XSS-safe:
// textContent / DOM nodes, never innerHTML.
(() => {
  if (sessionStorage.getItem("jc-admin") !== "1") return;

  // Named, tunable thresholds (hours). Mirror the 48h staleness monitor.
  const FRESH_H = 24;   // green under this
  const STALE_H = 48;   // red over this (the monitor opens an issue here)

  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };

  const ageHours = (iso) => {
    const t = Date.parse(iso);
    return Number.isNaN(t) ? Infinity : (Date.now() - t) / 3.6e6;
  };
  const relAge = (h) => {
    if (!Number.isFinite(h)) return "never";
    if (h < 1) return `${Math.round(h * 60)}m ago`;
    if (h < 48) return `${Math.round(h)}h ago`;
    return `${Math.round(h / 24)}d ago`;
  };
  const rag = (h) => (h < FRESH_H ? "ok" : h <= STALE_H ? "warn" : "danger");

  // Severity order for display. Age alone is not severity: a fresh feed that
  // is dropping content every run outranks a healthy one, and must not sort
  // below it.
  const RANK = { danger: 0, warn: 1, note: 2, ok: 3 };

  // Roll last_error up from colon-suffixed sub-slugs to their parent row.
  //
  // This used to be a lie. The sub-slugs were filtered out under a comment
  // saying they "roll up into the project-docs aggregate" — they did not roll
  // up anywhere, and the aggregate's own last_error is null. So a project-docs
  // row could read green while two sub-feeds dropped content daily. That green
  // is why a repo rename sat unread for 16 days and a published roadmap
  // silently lost a module.
  const rollUpErrors = (hb) => {
    const notes = {};
    Object.entries(hb).forEach(([slug, info]) => {
      const err = info && info.last_error;
      if (!err) return;
      const i = slug.indexOf(":");
      const parent = i === -1 ? slug : slug.slice(0, i);
      const label = i === -1 ? err : `${slug.slice(i + 1)} — ${err}`;
      (notes[parent] = notes[parent] || []).push(label);
    });
    return notes;
  };

  // A fresh feed carrying an error is neither ok nor stale. It gets its own
  // state so it cannot hide behind a green dot — and so it stays visually
  // distinct from a genuinely dead feed, which is a different problem.
  const stateFor = (h, noteCount) => {
    const base = rag(h);
    return base === "ok" && noteCount > 0 ? "note" : base;
  };

  const renderFeeds = (hb) => {
    const strip = document.getElementById("health-strip");
    if (!strip) return;
    const notes = rollUpErrors(hb);
    const rows = Object.entries(hb)
      .filter(([slug]) => !slug.includes(":"))
      .map(([slug, info]) => {
        const h = ageHours(info && info.last_success_utc);
        const n = notes[slug] || [];
        return { slug, h, notes: n, st: stateFor(h, n.length) };
      })
      .sort((a, b) => RANK[a.st] - RANK[b.st] || b.h - a.h);

    const nodes = [];
    rows.forEach(({ slug, h, notes: n, st }) => {
      const row = el("div", "nb-health-row");
      row.append(el("span", `nb-health-dot nb-health-dot--${st}`));
      row.append(el("span", "nb-health-slug", slug));
      if (n.length > 1) row.append(el("span", "nb-health-sub", `${n.length} sub-feeds`));
      row.append(el("span", "nb-health-age", relAge(h)));
      nodes.push(row);
      // textContent via el() — last_error is upstream-derived text and this
      // page never uses innerHTML.
      n.forEach((msg) => nodes.push(el("p", "nb-health-err", msg)));
    });
    strip.replaceChildren(...nodes);
  };

  const renderDoorbell = (status) => {
    const bell = document.getElementById("health-doorbell");
    if (!bell) return;
    const e = status && status.expiry;
    if (!e) { bell.remove(); return; }
    const soon = e.within_7 || 0;
    const near = (e.within_14 || 0) + (e.within_30 || 0);
    const nod = e.needs_date || 0;
    let cls = "ok", msg;
    if (soon > 0) { cls = "danger"; msg = `⚠ ${soon} credential${soon > 1 ? "s" : ""} need attention this week`; }
    else if (near > 0) { cls = "warn"; msg = `${near} credential${near > 1 ? "s" : ""} approaching expiry`; }
    else { msg = "credentials all clear"; }
    if (nod > 0) msg += ` · ${nod} need a date`;
    bell.className = `nb-health-doorbell nb-health-doorbell--${cls}`;
    bell.textContent = msg;
  };

  const load = async () => {
    const [hbRes, stRes] = await Promise.allSettled([
      fetch("/.feeds-heartbeat.json", { cache: "no-store" }).then((r) => r.json()),
      fetch("/admin/status.json", { cache: "no-store" }).then((r) => r.json()),
    ]);
    const strip = document.getElementById("health-strip");
    if (hbRes.status === "fulfilled") renderFeeds(hbRes.value);
    else if (strip) strip.replaceChildren(el("p", "nb-portfolio-error", "couldn't load feed health."));
    renderDoorbell(stRes.status === "fulfilled" ? stRes.value : null);
  };

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", load);
  else load();
})();
