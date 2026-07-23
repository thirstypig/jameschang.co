// jameschang.co — theme toggle + print expansion.

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
})();

// Footer "login" curtain → gated /admin/ page.
// NOT real authentication: this repo is public and GitHub Pages can't
// authenticate, so any browser-side check has its answer in this file. The
// password is stored only as its SHA-256 hash (the plaintext is never
// committed), and /admin/ holds only public-safe content. This stops casual
// snooping, not a determined person.
(() => {
  const footer = document.querySelector(".nb-footer");
  if (!footer || !window.crypto || !crypto.subtle) return;

  const PW_HASH =
    "7781113a99f177280ad3e89bcf631f03acb8fa8e626082dd9158eeee0bdd5674";

  const sha256hex = async (text) => {
    const buf = await crypto.subtle.digest("SHA-256",
      new TextEncoder().encode(text));
    return [...new Uint8Array(buf)]
      .map((b) => b.toString(16).padStart(2, "0")).join("");
  };

  // Footer trigger — matches the "// …" footer spans.
  const span = document.createElement("span");
  span.append("// ");
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "nb-footer-login";
  btn.textContent = "login";
  span.append(btn);
  footer.append(span);

  // Modal (reuses the site's notebook dialog styling).
  const dialog = document.createElement("dialog");
  dialog.id = "login-modal";
  dialog.className = "nb-quote-modal nb-login-modal";
  dialog.setAttribute("aria-label", "Log in");

  const form = document.createElement("form");
  const label = document.createElement("label");
  label.className = "nb-login-label";
  label.textContent = "password";
  const input = document.createElement("input");
  input.type = "password";
  input.className = "nb-login-input";
  input.autocomplete = "current-password";
  input.setAttribute("aria-label", "password");
  label.setAttribute("for", "login-pw");
  input.id = "login-pw";
  const err = document.createElement("p");
  err.className = "nb-login-error";
  err.textContent = "nope — try again";
  err.hidden = true;
  const submit = document.createElement("button");
  submit.type = "submit";
  submit.className = "nb-login-submit";
  submit.textContent = "enter";
  form.append(label, input, err, submit);
  dialog.append(form);
  document.body.append(dialog);

  btn.addEventListener("click", () => {
    err.hidden = true;
    input.value = "";
    dialog.showModal();
    input.focus();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const hex = await sha256hex(input.value);
    if (hex === PW_HASH) {
      sessionStorage.setItem("jc-admin", "1");
      window.location.href = "/admin/";
      return;
    }
    err.hidden = false;
    input.value = "";
    input.focus();
    dialog.classList.add("nb-login-shake");
    setTimeout(() => dialog.classList.remove("nb-login-shake"), 400);
  });
})();
