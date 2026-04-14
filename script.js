// jameschang.co — minimal JS.
// Only job: reveal the email on click so scrapers don't get a plain mailto in HTML.

(() => {
  const user = "jimmychang316";
  const domain = "gmail.com";
  const email = `${user}@${domain}`;

  const triggers = document.querySelectorAll("[data-email], [data-email-cta]");

  triggers.forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      el.textContent = email;
      el.setAttribute("href", `mailto:${email}`);
      // { once: true } auto-removes this listener; next click is a normal mailto.
    }, { once: true });
  });
})();
