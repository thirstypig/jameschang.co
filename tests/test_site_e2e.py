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
EXPECTED_MARKERS = ["WHOOP", "SPOTIFY", "MLB", "GOODREADS-READING", "GOODREADS", "FBST", "PLEX", "PAGE-UPDATED"]


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
        for css_file in ["styles.css", "projects/projects.css"]:
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
    """Homepage must produce a printable résumé."""

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
        assert len(self.DEEP_DIVES) == 12, (
            f"Expected 12 deep-dive pages, found {len(self.DEEP_DIVES)}: {self.DEEP_DIVES}"
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


# ── Tests: /now page section structure ───────────────────────────
#
# /07 was rebuilt and /09 renumbered to /08 in cede613. The cron sync
# writes inside marker pairs but should never touch section headers,
# so these assertions are stable against scheduled commits and only
# fail if a manual edit drops/adds a section without renumbering.

class TestNowSectionStructure:
    """/now must have exactly 8 numbered sections in sequence."""

    def test_section_numbers_are_sequential(self):
        _, body = fetch("now/index.html")
        nums = re.findall(r'<span class="nb-section-num">/(\d+)</span>', body)
        # Filter to top-level section markers (some are inside JS strings — those
        # appear with quoted attribute values; the body markers are bare HTML)
        numeric = [int(n) for n in nums]
        # We expect at least the static 8 — additional numbers may appear in
        # script blocks but the first 8 unique values must be /01..../08 in order
        sequential = []
        for n in numeric:
            if not sequential or n == sequential[-1] + 1:
                sequential.append(n)
            else:
                break  # gap — sequence broken
        assert sequential[:8] == list(range(1, 9)), (
            f"Expected /01../08 sequential, got {sequential[:8]}"
        )

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
        project-nav → snapshot-banner → work-hero. Dashboard pages are
        intentionally exempt (they're prompt-display pages, not snapshots
        of a live page)."""
        failures = []
        for f in self.NON_DASHBOARD_DEEP_DIVES:
            _, body = fetch(f)
            i_pnav = body.find('class="project-nav"')
            i_snap = body.find('class="snapshot-banner"')
            i_hero = body.find('class="work-hero"')
            if not (0 < i_pnav < i_snap < i_hero):
                failures.append(
                    f"{f}: project-nav={i_pnav}, snapshot-banner={i_snap}, work-hero={i_hero}"
                )
        assert not failures, (
            "Deep-dive block order drifted (expected project-nav → snapshot-banner → work-hero):\n"
            + "\n".join(failures)
        )
