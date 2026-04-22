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
EXPECTED_MARKERS = ["WHOOP", "SPOTIFY", "GITHUB", "MLB", "LETTERBOXD", "GOODREADS-READING", "GOODREADS", "FBST", "TRAKT"]


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
            key = d.get("name") or d.get("http-equiv")
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
        for css_file in ["styles.css", "work/work.css"]:
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
        required = ["GitHub", "MLB", "Letterboxd", "Trakt", "Goodreads", "Fantastic Leagues"]
        missing = [src for src in required if src not in body]
        assert not missing, f"Privacy policy missing feed sources: {missing}"

    def test_mentions_ga4(self):
        _, body = fetch("privacy/index.html")
        assert "Google Analytics 4" in body, "Privacy policy does not mention GA4"
        assert "G-B3HW5VBDB3" in body, "Privacy policy does not mention measurement ID"


# ── Tests: Print stylesheet ──────────────────────────────────────

class TestPrintStylesheet:
    """Homepage must have print-related elements."""

    def test_print_only_class_exists(self):
        _, body = fetch("index.html")
        assert "print-only" in body, "Missing .print-only class in index.html"

    def test_resume_pdf_exists(self):
        pdf_path = os.path.join(REPO_ROOT, "resume.pdf")
        assert os.path.exists(pdf_path), "resume.pdf not found in repo root"
