"""E2E tests for jameschang.co — validates all HTML pages for structure, meta tags,
CSP, links, images, and accessibility attributes.

Spins up a local HTTP server and validates pages via HTTP requests.
No external dependencies — uses only Python stdlib.
"""

import glob
import json
import os
import re
import threading
import time
import urllib.request
from datetime import datetime
from functools import partial
from html.parser import HTMLParser
from http.server import HTTPServer, SimpleHTTPRequestHandler

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PORT = 8799  # Unlikely to conflict

# All HTML pages in the site
HTML_FILES = sorted(
    os.path.relpath(f, REPO_ROOT)
    for f in glob.glob(os.path.join(REPO_ROOT, "**", "*.html"), recursive=True)
    if not any(skip in f for skip in [".git/", "node_modules/", ".playwright-mcp/"])
)

# Pages that should have CSP (exclude callback pages which use a different pattern)
STANDARD_PAGES = [f for f in HTML_FILES if "callback" not in f]

# Expected feed markers in now/index.html
EXPECTED_MARKERS = [
    "WHOOP", "SPOTIFY", "MLB", "GOODREADS-READING", "GOODREADS", "FBST", "PLEX",
    "PAGE-UPDATED",
    "ACTIVE-PROJECTS", "BACKBURNER-PROJECTS", "ACTIVE-EYEBROW", "BACKBURNER-EYEBROW",
    "GCAL", "GCAL-EYEBROW",
]


# ── Server fixture ───────────────────────────────────────────────

_server = None
_thread = None


def setup_module():
    """Start a local HTTP server for the repo."""
    global _server, _thread
    handler = partial(SimpleHTTPRequestHandler, directory=REPO_ROOT)
    _server = HTTPServer(("127.0.0.1", PORT), handler)
    _thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _thread.start()
    time.sleep(0.2)


def teardown_module():
    """Shut down the local server."""
    if _server:
        _server.shutdown()


def fetch(path):
    """GET a path from the local server, return (status, body)."""
    url = f"http://127.0.0.1:{PORT}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


# ── HTML parser helper ───────────────────────────────────────────

class MetaExtractor(HTMLParser):
    """Extract meta tags and key attributes from HTML."""

    def __init__(self):
        super().__init__()
        self.metas = {}  # name/http-equiv -> content
        self.title = None
        self._in_title = False
        self._title_data = []
        self.has_skip_link = False
        self.theme_toggle_aria_pressed = None
        self.img_srcs = []
        self.source_srcsets = []
        self.internal_hrefs = []
        self.json_ld_blocks = []
        self._in_script_ld = False
        self._script_data = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "meta":
            key = d.get("name") or d.get("http-equiv") or d.get("property")
            if key and "content" in d:
                self.metas[key.lower()] = d["content"]
        elif tag == "title":
            self._in_title = True
            self._title_data = []
        elif tag == "a":
            cls = d.get("class", "")
            href = d.get("href", "")
            if "skip-link" in cls:
                self.has_skip_link = True
            if href and not href.startswith(("http", "mailto:", "tel:", "#", "javascript:")):
                self.internal_hrefs.append(href)
        elif tag == "button":
            cls = d.get("class", "")
            if "theme-toggle" in cls:
                self.theme_toggle_aria_pressed = d.get("aria-pressed")
        elif tag == "img":
            src = d.get("src", "")
            if src:
                self.img_srcs.append(src)
        elif tag == "source":
            srcset = d.get("srcset", "")
            if srcset:
                self.source_srcsets.append(srcset)
        elif tag == "script":
            if d.get("type") == "application/ld+json":
                self._in_script_ld = True
                self._script_data = []

    def handle_data(self, data):
        if self._in_title:
            self._title_data.append(data)
        if self._in_script_ld:
            self._script_data.append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
            self.title = "".join(self._title_data).strip()
        if tag == "script" and self._in_script_ld:
            self._in_script_ld = False
            self.json_ld_blocks.append("".join(self._script_data))


def parse_page(html_body):
    parser = MetaExtractor()
    parser.feed(html_body)
    return parser


# ── Tests: Page loads ────────────────────────────────────────────

class TestPageLoads:
    """Every HTML file should return 200."""

    def test_all_pages_load(self):
        failures = []
        for f in HTML_FILES:
            url_path = f.replace("index.html", "")
            status, _ = fetch(url_path)
            if status != 200:
                failures.append(f"{f}: HTTP {status}")
        assert not failures, f"Pages failed to load:\n" + "\n".join(failures)


# ── Tests: Meta tags ─────────────────────────────────────────────

class TestMetaTags:
    """Standard pages must have viewport, color-scheme, and title."""

    def test_viewport_on_all_pages(self):
        failures = []
        for f in HTML_FILES:
            _, body = fetch(f)
            p = parse_page(body)
            if "viewport" not in p.metas:
                failures.append(f)
        assert not failures, f"Missing viewport meta:\n" + "\n".join(failures)

    def test_color_scheme_on_standard_pages(self):
        failures = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            p = parse_page(body)
            if "color-scheme" not in p.metas:
                failures.append(f)
        assert not failures, f"Missing color-scheme meta:\n" + "\n".join(failures)

    def test_title_on_all_pages(self):
        failures = []
        for f in HTML_FILES:
            _, body = fetch(f)
            p = parse_page(body)
            if not p.title:
                failures.append(f)
        assert not failures, f"Missing <title>:\n" + "\n".join(failures)

    def test_referrer_on_standard_pages(self):
        failures = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            p = parse_page(body)
            if "referrer" not in p.metas:
                failures.append(f)
        assert not failures, f"Missing referrer meta:\n" + "\n".join(failures)


# ── Tests: CSP ───────────────────────────────────────────────────

class TestCSP:
    """All pages must have Content-Security-Policy."""

    def test_csp_present_on_all_pages(self):
        failures = []
        for f in HTML_FILES:
            _, body = fetch(f)
            p = parse_page(body)
            if "content-security-policy" not in p.metas:
                failures.append(f)
        assert not failures, f"Missing CSP:\n" + "\n".join(failures)

    def test_object_src_none_on_standard_pages(self):
        failures = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            p = parse_page(body)
            csp = p.metas.get("content-security-policy", "")
            if "object-src 'none'" not in csp:
                failures.append(f)
        assert not failures, f"Missing object-src 'none':\n" + "\n".join(failures)


# ── Tests: Accessibility ─────────────────────────────────────────

class TestAccessibility:
    """Theme toggle and skip link accessibility."""

    def test_skip_link_on_standard_pages(self):
        failures = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            p = parse_page(body)
            if not p.has_skip_link:
                failures.append(f)
        assert not failures, f"Missing skip link:\n" + "\n".join(failures)

    def test_aria_pressed_on_theme_toggle(self):
        failures = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            p = parse_page(body)
            if p.theme_toggle_aria_pressed is None:
                failures.append(f"{f}: no aria-pressed")
            elif p.theme_toggle_aria_pressed != "false":
                failures.append(f"{f}: aria-pressed={p.theme_toggle_aria_pressed} (expected 'false')")
        assert not failures, f"Theme toggle aria-pressed issues:\n" + "\n".join(failures)


# ── Tests: JSON-LD ───────────────────────────────────────────────

class TestJsonLD:
    """JSON-LD structured data must be valid JSON."""

    def test_json_ld_valid_on_all_pages(self):
        failures = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            p = parse_page(body)
            for i, block in enumerate(p.json_ld_blocks):
                try:
                    json.loads(block)
                except json.JSONDecodeError as e:
                    failures.append(f"{f} block {i}: {e}")
        assert not failures, f"Invalid JSON-LD:\n" + "\n".join(failures)


# ── Tests: Images exist ──────────────────────────────────────────

class TestImages:
    """All referenced images must exist as files."""

    def test_img_srcs_exist(self):
        failures = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            p = parse_page(body)
            page_dir = os.path.dirname(os.path.join(REPO_ROOT, f))
            for src in p.img_srcs:
                if src.startswith("http") or src.startswith("data:"):
                    continue
                if src.startswith("/"):
                    full = os.path.join(REPO_ROOT, src.lstrip("/"))
                else:
                    full = os.path.join(page_dir, src)
                # Strip query strings
                full = full.split("?")[0]
                if not os.path.exists(full):
                    failures.append(f"{f}: missing {src}")
        assert not failures, f"Missing images:\n" + "\n".join(failures)


