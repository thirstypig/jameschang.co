// Gate check for /admin/. The "jc-admin" sessionStorage flag is a curtain, not
// real auth — it is trivially spoofable in devtools, so this page holds only
// public-safe content by design. See docs/superpowers/specs (local).
(() => {
  if (sessionStorage.getItem("jc-admin") !== "1") {
    window.location.replace("/");
    return;
  }
  const root = document.getElementById("admin-root");
  if (root) root.hidden = false;
  // Collapsible sections: remember which ones the viewer closed. A per-viewer
  // convenience — storage can be missing or throw, and the page works without it.
  const CLOSED_KEY = "jc-cockpit-closed";
  let closed = [];
  try { closed = JSON.parse(localStorage.getItem(CLOSED_KEY) || "[]"); } catch (e) { closed = []; }
  document.querySelectorAll("details.nb-cockpit-sec[data-sec]").forEach((d) => {
    if (closed.includes(d.dataset.sec)) d.open = false;
    d.addEventListener("toggle", () => {
      const now = [...document.querySelectorAll("details.nb-cockpit-sec[data-sec]")]
        .filter((x) => !x.open).map((x) => x.dataset.sec);
      try { localStorage.setItem(CLOSED_KEY, JSON.stringify(now)); } catch (e) { /* convenience only */ }
    });
  });

  const out = document.querySelector(".nb-admin-signout");
  if (out) {
    out.addEventListener("click", () => {
      sessionStorage.removeItem("jc-admin");
      window.location.href = "/";
    });
  }
})();
