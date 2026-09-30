// Shared JSON loader for the /admin/ panels (cockpit.js, portfolio.js, goals.js).
// Each file is fetched once per page load, so every panel renders the same
// snapshot and the page makes one request per file instead of three; one retry
// absorbs a dropped connection. no-store: Pages caches for 10 minutes.
window.jcAdminJSON = (() => {
  const cache = {};
  const get = (url) => fetch(url, { cache: "no-store" }).then((r) => {
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    return r.json();
  });
  return (url) => (cache[url] ||= get(url).catch(() => get(url)));
})();
