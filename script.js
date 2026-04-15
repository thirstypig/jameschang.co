// jameschang.co — theme toggle only.
// Email is now a plain mailto:; no reveal logic needed.

(() => {
  // Explicit [data-theme] on <html> overrides OS preference.
  // Removing the attribute falls back to @media (prefers-color-scheme).
  const stored = localStorage.getItem("theme");
  if (stored === "light" || stored === "dark") {
    document.documentElement.setAttribute("data-theme", stored);
  }

  const toggle = document.querySelector(".theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const osDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      const current = document.documentElement.getAttribute("data-theme") ?? (osDark ? "dark" : "light");
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
    });
  }
})();