# ── Tests: Feed markers ──────────────────────────────────────────

class TestFeedMarkers:
    """now/index.html must have paired START/END markers for all feeds."""

    def test_all_markers_present(self):
        _, body = fetch("now/index.html")
        failures = []
        for marker in EXPECTED_MARKERS:
            if f"<!-- {marker}-START -->" not in body:
                failures.append(f"Missing <!-- {marker}-START -->")
            if f"<!-- {marker}-END -->" not in body:
                failures.append(f"Missing <!-- {marker}-END -->")
        assert not failures, f"Feed marker issues:\n" + "\n".join(failures)

# ── Tests: OpenSSL parity ────────────────────────────────────────

class TestOpenSSLParity:
    """All openssl enc calls must use the same -iter value."""

    def test_iter_600000_everywhere(self):
        failures = []
        for pattern in ["bin/*.sh", "bin/*.py"]:
            for filepath in glob.glob(os.path.join(REPO_ROOT, pattern)):
                with open(filepath) as f:
                    for i, line in enumerate(f, 1):
                        if "openssl" in line and "enc" in line:
                            if "-iter" not in line and "-pbkdf2" in line:
                                failures.append(f"{os.path.basename(filepath)}:{i}: openssl enc with -pbkdf2 but no -iter")
                            elif "-iter" in line and "600000" not in line:
                                failures.append(f"{os.path.basename(filepath)}:{i}: openssl enc with wrong -iter")
        assert not failures, f"OpenSSL -iter issues:\n" + "\n".join(failures)


# ── Tests: Dark mode CSS parity ──────────────────────────────────

class TestDarkModeParity:
    """CSS files should have balanced @media dark / [data-theme] selectors."""

    def test_selector_balance(self):
        failures = []
        for css_file in ["notebook.css", "projects/projects.css"]:
            path = os.path.join(REPO_ROOT, css_file)
            if not os.path.exists(path):
                continue
            with open(path) as f:
                content = f.read()
            media_count = len(re.findall(r"prefers-color-scheme:\s*dark", content))
            attr_count = len(re.findall(r'data-theme="dark"', content))
            # Allow variance — some components use [data-theme] without a
            # wrapping @media block (e.g. duplicate selectors for specificity).
            # Flag only extreme imbalances suggesting whole blocks are missing.
            if abs(media_count - attr_count) > 8:
                failures.append(
                    f"{css_file}: @media dark={media_count}, [data-theme]={attr_count} "
                    f"(gap of {abs(media_count - attr_count)})"
                )
        assert not failures, f"Dark mode selector imbalance:\n" + "\n".join(failures)


# ── Tests: GA4 ───────────────────────────────────────────────────

class TestGA4:
    """Google Analytics 4 must be present on all pages."""

    def test_ga4_snippet_on_all_pages(self):
        failures = []
        for f in HTML_FILES:
            _, body = fetch(f)
            if "G-B3HW5VBDB3" not in body:
                failures.append(f)
        assert not failures, f"Missing GA4 snippet:\n" + "\n".join(failures)

    def test_csp_allows_google(self):
        failures = []
        for f in HTML_FILES:
            _, body = fetch(f)
            p = parse_page(body)
            csp = p.metas.get("content-security-policy", "")
            if "googletagmanager.com" not in csp:
                failures.append(f"{f}: missing googletagmanager.com in CSP")
        assert not failures, f"CSP missing Google domains:\n" + "\n".join(failures)


# ── Tests: Privacy policy accuracy ───────────────────────────────

class TestPrivacyPolicy:
    """Privacy policy must accurately reflect site data practices."""

    def test_lists_all_feed_sources(self):
        _, body = fetch("privacy/index.html")
        # Trakt + Letterboxd disclosures dropped 2026-04-28 along with the
        # feeds themselves. Plex + Thirsty Pig hitlist added 2026-04-28
        # after /ce:review surfaced their absence. The list must accurately
        # reflect what /now still surfaces at runtime.
        required = ["GitHub", "MLB", "Goodreads", "Fantastic Leagues", "Plex", "hitlist"]
        missing = [src for src in required if src not in body]
        assert not missing, f"Privacy policy missing feed sources: {missing}"

    def test_mentions_ga4(self):
        _, body = fetch("privacy/index.html")
        assert "Google Analytics 4" in body, "Privacy policy does not mention GA4"
        assert "G-B3HW5VBDB3" in body, "Privacy policy does not mention measurement ID"


# ── Tests: Print stylesheet ──────────────────────────────────────

class TestPrintStylesheet:
    """Homepage must produce a printable résumé.

    The print stylesheet (notebook.css @media print) + print-name-block
    element + script.js beforeprint listener together produce resume.pdf.
    These tests pin invariants of that pipeline so a casual edit can't
    silently break the PDF identity block, the certifications expansion,
    or the print-specific font sizing."""

    def test_print_media_block_exists(self):
        # The notebook design uses ATS-canonical lowercase section labels
        # directly (about, experience, education...) so it doesn't need the
        # live design's .no-print/.print-only dual-text aliasing pattern.
        # What it DOES need is an @media print block in the active stylesheet.
        css_path = os.path.join(REPO_ROOT, "notebook.css")
        css = open(css_path).read()
        assert "@media print" in css, "Missing @media print block in notebook.css"
        assert "@page" in css, "Missing @page rule for résumé page sizing"

    def test_resume_pdf_exists(self):
        pdf_path = os.path.join(REPO_ROOT, "resume.pdf")
        assert os.path.exists(pdf_path), "resume.pdf not found in repo root"

    def test_print_name_block_only_on_homepage(self):
        """The .print-name-block <header> renders the name + contact line at
        the top of resume.pdf. It belongs on index.html only — other pages
        wouldn't add value if a contributor accidentally copy-pasted it.
        Regression this prevents: someone deletes it during a refactor →
        resume.pdf top of page 1 has no candidate name."""
        _, body = fetch("index.html")
        assert 'class="print-name-block"' in body, (
            "Missing <header class='print-name-block'> on homepage — "
            "resume.pdf will have no name + contact info on page 1"
        )
        assert '<h1 class="print-name">James Chang, MBA</h1>' in body, (
            "Print-name-block missing the canonical name <h1>"
        )
        # Ensure it's NOT on /now or /privacy or /projects (would print twice)
        for f in ["now/index.html", "privacy/index.html", "projects/index.html"]:
            _, other = fetch(f)
            assert 'class="print-name-block"' not in other, (
                f"{f}: print-name-block leaked onto a non-homepage — "
                "would render duplicate name blocks if printed"
            )

    def test_print_name_block_hidden_on_screen(self):
        """notebook.css must declare `.print-name-block { display: none }`
        OUTSIDE the @media print block so the element is screen-hidden by
        default, then revealed only in print. Regression this prevents:
        someone removes the screen-hide rule → the name block bleeds onto
        the homepage above the nav, breaking the screen design."""
        css = open(os.path.join(REPO_ROOT, "notebook.css")).read()
        # Strip the @media print block first to ensure the rule lives at
        # the top level, not just inside @media print.
        before_print = css.split("@media print")[0]
        assert ".print-name-block { display: none" in before_print or \
               ".print-name-block {\n  display: none" in before_print, (
            "Missing top-level `.print-name-block { display: none }` — "
            "the print-only block is leaking onto the screen"
        )

    def test_print_name_block_contact_canonical_urls(self):
        """The contact line carries the four canonical channels: email,
        LinkedIn, GitHub, jameschang.co. Catches typos / stale handles
        when any of these change."""
        _, body = fetch("index.html")
        # Scope assertions to the print-name-block region
        m = re.search(
            r'<header class="print-name-block">(.*?)</header>',
            body, re.DOTALL,
        )
        assert m, "print-name-block region not found"
        block = m.group(1)
        for required in [
            "jimmychang316@gmail.com",
            "linkedin.com/in/jimmychang316",
            "github.com/thirstypig",
            "jameschang.co",
        ]:
            assert required in block, (
                f"print-name-block contact line missing: {required}"
            )

    def test_script_js_expands_details_on_print(self):
        """Chrome's <details> element is open-attribute-driven, not
        CSS-driven — a stylesheet alone cannot unfold a closed <details>
        in print. script.js carries a beforeprint listener that sets the
        `open` attribute on every <details> right before --print-to-pdf
        runs. Without this, the 8 additional certifications collapse and
        resume.pdf shows only CSPO + Product School. This is exactly the
        kind of silent regression (only visible when someone prints) the
        test suite is for."""
        js = open(os.path.join(REPO_ROOT, "script.js")).read()
        assert 'addEventListener("beforeprint"' in js or \
               "addEventListener('beforeprint'" in js, (
            "script.js missing the beforeprint listener — additional "
            "certifications will collapse in resume.pdf"
        )
        assert 'querySelectorAll("details")' in js or \
               "querySelectorAll('details')" in js, (
            "script.js beforeprint listener doesn't query <details> — "
            "the cert expansion won't fire"
        )
        # The actual unfold operation (could be .open = true OR setAttribute)
        assert 'setAttribute("open"' in js or "open = true" in js, (
            "script.js beforeprint listener doesn't open <details> elements"
        )

    def test_print_card_name_overrides_screen_size(self):
        """The screen rule `.nb-card.compact .nb-card-name { font-size: 20px }`
        has higher specificity (2 classes) than a plain `.nb-card-name`
        print rule (1 class). The print stylesheet must either match
        specificity or use !important so project names in resume.pdf
        render at the print 10.5pt, not the screen 20px. Regression
        this prevents: someone removes the specificity guard → project
        names blow up to display size in the PDF and consume an extra
        page (real bug fixed in commit ba49300)."""
        css = open(os.path.join(REPO_ROOT, "notebook.css")).read()
        print_block = css[css.find("@media print"):]
        # The override must be present in some recognizable form
        has_specificity_match = ".nb-card.compact .nb-card-name" in print_block
        has_important = "font-size: 10.5pt !important" in print_block
        assert has_specificity_match or has_important, (
            "Print rule for .nb-card-name doesn't override the screen-mode "
            ".nb-card.compact .nb-card-name { font-size: 20px } rule. "
            "Project names will render at 20px in resume.pdf instead of 10.5pt."
        )


