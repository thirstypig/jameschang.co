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
  const out = document.querySelector(".nb-admin-signout");
  if (out) {
    out.addEventListener("click", () => {
      sessionStorage.removeItem("jc-admin");
      window.location.href = "/";
    });
  }
})();
