// jameschang.co — theme toggle only.
// Email is now a plain mailto:; no reveal logic needed.

(() => {
  const stored = localStorage.getItem("theme");
  if (stored === "light" || stored === "dark") {
    document.documentElement.setAttribute("data-theme", stored);
  }

  const toggle = document.querySelector(".theme-toggle");
  if (!toggle) return;

  const osDark = () => window.matchMedia("(prefers-color-scheme: dark)").matches;
  const currentTheme = () =>
    document.documentElement.getAttribute("data-theme") ?? (osDark() ? "dark" : "light");

  // aria-pressed = "true" when dark mode is active, for screen-reader state.
  const syncPressed = () => toggle.setAttribute("aria-pressed", currentTheme() === "dark" ? "true" : "false");
  syncPressed();

  toggle.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    syncPressed();
  });
})();
