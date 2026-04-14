// jameschang.co — minimal JS.
// Jobs: (1) reveal email on click, (2) theme toggle with localStorage persistence.

(() => {
  // --- Email reveal ---
  const user = "jimmychang316";
  const domain = "gmail.com";
  const email = `${user}@${domain}`;

  document.querySelectorAll("[data-email], [data-email-cta]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      el.textContent = email;
      el.setAttribute("href", `mailto:${email}`);
    }, { once: true });
  });

  // --- Theme toggle ---
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