# ── Tests: Internal links ────────────────────────────────────────

class TestInternalLinks:
    """All internal href values must resolve to real files."""

    def test_internal_hrefs_resolve(self):
        failures = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            p = parse_page(body)
            page_dir = os.path.dirname(os.path.join(REPO_ROOT, f))
            for href in p.internal_hrefs:
                # Skip anchors and query strings
                if href.startswith("#"):
                    continue
                clean = href.split("?")[0].split("#")[0]
                if clean.startswith("/"):
                    full = os.path.join(REPO_ROOT, clean.lstrip("/"))
                else:
                    full = os.path.join(page_dir, clean)
                # Directories should have index.html
                if full.endswith("/"):
                    full = os.path.join(full, "index.html")
                if not os.path.exists(full):
                    failures.append(f"{f}: broken href {href}")
        assert not failures, f"Broken internal links:\n" + "\n".join(failures)


# ── Tests: Symlinks ──────────────────────────────────────────────

class TestNoSymlinks:
    """No symlinks should be committed — they break GitHub Pages."""

    def test_no_symlinks_in_tracked_files(self):
        import subprocess
        result = subprocess.run(
            ["git", "ls-files", "-s"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        symlinks = [
            line.split("\t")[-1]
            for line in result.stdout.strip().split("\n")
            if line.startswith("120000")
        ]
        assert not symlinks, f"Symlinks in git (break GitHub Pages):\n" + "\n".join(symlinks)


# ── Tests: Sitemap consistency ───────────────────────────────────

class TestSitemap:
    """sitemap.xml URLs must match actual HTML files."""

    def test_sitemap_urls_resolve(self):
        sitemap_path = os.path.join(REPO_ROOT, "sitemap.xml")
        if not os.path.exists(sitemap_path):
            return  # no sitemap, nothing to check
        with open(sitemap_path) as f:
            content = f.read()
        urls = re.findall(r"<loc>https://jameschang\.co/([^<]*)</loc>", content)
        failures = []
        for url_path in urls:
            if not url_path:
                # Root URL
                full = os.path.join(REPO_ROOT, "index.html")
            elif url_path.endswith("/"):
                full = os.path.join(REPO_ROOT, url_path, "index.html")
            else:
                full = os.path.join(REPO_ROOT, url_path)
            if not os.path.exists(full):
                failures.append(f"sitemap lists /{url_path} but file not found")
        assert not failures, f"Sitemap drift:\n" + "\n".join(failures)

    def test_robots_txt_references_sitemap(self):
        robots_path = os.path.join(REPO_ROOT, "robots.txt")
        if not os.path.exists(robots_path):
            return
        with open(robots_path) as f:
            content = f.read()
        assert "sitemap.xml" in content.lower() or "Sitemap" in content, \
            "robots.txt does not reference sitemap.xml"


# ── Tests: OG image ──────────────────────────────────────────────

class TestOGImage:
    """OG social preview image must exist."""

    def test_og_image_exists(self):
        _, body = fetch("index.html")
        p = parse_page(body)
        og_image = p.metas.get("og:image", "")
        if not og_image:
            return  # no og:image meta, skip
        # Resolve path
        if og_image.startswith("http"):
            # Extract path from full URL
            from urllib.parse import urlparse
            path = urlparse(og_image).path.lstrip("/")
        elif og_image.startswith("/"):
            path = og_image.lstrip("/")
        else:
            path = og_image
        full = os.path.join(REPO_ROOT, path)
        assert os.path.exists(full), f"OG image missing: {og_image} (expected at {full})"


# ── Tests: Top-nav consistency ───────────────────────────────────
#
# The top nav is duplicated across 16 HTML files with no compile-time check
# that they stay in sync. These tests assert the structure that was
# standardized in commits 5f06bd8 (rename to /projects/, drop [about],
# update brand) and cede613 (rename [now] → [/now], unify nav order).
# Without these tests, any future single-file edit could silently drift
# from the rest of the site.

class TestNavConsistency:
    """Every page's top nav must match the canonical structure."""

    def test_brand_text_is_jameschang_co(self):
        """Brand reads jameschang.co with the dot in an accent span — set in cede613."""
        failures = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            if 'class="nb-brand">jameschang<span class="dot">.</span>co</a>' not in body:
                failures.append(f"{f}: brand drifted from jameschang.co")
        assert not failures, "Brand inconsistency:\n" + "\n".join(failures)

    def test_no_about_link_anywhere(self):
        """[about] was retired — the brand link covers home/about."""
        failures = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            if '[about]' in body and 'class="nb-link"' in body:
                # Be precise — only flag if [about] appears inside a nav link
                if re.search(r'class="nb-link"[^>]*>\[about\]</a>', body):
                    failures.append(f"{f}: stray [about] nav link")
        assert not failures, "[about] link reappeared:\n" + "\n".join(failures)

    def test_now_link_uses_slash_prefix(self):
        """[now] was renamed to [/now] in cede613 to match path convention."""
        failures = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            # Exactly one [/now] nav link; zero [now] nav links
            if re.search(r'class="nb-link"[^>]*>\[now\]</a>', body):
                failures.append(f"{f}: legacy [now] (should be [/now])")
            if not re.search(r'class="nb-link"[^>]*>\[/now\]</a>', body):
                failures.append(f"{f}: missing [/now] nav link")
        assert not failures, "[/now] inconsistency:\n" + "\n".join(failures)

    def test_nav_order_experience_then_projects_then_now(self):
        """Standard order: [experience] → [projects ▾] → [/now]. /now had this
        flipped before cede613; the test prevents regression."""
        failures = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            # Find first occurrence of each marker inside the nav block
            nav_match = re.search(r'<div class="nb-nav-inner">(.*?)</div>\s*</header>', body, re.DOTALL)
            if not nav_match:
                continue
            nav = nav_match.group(1)
            i_exp = nav.find('[experience]')
            i_proj = nav.find('[projects&nbsp;▾]')
            i_now = nav.find('[/now]')
            # All three must be present and in that order
            if not (0 < i_exp < i_proj < i_now):
                failures.append(
                    f"{f}: nav order [experience]={i_exp} [projects ▾]={i_proj} [/now]={i_now}"
                )
        assert not failures, "Nav order drifted:\n" + "\n".join(failures)


# ── Tests: Cross-project nav on deep-dive pages ──────────────────
#
# Added in commit 5f06bd8. Every deep-dive sub-page under /projects/{slug}/
# must surface the cross-project nav strip so visitors can switch projects
# without going back to the projects landing. These tests catch (a) a new
# deep-dive page added without the strip, (b) a project's hrefs drifting
# from the canonical entry-point sub-pages, (c) aria-current going stale.

class TestCrossProjectNav:
    """All deep-dive sub-pages must carry the cross-project nav."""

    DEEP_DIVES = [
        f for f in STANDARD_PAGES
        if f.startswith("projects/") and f.count("/") >= 3
    ]
    EXPECTED_LINKS = {
        "aleph": "/projects/aleph/how-it-works/",
        "fantastic-leagues": "/projects/fantastic-leagues/ai-insights/",
        "judge-tool": "/projects/judge-tool/tech/",
    }

    def test_every_deep_dive_has_cross_project_nav_with_canonical_links(self):
        """Combined presence + href assertion (merged 2026-04-28 from two
        separate tests after /ce:review flagged the duplicate iteration)."""
        # Sanity: 12 deep-dives (4 aleph + 5 fl + 3 judge-tool)
        assert len(self.DEEP_DIVES) == 13, (
            f"Expected 13 deep-dive pages, found {len(self.DEEP_DIVES)}: {self.DEEP_DIVES}"
        )
        failures = []
        for f in self.DEEP_DIVES:
            _, body = fetch(f)
            if 'class="cross-project-nav"' not in body:
                failures.append(f"{f}: missing cross-project-nav")
                continue
            for slug, expected_href in self.EXPECTED_LINKS.items():
                if expected_href not in body:
                    failures.append(f"{f}: missing canonical href {expected_href}")
        assert not failures, "Cross-project nav drift:\n" + "\n".join(failures)

    def test_current_project_is_marked_aria_current(self):
        """Within the cross-project nav, exactly one chip should carry
        aria-current='page' — the slug of the page being viewed."""
        failures = []
        for f in self.DEEP_DIVES:
            _, body = fetch(f)
            slug = f.split("/")[1]  # projects/<slug>/...
            # Find the cross-project-nav block specifically
            block_match = re.search(
                r'<nav class="cross-project-nav"[^>]*>(.*?)</nav>',
                body, re.DOTALL,
            )
            if not block_match:
                failures.append(f"{f}: cross-project-nav block not found")
                continue
            block = block_match.group(1)
            # Inside the block, exactly one anchor should have aria-current
            current_anchors = re.findall(r'<a[^>]*aria-current="page"[^>]*>', block)
            if len(current_anchors) != 1:
                failures.append(f"{f}: expected 1 aria-current chip, found {len(current_anchors)}")
                continue
            # The aria-current chip's href should match the current slug
            anchor = current_anchors[0]
            if f"/projects/{slug}/" not in anchor:
                failures.append(f"{f}: aria-current chip points at wrong project")
        assert not failures, "aria-current drift:\n" + "\n".join(failures)


# ── Tests: Project doc sync markers ──────────────────────────────
#
# bin/update-project-docs.py splices rendered HTML between CHANGELOG-START/END
# (or ROADMAP-START/END) on each destination page. If the markers ever drift
# out of a destination page, the cron silently skips that page forever. These
# tests enforce the bootstrap invariant: the marker must exist before the
# script can do anything useful.

class TestProjectDocSyncMarkers:
    """Every (slug, doctype) entry in PROJECT_DOCS must have its marker pair."""

    # Mirror of bin/update-project-docs.py's PROJECT_DOCS — kept literal here
    # to catch unintended additions / removals via this test.
    EXPECTED = [
        ("aleph", "changelog"),
        ("aleph", "roadmap"),
        ("fantastic-leagues", "changelog"),
        ("fantastic-leagues", "roadmap"),
        ("judge-tool", "changelog"),
        ("judge-tool", "roadmap"),
    ]

    def test_markers_present_on_destination_pages(self):
        failures = []
        for slug, doctype in self.EXPECTED:
            page = f"projects/{slug}/{doctype}/index.html"
            _, body = fetch(page)
            marker = doctype.upper()
            for tag in (f"<!-- {marker}-START -->", f"<!-- {marker}-END -->"):
                if tag not in body:
                    failures.append(f"{page}: missing {tag}")
        assert not failures, "Project doc sync marker drift:\n" + "\n".join(failures)


# ── Tests: Fantastic Leagues Roadmap internal nav link ───────────
#
# The FL roadmap was promoted from an external link (app.thefantasticleagues.com)
# to an internal sub-page (/projects/fantastic-leagues/roadmap/) once the
# Tsx adapter went live. Every FL deep-dive must carry the internal Roadmap
# link in its project-nav. The external URL still appears INSIDE the FL
# roadmap page (as "View live ↗") but no longer in nav.

class TestFLRoadmapInternalNav:
    FL_DEEP_DIVES = [
        f for f in STANDARD_PAGES if f.startswith("projects/fantastic-leagues/")
    ]
    EXPECTED_HREF = "/projects/fantastic-leagues/roadmap/"

    def test_every_fl_page_has_internal_roadmap_link(self):
        assert self.FL_DEEP_DIVES, "No FL deep-dive pages found — path filter broke"
        failures = []
        for f in self.FL_DEEP_DIVES:
            _, body = fetch(f)
            nav_match = re.search(
                r'<nav class="project-nav"[^>]*>(.*?)</nav>',
                body, re.DOTALL,
            )
            if not nav_match:
                failures.append(f"{f}: project-nav block not found")
                continue
            nav = nav_match.group(1)
            if self.EXPECTED_HREF not in nav:
                failures.append(f"{f}: project-nav missing {self.EXPECTED_HREF}")
            # Internal links must NOT have rel/target attrs — those are for
            # external links. A stale rel/target here would be a leftover from
            # the pre-promotion external href.
            if f'href="{self.EXPECTED_HREF}" target=' in nav:
                failures.append(f"{f}: internal Roadmap link has stale target attr")
        assert not failures, "FL Roadmap nav drift:\n" + "\n".join(failures)

    def test_external_app_url_not_in_fl_navs(self):
        """The pre-promotion external href must not linger in any FL nav.
        It can still appear in `.snapshot-banner` or page body — only nav
        is asserted clean."""
        stale = "https://app.thefantasticleagues.com/roadmap"
        failures = []
        for f in self.FL_DEEP_DIVES:
            _, body = fetch(f)
            nav_match = re.search(
                r'<nav class="project-nav"[^>]*>(.*?)</nav>',
                body, re.DOTALL,
            )
            if not nav_match:
                continue
            if stale in nav_match.group(1):
                failures.append(f"{f}: project-nav still contains stale external href {stale}")
        assert not failures, "Stale external href in nav:\n" + "\n".join(failures)


# ── Tests: Judge Tool branding ────────────────────────────────────

class TestJudgeToolBranding:
    """Regression guard: 'KCBS' must not reappear in Judge Tool project pages.

    The membership section on index.html and calendar event names in
    now/index.html legitimately retain 'KCBS' — these pages are intentionally
    excluded. The project deep-dive pages have no valid reason to use the term.
    """

    JUDGE_TOOL_PAGES = [
        f for f in STANDARD_PAGES
        if f.startswith("projects/judge-tool/")
    ]

    def test_no_kcbs_in_judge_tool_pages(self):
        assert self.JUDGE_TOOL_PAGES, "No judge-tool pages found — path filter broke"
        failures = []
        for f in self.JUDGE_TOOL_PAGES:
            _, body = fetch(f)
            if "KCBS" in body:
                positions = [m.start() for m in re.finditer("KCBS", body)]
                failures.append(f"{f}: 'KCBS' at char positions {positions[:5]}")
        assert not failures, (
            "Legacy KCBS branding must not appear in Judge Tool project pages:\n"
            + "\n".join(failures)
        )


# ── Tests: /now page section structure ───────────────────────────
#
# /07 was rebuilt and /09 renumbered to /08 in cede613. The cron sync
# writes inside marker pairs but should never touch section headers,
# so these assertions are stable against scheduled commits and only
# fail if a manual edit drops/adds a section without renumbering.

class TestNowSectionStructure:
    """/now must have exactly 9 numbered sections in sequence."""

    def test_section_numbers_are_sequential(self):
        _, body = fetch("now/index.html")
        nums = re.findall(r'<span class="nb-section-num">/(\d+)</span>', body)
        # Filter to top-level section markers (some are inside JS strings — those
        # appear with quoted attribute values; the body markers are bare HTML)
        numeric = [int(n) for n in nums]
        # We expect at least the static 9 — additional numbers may appear in
        # script blocks but the first 9 unique values must be /01..../09 in order
        sequential = []
        for n in numeric:
            if not sequential or n == sequential[-1] + 1:
                sequential.append(n)
            else:
                break  # gap — sequence broken
        assert sequential[:9] == list(range(1, 10)), (
            f"Expected /01../09 sequential, got {sequential[:9]}"
        )

    def test_section_09_is_people_follow(self):
        """/09 is the hand-maintained 'people i follow' section."""
        _, body = fetch("now/index.html")
        section_match = re.search(
            r'<span class="nb-section-num">/09</span>\s*<h2 class="nb-section-title">([^<]+)</h2>',
            body, re.DOTALL,
        )
        assert section_match, "Section /09 header not found"
        assert section_match.group(1).strip() == "people i follow"

    def test_section_07_has_three_media_subfeeds(self):
        """/07 must contain watching (Plex), listening (Spotify), reading
        (Goodreads) sub-feeds. Trakt and Letterboxd must NOT appear."""
        _, body = fetch("now/index.html")
        # Find the section-07 block
        section_match = re.search(
            r'<span class="nb-section-num">/07</span>(.*?)<span class="nb-section-num">/08</span>',
            body, re.DOTALL,
        )
        assert section_match, "Section /07 boundary not found"
        section = section_match.group(1)

        # Three feed heads with the expected names
        for name in ("watching", "listening", "reading"):
            assert f"<strong>{name}</strong>" in section, (
                f"Section /07 missing feed: <strong>{name}</strong>"
            )

        # Trakt + Letterboxd were removed
        assert "TRAKT-START" not in section, "TRAKT marker reappeared in /07"
        assert "LETTERBOXD-START" not in section, "LETTERBOXD marker reappeared in /07"

    def test_pondering_questions_numbering_is_continuous(self):
        """The 'questions i'm pondering' list is split into topic groups (baseball,
        nba, rams & browns), each rendered as a SEPARATE <ol class="nb-feed-questions">
        with a hand-maintained `start=` attribute so the visible numbers run
        continuously (1-5, 6-10, 11-13). Those `start` values are a manual invariant:
        add or remove a question in an earlier group and every later group's `start`
        must shift too. Regression guard — a drifted `start` yields duplicated or
        gapped list numbers on the live page (the exact mistake this guards was a
        real edit: start='9' had to become start='11' when the nba group grew)."""
        _, body = fetch("now/index.html")
        blocks = re.findall(
            r'<ol class="nb-feed-questions"([^>]*)>(.*?)</ol>', body, re.DOTALL
        )
        assert len(blocks) >= 2, (
            "expected multiple grouped <ol class='nb-feed-questions'> in the pondering list"
        )
        expected_start = 1
        for i, (attrs, inner) in enumerate(blocks):
            m = re.search(r'start="(\d+)"', attrs)
            actual_start = int(m.group(1)) if m else 1
            assert actual_start == expected_start, (
                f"pondering <ol> #{i} has start={actual_start}, expected {expected_start} "
                f"— list numbering is discontinuous (a group's `start` wasn't bumped "
                f"after a question was added/removed in an earlier group)"
            )
            li_count = len(re.findall(r"<li>", inner))
            assert li_count > 0, f"pondering <ol> #{i} has no <li> questions"
            expected_start += li_count


class TestProjectCardRoadmaps:
    """Roadmap items are config-driven and must survive cron sync cycles.

    Regression guard: roadmap_items in projects-config.json are read by
    bin/update-projects.py and rendered into project cards. A cron run
    should never delete or corrupt these config-driven sections.
    """

    def test_all_active_projects_have_roadmap_section(self):
        """Every active project card must have a roadmap div."""
        _, body = fetch("now/index.html")
        # Find all project cards in the active section
        active_match = re.search(
            r'<!-- ACTIVE-PROJECTS-START -->(.*?)<!-- ACTIVE-PROJECTS-END -->',
            body, re.DOTALL,
        )
        assert active_match, "ACTIVE-PROJECTS markers not found"
        active = active_match.group(1)

        # Count project cards and roadmap sections
        cards = re.findall(r'<article class="nb-proj-card">', active)
        roadmaps = re.findall(r'<div class="nb-proj-roadmap">', active)

        assert len(cards) > 0, "No active project cards found"
        assert len(roadmaps) == len(cards), (
            f"Active section has {len(cards)} cards but only {len(roadmaps)} roadmap divs — "
            "roadmap items were deleted by cron"
        )

    def test_roadmap_items_are_non_empty(self):
        """Each roadmap section must contain at least one list item."""
        _, body = fetch("now/index.html")
        # Find all roadmap sections
        roadmaps = re.findall(
            r'<div class="nb-proj-roadmap">(.*?)</div>',
            body, re.DOTALL,
        )
        assert len(roadmaps) > 0, "No roadmap sections found on /now"

        for i, rm in enumerate(roadmaps):
            items = re.findall(r'<li>([^<]+)</li>', rm)
            assert len(items) > 0, (
                f"Roadmap section {i} has no items — content was deleted"
            )

    def test_roadmap_label_present(self):
        """Each roadmap must have the 'upcoming roadmap features' label."""
        _, body = fetch("now/index.html")
        roadmaps = re.findall(
            r'<div class="nb-proj-roadmap">(.*?)</div>',
            body, re.DOTALL,
        )
        for i, rm in enumerate(roadmaps):
            assert "upcoming roadmap features" in rm, (
                f"Roadmap section {i} missing label — likely corrupted by cron"
            )


# ── Tests: Multi-file structural parity ──────────────────────────
#
# Added 2026-04-28 after /ce:review flagged drift gaps the rest of the
# suite doesn't cover. Static HTML duplication across 16 files means
# any single-file edit can silently desynchronize a duplicated block.
# These tests pin the dropdown menu HTML, the CSP meta-tag content,
# and the deep-dive structural ordering.

class TestStructuralParity:
    """Locks duplicated structural blocks across the site so any drift fails fast."""

    HOMOGENEOUS_CSP_PAGES = [
        f for f in STANDARD_PAGES if f != "now/index.html"
    ]
    NON_DASHBOARD_DEEP_DIVES = [
        f for f in STANDARD_PAGES
        if f.startswith("projects/")
        and f.count("/") >= 3
        and not f.endswith("dashboard/index.html")
    ]
    CSP_META_RE = re.compile(
        r'<meta http-equiv="Content-Security-Policy" content="([^"]+)"',
        re.IGNORECASE,
    )
    DROPDOWN_MENU_RE = re.compile(
        r'<div class="nb-dropdown" role="menu"[^>]*>(.*?)</div>',
        re.DOTALL,
    )

    def test_csp_homogeneous_across_15_pages(self):
        """15 of 16 pages must share an identical CSP. now/index.html is
        intentionally exempt — it adds https://thirstypig.com to connect-src
        for the client-side hitlist fetch (documented in CLAUDE.md)."""
        cspsets = {}
        for f in self.HOMOGENEOUS_CSP_PAGES:
            _, body = fetch(f)
            m = self.CSP_META_RE.search(body)
            assert m, f"{f}: no CSP meta tag found"
            cspsets.setdefault(m.group(1), []).append(f)
        # Exactly one unique CSP value across the homogeneous set
        assert len(cspsets) == 1, (
            "CSP drift across 15 pages — expected one unique value, got:\n"
            + "\n".join(f"  CSP variant ({len(files)} pages): {files[:3]}..."
                       for files in cspsets.values())
        )

    def test_dropdown_menu_html_is_pinned_across_all_pages(self):
        """The [projects ▾] dropdown menu items must be byte-identical
        across all 16 pages — a single-file edit reordering or dropping
        a project would otherwise drift silently."""
        menus = {}
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            m = self.DROPDOWN_MENU_RE.search(body)
            assert m, f"{f}: no dropdown menu block found"
            # Normalize whitespace so indentation differences don't trip parity
            content = re.sub(r'\s+', ' ', m.group(1)).strip()
            menus.setdefault(content, []).append(f)
        assert len(menus) == 1, (
            "Dropdown menu drift across pages — expected one variant, got:\n"
            + "\n".join(f"  variant ({len(files)} pages): {files[:3]}..."
                       for files in menus.values())
        )

    def test_deep_dive_block_order(self):
        """On non-dashboard deep-dive pages, the structural order is
        project-nav → [snapshot-banner →] work-hero. snapshot-banner is
        optional; when present it must fall between project-nav and work-hero.
        Dashboard pages are intentionally exempt."""
        failures = []
        for f in self.NON_DASHBOARD_DEEP_DIVES:
            _, body = fetch(f)
            i_pnav = body.find('class="project-nav"')
            i_snap = body.find('class="snapshot-banner"')
            i_hero = body.find('class="work-hero"')
            if i_pnav == -1 or i_hero == -1:
                failures.append(
                    f"{f}: missing required element — project-nav={i_pnav}, work-hero={i_hero}"
                )
                continue
            if i_snap == -1:
                ok = i_pnav < i_hero
            else:
                ok = i_pnav < i_snap < i_hero
            if not ok:
                failures.append(
                    f"{f}: project-nav={i_pnav}, snapshot-banner={i_snap}, work-hero={i_hero}"
                )
        assert not failures, (
            "Deep-dive block order drifted (expected project-nav → [snapshot-banner →] work-hero):\n"
            + "\n".join(failures)
        )


# ── Tests: Bucket list ───────────────────────────────────────────

class TestBucketList:
    """Bucket list is a flat JSON file rendered client-side on /now and /bucketlist/.
    These tests pin the contract the thirstypig admin writes to and the renderers read from.
    """

    REQUIRED_KEYS = {"id", "title", "note", "status", "completed_date", "priority", "difficulty"}
    VALID_STATUSES = {"todo", "done"}
    VALID_PRIORITIES = {"high", "medium", "low", None}
    VALID_DIFFICULTIES = {"easy", "hard", None}

    def _load(self):
        path = os.path.join(REPO_ROOT, "bucketlist.json")
        with open(path) as f:
            return json.load(f)

    def test_json_parses_and_has_top_level_keys(self):
        data = self._load()
        assert "items" in data, "bucketlist.json missing 'items'"
        assert "last_updated" in data, "bucketlist.json missing 'last_updated'"
        assert isinstance(data["items"], list), "'items' must be a list"

    def test_every_item_has_required_schema(self):
        """Every row must carry the keys the admin and renderers depend on. A missing key
        would silently break either the public renderer (blank pill) or the admin's edit
        form (can't target a row without an id)."""
        data = self._load()
        failures = []
        for i, item in enumerate(data["items"]):
            missing = self.REQUIRED_KEYS - set(item.keys())
            if missing:
                failures.append(f"items[{i}] missing keys: {missing}")
            if item.get("status") not in self.VALID_STATUSES:
                failures.append(f"items[{i}] invalid status: {item.get('status')!r}")
            if item.get("status") == "todo" and item.get("completed_date") is not None:
                failures.append(f"items[{i}] is todo but has completed_date set")
            if item.get("status") == "done":
                cd = item.get("completed_date")
                if cd is None:
                    failures.append(f"items[{i}] is done but completed_date is null/missing")
                else:
                    try:
                        datetime.strptime(cd, "%Y-%m-%d")
                    except (TypeError, ValueError):
                        failures.append(f"items[{i}] completed_date is not a valid ISO date")
            if not isinstance(item.get("title"), str):
                failures.append(f"items[{i}] title is not a string: {type(item.get('title')).__name__}")
            if not item.get("title"):
                failures.append(f"items[{i}] has empty title")
            if not isinstance(item.get("note"), str):
                failures.append(f"items[{i}] note is not a string: {type(item.get('note')).__name__}")
            if item.get("priority") not in self.VALID_PRIORITIES:
                failures.append(f"items[{i}] invalid priority: {item.get('priority')!r}")
            if item.get("difficulty") not in self.VALID_DIFFICULTIES:
                failures.append(f"items[{i}] invalid difficulty: {item.get('difficulty')!r}")
        assert not failures, "bucketlist.json schema violations:\n" + "\n".join(failures)

    def test_ids_are_unique(self):
        """Admin uses id to target rows for edit/delete. Duplicate ids would let the
        admin update the wrong row."""
        data = self._load()
        ids = [item["id"] for item in data["items"]]
        dupes = {x for x in ids if ids.count(x) > 1}
        assert not dupes, f"Duplicate ids in bucketlist.json: {dupes}"

    def test_last_updated_is_valid_iso8601(self):
        """`last_updated` is the contract timestamp the admin must bump on every save.
        Spec says ISO 8601; an unparseable value (e.g. 'yesterday') means the admin shipped
        a bug and downstream consumers can't sort or diff."""
        data = self._load()
        last_updated = data.get("last_updated")
        assert isinstance(last_updated, str), (
            f"last_updated must be a string, got {type(last_updated).__name__}"
        )
        # datetime.fromisoformat in Python <3.11 doesn't accept trailing 'Z'; normalize.
        normalized = last_updated.replace("Z", "+00:00") if last_updated.endswith("Z") else last_updated
        try:
            datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise AssertionError(
                f"last_updated is not valid ISO 8601: {last_updated!r} ({exc})"
            )

    def test_now_has_bucketlist_render_target(self):
        """now/now.js fills #bucketlist-section. If the container is removed from
        now/index.html, the renderer silently no-ops and the top-5 teaser disappears."""
        _, body = fetch("now/index.html")
        assert 'id="bucketlist-section"' in body, (
            "now/index.html missing <section id=\"bucketlist-section\"> render target"
        )

    def test_now_js_links_to_bucketlist_page(self):
        """The /now teaser must link to /bucketlist/ — that link is the only path in
        because there's intentionally no top-nav entry."""
        path = os.path.join(REPO_ROOT, "now/now.js")
        with open(path) as f:
            js = f.read()
        assert "/bucketlist/" in js, "now/now.js missing link to /bucketlist/"

    def test_bucketlist_page_loads_and_references_renderer(self):
        status, body = fetch("bucketlist/index.html")
        assert status == 200, f"/bucketlist/ returned {status}"
        assert "/bucketlist/bucketlist.js" in body, (
            "bucketlist/index.html doesn't reference its renderer script"
        )
        for anchor in ("bucketlist-todo", "bucketlist-done", "bucketlist-updated"):
            assert f'id="{anchor}"' in body, (
                f"bucketlist/index.html missing #{anchor} render target"
            )

    def test_bucketlist_renderer_script_exists(self):
        """The script tag in bucketlist/index.html must resolve. A 404 would leave the
        page stuck on its 'Loading…' placeholder."""
        status, _ = fetch("bucketlist/bucketlist.js")
        assert status == 200, f"/bucketlist/bucketlist.js returned {status}"

    def test_no_top_nav_link_to_bucketlist(self):
        """Per design: the only path into /bucketlist/ is the 'see the full list →' teaser
        on /now. If a top-nav link sneaks in, this test catches it."""
        offenders = []
        for f in STANDARD_PAGES:
            _, body = fetch(f)
            # Look only inside the .nb-nav block (top nav). The /bucketlist/ page itself
            # legitimately uses /bucketlist/ in its <link rel="canonical"> + crumbs.
            nav_match = re.search(r'<header class="nb-nav".*?</header>', body, re.DOTALL)
            if nav_match and "/bucketlist" in nav_match.group(0):
                offenders.append(f)
        assert not offenders, (
            "Top nav references /bucketlist/ on: " + ", ".join(offenders)
        )


class TestQuotes:
    """Quotes are a flat JSON file rendered client-side into /now's /12 section.
    These tests pin the schema the renderer reads from and the contract that
    every quote carries a source (attribution discipline — no anonymous quotes
    slipping in unlabeled)."""

    REQUIRED_KEYS = {"id", "text", "source"}
    OPTIONAL_KEYS = {"original", "lang", "translation", "note", "category", "title", "entries", "link"}
    VALID_LANGS = {"zh", "la", "fr", ""}
    VALID_CATEGORIES = {"idiom", "film", "literature", "proverb", "philosophy", "latin", "poem", ""}

    def _load(self):
        path = os.path.join(REPO_ROOT, "quotes.json")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_json_parses_and_has_top_level_keys(self):
        data = self._load()
        assert "items" in data, "quotes.json missing 'items'"
        assert "last_updated" in data, "quotes.json missing 'last_updated'"
        assert isinstance(data["items"], list), "'items' must be a list"

    def test_every_item_has_required_schema(self):
        """id + text + source are mandatory; any extra key must be a known optional
        one (typo guard). lang/category, when present, must be from the allowed sets
        the renderer + CSS know how to style."""
        data = self._load()
        allowed = self.REQUIRED_KEYS | self.OPTIONAL_KEYS
        failures = []
        for i, item in enumerate(data["items"]):
            missing = self.REQUIRED_KEYS - set(item.keys())
            if missing:
                failures.append(f"items[{i}] missing keys: {missing}")
            unknown = set(item.keys()) - allowed
            if unknown:
                failures.append(f"items[{i}] has unknown keys: {unknown}")
            if not isinstance(item.get("text"), str) or not item.get("text").strip():
                failures.append(f"items[{i}] text is empty or not a string")
            if not isinstance(item.get("source"), str) or not item.get("source").strip():
                failures.append(f"items[{i}] source is empty or not a string")
            if item.get("lang", "") not in self.VALID_LANGS:
                failures.append(f"items[{i}] invalid lang: {item.get('lang')!r}")
            if item.get("category", "") not in self.VALID_CATEGORIES:
                failures.append(f"items[{i}] invalid category: {item.get('category')!r}")
            # A non-empty `original` should carry a `lang` so the renderer can label it.
            if item.get("original", "").strip() and not item.get("lang", "").strip():
                failures.append(f"items[{i}] has original text but no lang label")
            # `entries` (collection / poem) must be a non-empty list of non-empty strings,
            # and such an item must carry a `title` (the card headline + modal heading).
            if "entries" in item:
                entries = item["entries"]
                if not isinstance(entries, list) or not entries:
                    failures.append(f"items[{i}] entries must be a non-empty list")
                elif not all(isinstance(e, str) and e.strip() for e in entries):
                    failures.append(f"items[{i}] entries must all be non-empty strings")
                if not item.get("title", "").strip():
                    failures.append(f"items[{i}] has entries but no title")
            # `link`, when present, must be {url, label} with an http(s) url — the
            # renderer only emits anchors for http/https (XSS / javascript: guard).
            if "link" in item:
                link = item["link"]
                if not isinstance(link, dict) or not isinstance(link.get("url"), str):
                    failures.append(f"items[{i}] link must be an object with a url string")
                elif not re.match(r"^https?://", link["url"], re.IGNORECASE):
                    failures.append(f"items[{i}] link url must be http(s): {link.get('url')!r}")
                elif not isinstance(link.get("label"), str) or not link["label"].strip():
                    failures.append(f"items[{i}] link must have a non-empty label")
        assert not failures, "quotes.json schema violations:\n" + "\n".join(failures)

    def test_collections_and_poem_render_via_entries(self):
        """A collection (many quotes) or poem is one card that expands into a module.
        Pin that the entries-bearing items exist and that the poem is tagged so the
        renderer applies pre-line (line-break-preserving) styling instead of a list."""
        data = self._load()
        by_id = {q["id"]: q for q in data["items"]}
        collections = [q for q in data["items"] if q.get("entries")]
        assert collections, "expected at least one entries-based collection/poem item"
        poems = [q for q in collections if q.get("category") == "poem"]
        assert poems, "expected at least one poem (category='poem') among entries items"
        # The renderer keys off category=='poem'; every poem entry should contain a
        # line break (stanzas are multi-line) — guards against flattening to one line.
        for p in poems:
            assert any("\n" in e for e in p["entries"]), (
                f"poem {p['id']} has no multi-line stanza — pre-line styling would be a no-op"
            )

    def test_ids_are_unique(self):
        data = self._load()
        ids = [item["id"] for item in data["items"]]
        dupes = {x for x in ids if ids.count(x) > 1}
        assert not dupes, f"Duplicate ids in quotes.json: {dupes}"

    def test_every_quote_has_attribution(self):
        """Attribution discipline: every quote must name a source — even if that
        source is the honest 'Source unknown'. Catches a quote being added without
        any provenance, which is the whole point of the section's verification."""
        data = self._load()
        anonymous = [item["id"] for item in data["items"] if not item.get("source", "").strip()]
        assert not anonymous, f"Quotes missing a source: {anonymous}"

    def test_bruce_lee_box_excludes_verified_misattributions(self):
        """The Bruce Lee collection was curated (2026-06-02 attribution verification)
        to drop lines proven NOT his. Pin that curation so a future edit can't silently
        re-add a misattributed quote. Concrete regression this prevents: someone pastes
        the popular 'Bruce Lee quotes' list back in wholesale, reintroducing Goethe /
        Jeremy Taylor / the 1993 film Dragon line, or the embellished 'breaking a board'
        prefix (the real Enter the Dragon line is just 'Boards don't hit back.')."""
        data = self._load()
        bruce = next((q for q in data["items"] if q.get("id") == "bruce-lee"), None)
        assert bruce, "bruce-lee collection item missing"
        blob = " ".join(bruce.get("entries", [])).lower()
        forbidden = {
            "knowing is not enough": "Goethe, not Bruce Lee",
            "friendship caught on fire": "Jeremy Taylor, not Bruce Lee",
            "key to immortality": "1993 film Dragon, not Bruce Lee",
            "there's no challenge in breaking a board": "embellished prefix — real line is just 'Boards don't hit back.'",
        }
        leaked = [f"{phrase!r} ({why})" for phrase, why in forbidden.items() if phrase in blob]
        assert not leaked, (
            "Misattributed lines leaked back into the Bruce Lee box:\n" + "\n".join(leaked)
        )

    def test_goethe_line_is_its_own_attributed_card(self):
        """The 'knowing is not enough' line lives as a standalone card attributed to
        Goethe (not inside the Bruce Lee box). Pins the correct attribution so a future
        edit can't re-credit it to Bruce Lee."""
        data = self._load()
        goethe = next(
            (q for q in data["items"] if "knowing is not enough" in q.get("text", "").lower()),
            None,
        )
        assert goethe, "Goethe 'knowing is not enough' standalone card missing"
        assert "goethe" in goethe.get("source", "").lower(), (
            f"'knowing is not enough' must be attributed to Goethe, got: {goethe.get('source')!r}"
        )
        assert "entries" not in goethe, "Goethe line should be a single quote, not a collection box"

    def test_last_updated_is_valid_iso8601(self):
        data = self._load()
        last_updated = data.get("last_updated")
        assert isinstance(last_updated, str), (
            f"last_updated must be a string, got {type(last_updated).__name__}"
        )
        normalized = last_updated.replace("Z", "+00:00") if last_updated.endswith("Z") else last_updated
        try:
            datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise AssertionError(f"last_updated is not valid ISO 8601: {last_updated!r} ({exc})")

    def test_now_has_quotes_render_target(self):
        """now/now.js fills #quotes-section. If the container is removed from
        now/index.html, the renderer silently no-ops and the /12 section vanishes."""
        _, body = fetch("now/index.html")
        assert 'id="quotes-section"' in body, (
            "now/index.html missing <section id=\"quotes-section\"> render target"
        )

    def test_now_has_quote_modal_dialog(self):
        """The shared <dialog> the cards expand into must be seeded in the HTML;
        the renderer populates it rather than creating it, so a missing element
        means clicking a card does nothing."""
        _, body = fetch("now/index.html")
        assert 'id="quote-modal"' in body, (
            "now/index.html missing <dialog id=\"quote-modal\"> for the expand popup"
        )

    def test_now_js_references_quotes_json(self):
        path = os.path.join(REPO_ROOT, "now/now.js")
        with open(path, encoding="utf-8") as f:
            js = f.read()
        assert "/quotes.json" in js, "now/now.js missing fetch of /quotes.json"


class TestDetailCards:
    """`people i follow` (/09) and the `off the clock` (/06) top items render as cards
    that expand into the shared #detail-modal. now.js clones each card's <template>
    into the modal — so a missing template, trigger, or dialog breaks the popup."""

    def test_detail_modal_present(self):
        _, body = fetch("now/index.html")
        assert 'id="detail-modal"' in body, (
            "now/index.html missing <dialog id=\"detail-modal\"> for the people/off-the-clock popups"
        )

    def test_every_detail_card_has_trigger_and_template(self):
        """Each card needs a .nb-detail-trigger (the open button) and a <template>
        (the modal payload). A card without a template would open an empty modal;
        without a trigger it can't open at all. <template> is used ONLY by detail
        cards on /now, so the counts must line up exactly."""
        _, body = fetch("now/index.html")
        cards = body.count('class="nb-detail-card"')
        triggers = body.count('class="nb-detail-trigger"')
        templates = body.count('<template>')
        assert cards == 14, f"expected 14 detail cards (7 people + 7 off-the-clock), got {cards}"
        assert triggers == cards, f"{triggers} triggers vs {cards} cards — each card needs exactly one"
        assert templates == cards, f"{templates} <template>s vs {cards} cards — each card needs exactly one"

    def test_people_and_off_the_clock_card_counts(self):
        _, body = fetch("now/index.html")
        people = re.search(r'<span class="nb-section-num">/09</span>(.*?)</section>', body, re.DOTALL)
        clock = re.search(
            r'<span class="nb-section-num">/06</span>(.*?)<span class="nb-section-num">/07</span>',
            body, re.DOTALL,
        )
        assert people and people.group(1).count('class="nb-detail-card"') == 7, (
            "expected 7 detail cards in /09 people i follow"
        )
        assert clock and clock.group(1).count('class="nb-detail-card"') == 7, (
            "expected 7 detail cards in /06 off the clock (top list)"
        )

    def test_now_js_wires_detail_modal_via_clone(self):
        """The wiring must clone <template> content (preserves links/<em>, XSS-safe),
        not innerHTML — and must target #detail-modal + .nb-detail-trigger."""
        path = os.path.join(REPO_ROOT, "now/now.js")
        with open(path, encoding="utf-8") as f:
            js = f.read()
        assert "detail-modal" in js, "now.js missing #detail-modal wiring"
        assert "nb-detail-trigger" in js, "now.js missing .nb-detail-trigger selector"
        assert "cloneNode" in js, "detail wiring must clone template content (no innerHTML)"

    def test_off_the_clock_eyebrow_includes_alumni(self):
        """The /06 eyebrow must reflect all card categories including the alumni/previous
        memberships added 2026-06-04. Without 'alumni', the label is misleading since
        3 of the 7 cards are alumni or previous memberships, not board service/arts/sports."""
        _, body = fetch("now/index.html")
        clock = re.search(
            r'<span class="nb-section-num">/06</span>(.*?)<span class="nb-section-num">/07</span>',
            body, re.DOTALL,
        )
        assert clock, "/06 section not found"
        eyebrow = re.search(r'class="nb-section-eyebrow">(.*?)</p>', clock.group(1), re.DOTALL)
        assert eyebrow and "alumni" in eyebrow.group(1), (
            "/06 eyebrow must include 'alumni' — section now has 3 alumni/previous cards"
        )

    def test_off_the_clock_new_cards_have_expected_links(self):
        """The three alumni/previous detail cards added 2026-06-04 must carry their
        canonical site links. Missing links would leave visitors with a popup that has
        no way to learn more — the primary purpose of the modal."""
        _, body = fetch("now/index.html")
        clock = re.search(
            r'<span class="nb-section-num">/06</span>(.*?)<span class="nb-section-num">/07</span>',
            body, re.DOTALL,
        )
        assert clock, "/06 section not found"
        section = clock.group(1)
        assert "tmbaa.org" in section, (
            "tmbaa.org link missing from /06 — USC Marching Band card must link to tmbaa.org"
        )
        assert "www.aquariumofpacific.org" in section, (
            "www.aquariumofpacific.org link missing from /06 — Aquarium card must use canonical www form"
        )


# ── Tests: Homepage minor memberships ────────────────────────────────

class TestMinorMemberships:
    """The three alumni/previous membership cards on the homepage use a visual
    de-emphasis treatment (.nb-membership--minor) and are grouped in a .nb-grid-3
    wrapper so they read as secondary relative to the three primary memberships above."""

    def test_exactly_three_minor_membership_articles(self):
        """Trip-wire: exactly 3 articles carry the --minor modifier. Promotes visual
        hierarchy contract — if one is accidentally promoted or a 4th is added without
        updating this test, it fails explicitly."""
        _, body = fetch("index.html")
        count = body.count('class="nb-membership nb-membership--minor"')
        assert count == 6, (
            f"expected 6 nb-membership--minor articles on homepage (incl. former memberships), got {count} — "
            "update this assertion if intentionally adding/removing a minor membership"
        )

    def test_minor_cards_are_inside_grid_wrapper(self):
        """The six minor cards (incl. former memberships) must stay inside a .nb-grid-3 wrapper
        so they render in a grid rather than stacking like the primary memberships above."""
        _, body = fetch("index.html")
        grid_match = re.search(
            r'<div class="nb-grid-3">(.*?)</div>\s*</section>',
            body, re.DOTALL,
        )
        assert grid_match, "No .nb-grid-3 found inside #memberships section"
        grid_content = grid_match.group(1)
        minor_count = grid_content.count('class="nb-membership nb-membership--minor"')
        assert minor_count == 6, (
            f"expected all 6 minor cards inside .nb-grid-3, found {minor_count}"
        )


# ── Tests: Homepage JSON-LD memberOf ─────────────────────────────────

class TestMemberOfJsonLD:
    """The JSON-LD Person schema on the homepage must accurately reflect all five
    organizational memberships. memberOf drives structured-data rich results on Google
    and is invisible to manual inspection — only a test catches silent drift."""

    @staticmethod
    def _person_node():
        _, body = fetch("index.html")
        p = parse_page(body)
        graph_block = next((b for b in p.json_ld_blocks if '"@graph"' in b), None)
        assert graph_block, "No @graph JSON-LD block on homepage"
        data = json.loads(graph_block)
        person = next((n for n in data["@graph"] if n.get("@type") == "Person"), None)
        assert person, "No Person node in @graph"
        return person

    def test_memberof_contains_five_organizations(self):
        """Five orgs expected: Chinese American Museum, KCBS, USC Marching Band,
        USC Alumni Club of Shanghai, Aquarium of the Pacific."""
        person = self._person_node()
        orgs = person.get("memberOf", [])
        assert len(orgs) == 5, (
            f"expected 5 memberOf entries, got {len(orgs)}: {[o.get('name') for o in orgs]}"
        )

    def test_tmbaa_memberof_entry_has_url(self):
        """TMBAA entry must carry a url field — added as a review fix since the HTML
        links tmbaa.org but the JSON-LD originally omitted it."""
        person = self._person_node()
        tmbaa = next(
            (o for o in person.get("memberOf", []) if "Marching Band" in o.get("name", "")),
            None,
        )
        assert tmbaa, "USC Marching Band Alumni Association not found in memberOf"
        assert tmbaa.get("url"), (
            "USC Marching Band memberOf entry must have a url field (tmbaa.org)"
        )

    def test_aquarium_memberof_url_is_canonical_www(self):
        """Aquarium of the Pacific url must use the www-canonical form to match
        the visible link — review finding 2026-06-04."""
        person = self._person_node()
        aquarium = next(
            (o for o in person.get("memberOf", []) if "Aquarium" in o.get("name", "")),
            None,
        )
        assert aquarium, "Aquarium of the Pacific not found in memberOf"
        url = aquarium.get("url", "")
        assert url.startswith("https://www."), (
            f"Aquarium memberOf url must use https://www. canonical form, got: {url!r}"
        )
