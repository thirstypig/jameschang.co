// jameschang.co — theme toggle + headshot rotation + print expansion.
// Email is now a plain mailto:; no reveal logic needed.

// Before print: expand any <details> elements (e.g., the "+ 8 additional
// certifications" collapse) so all credentials render on the resume PDF.
// Chrome's <details> is open-attribute-driven, not CSS-driven, so a
// stylesheet alone can't unfold it.
window.addEventListener("beforeprint", () => {
  document.querySelectorAll("details").forEach(d => d.setAttribute("open", ""));
});

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

  // Headshot rotation — crossfade through N images
  const rotator = document.querySelector(".headshot-rotate");
  if (rotator) {
    const pics = rotator.querySelectorAll("picture");
    if (pics.length > 1) {
      let current = 0;
      let intervalId = null;
      pics.forEach((p, i) => { p.style.opacity = i === 0 ? "1" : "0"; });

      const tick = () => {
        pics[current].style.opacity = "0";
        current = (current + 1) % pics.length;
        pics[current].style.opacity = "1";
      };
      const start = () => { if (!intervalId) intervalId = setInterval(tick, 5000); };
      const stop = () => { clearInterval(intervalId); intervalId = null; };

      const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

      // Only start if motion is allowed
      if (!motionQuery.matches) start();

      // Pause when tab is hidden, resume when visible (unless reduced-motion)
      document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
          stop();
        } else if (!motionQuery.matches) {
          start();
        }
      });

      // Live-respond to reduced-motion preference changes
      motionQuery.addEventListener("change", (e) => {
        if (e.matches) {
          stop();
        } else if (!document.hidden) {
          start();
        }
      });
    }
  }
})();
