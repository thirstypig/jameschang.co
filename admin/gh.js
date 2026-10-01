// Shared GitHub Contents API writer for the /admin/ editors (goals.js, money.js).
// Each editor stages its edits as a pure function over the JSON document; save()
// fetches the current file, applies the edits, and commits it. A 409/422 means the
// file moved under us (the Mac's publish, another tab) — refetch and replay once.
// The fine-grained token (Contents read/write on this repo) is pasted once per tab
// and held in sessionStorage only, never logged. XSS-safe: no DOM work here.
window.jcGh = (() => {
  const REPO = "thirstypig/jameschang.co";
  const TOKEN_KEY = "jc-gh-token";

  const token = () => sessionStorage.getItem(TOKEN_KEY);
  const setToken = (t) => sessionStorage.setItem(TOKEN_KEY, t);
  const forgetToken = () => sessionStorage.removeItem(TOKEN_KEY);

  const b64encode = (str) => {
    const bytes = new TextEncoder().encode(str);
    let bin = "";
    for (const b of bytes) bin += String.fromCharCode(b);
    return btoa(bin);
  };
  const b64decode = (b64) =>
    new TextDecoder().decode(Uint8Array.from(atob(b64.replace(/\n/g, "")), (c) => c.charCodeAt(0)));

  // mutate(doc) applies the staged edits to a freshly fetched copy, in place.
  const save = async (path, mutate, message) => {
    const t = token();
    if (!t) throw new Error("Paste a token first.");
    const api = `https://api.github.com/repos/${REPO}/contents/${path}`;
    const call = (opts = {}) => fetch(api + (opts.method ? "" : "?ref=main"), {
      ...opts,
      cache: "no-store",
      headers: { Authorization: `Bearer ${t}`, Accept: "application/vnd.github+json", ...(opts.headers || {}) },
    });
    for (let attempt = 0; attempt < 2; attempt++) {
      const got = await call();
      if (got.status === 401 || got.status === 403) {
        forgetToken();
        throw new Error("token rejected — needs Contents read/write on this repo");
      }
      if (!got.ok) throw new Error(`couldn't read ${path} (${got.status})`);
      const meta = await got.json();
      const fresh = JSON.parse(b64decode(meta.content));
      mutate(fresh);
      const body = JSON.stringify(fresh, null, 2) + "\n";
      const put = await call({
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, content: b64encode(body), sha: meta.sha, branch: "main" }),
      });
      if (put.ok) return fresh;
      if (put.status !== 409 && put.status !== 422) throw new Error(`save failed (${put.status})`);
    }
    throw new Error(`${path} kept changing — try again`);
  };

  return { token, setToken, forgetToken, save };
})();
