"""Test-suite for the generated website.

The tests build the site from the .jemdoc sources into a temporary folder and
then check the result: that every page is produced, that the shared menu is
identical everywhere, that no link is broken, that the HTML is well formed, and
so on. None of these tests needs a browser or an internet connection.

Run them with:

    conda activate vtlp
    pytest
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

import html5lib
import pytest
import yaml
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "www")
BUILD = os.path.join(ROOT, "build.py")
BASE_URL = "https://phuongluuvo.github.io/"

#: jemdoc emits a few obsolete-but-harmless attributes; html5lib reports them
#: as parse errors and we do not want the test-suite to fail because of them.
TOLERATED_HTML5LIB_ERRORS = {
    "expected-doctype-but-got-start-tag",
    "unknown-attribute",
    "obsolete-attribute",
}


# --------------------------------------------------------------------------- #
# fixtures and helpers
# --------------------------------------------------------------------------- #

def load_build_module():
    """Import build.py as a module so that its helpers can be unit-tested."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("site_build", BUILD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def site(tmp_path_factory):
    """Build the site once for the whole test session."""
    out = tmp_path_factory.mktemp("site")
    result = subprocess.run(
        [sys.executable, BUILD, "--out", str(out)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        "build.py failed:\n%s\n%s" % (result.stdout, result.stderr)
    )
    return out


@pytest.fixture(scope="session")
def page_names():
    """The .html names that the sources should produce."""
    return sorted(
        name[: -len(".jemdoc")] + ".html"
        for name in os.listdir(SRC)
        if name.endswith(".jemdoc") and name != "menu.jemdoc"
    )


def soup_of(site, name):
    with open(site / name, "r", encoding="utf-8") as handle:
        return BeautifulSoup(handle.read(), "lxml")


def text_of(site, name):
    with open(site / name, "r", encoding="utf-8") as handle:
        return handle.read()


@pytest.fixture(scope="session")
def all_pages(site, page_names):
    return {name: text_of(site, name) for name in page_names}


# --------------------------------------------------------------------------- #
# the build itself
# --------------------------------------------------------------------------- #

def test_build_produces_every_page(site, page_names):
    assert page_names, "no .jemdoc pages found in www/"
    missing = [n for n in page_names if not (site / n).is_file()]
    assert not missing, "these pages were not generated: %s" % missing


def test_generated_html_uses_lf_line_endings(site, page_names):
    for name in page_names:
        data = (site / name).read_bytes()
        assert b"\r\n" not in data, "%s contains CRLF line endings" % name
        assert not data.startswith(b"\xef\xbb\xbf"), "%s starts with a BOM" % name


def test_static_assets_are_copied(site):
    for relative in (
        "css/site.css",
        "images/portrait.svg",
        "files/cv.pdf",
        "files/publications.bib",
        ".nojekyll",
        "CNAME",
    ):
        assert (site / relative).is_file(), "missing asset: %s" % relative


def test_cname_has_the_custom_domain(site):
    assert (site / "CNAME").read_text(encoding="utf-8").strip() == "phuongluuvo.me"


# --------------------------------------------------------------------------- #
# the shared navigation menu
# --------------------------------------------------------------------------- #

def test_every_page_has_the_same_menu(site, page_names):
    menus = {}
    for name in page_names:
        soup = soup_of(site, name)
        menu = soup.find(id="layout-menu")
        assert menu is not None, "%s has no menu" % name
        menus[name] = [a.get("href") for a in menu.find_all("a")]

    reference = menus[page_names[0]]
    for name, links in menus.items():
        assert links == reference, "%s has a different menu than %s" % (
            name, page_names[0],
        )


def test_menu_contains_the_expected_entries(site):
    soup = soup_of(site, "index.html")
    menu = soup.find(id="layout-menu")
    # jemdoc replaces spaces in menu labels with non-breaking spaces.
    labels = [a.get_text(strip=True).replace("\xa0", " ") for a in menu.find_all("a")]
    for expected in (
        "Biography", "News", "About me", "Faculty", "Honors students",
        "Interns", "Prospective Students", "Publications", "Courses",
    ):
        assert expected in labels, "menu entry %r is missing" % expected
    assert any("PhD" in label for label in labels), "no PhD/Master students entry"
    assert any("Awards" in label for label in labels), "no Awards entry"


def test_the_current_menu_item_is_highlighted(site, page_names):
    """A page highlights its own menu entry.

    index.html and mathjax-test.html are deliberately not menu entries (the
    Home page is a menu *category*, and the MathJax test page is a utility
    page), so for those nothing must be highlighted.
    """
    for name in page_names:
        soup = soup_of(site, name)
        menu = soup.find(id="layout-menu")
        links = [a.get("href") for a in menu.find_all("a")]
        current = soup.select("#layout-menu a.current")
        if name in links:
            assert len(current) == 1, "%s highlights %d menu items" % (name, len(current))
            assert current[0].get("href") == name
        else:
            assert not current, (
                "%s is not a menu entry, so nothing should be highlighted" % name
            )


# --------------------------------------------------------------------------- #
# links
# --------------------------------------------------------------------------- #

def test_internal_links_do_not_open_a_new_tab(site, page_names):
    """Regression test: only external links may carry target="blank"."""
    offenders = []
    for name in page_names:
        soup = soup_of(site, name)
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if "://" in href or href.startswith("mailto:"):
                continue
            if anchor.get("target"):
                offenders.append("%s -> %s" % (name, href))
    assert not offenders, (
        "internal links should stay in the same tab: %s" % offenders
    )


def test_external_links_open_a_new_tab(site, page_names):
    checked = 0
    for name in page_names:
        soup = soup_of(site, name)
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if not href.startswith(("http://", "https://")):
                continue
            checked += 1
            assert anchor.get("target") == "blank", (
                "external link %s in %s should open a new tab" % (href, name)
            )
    assert checked > 5, "expected several external links in the demo content"


def test_every_local_link_and_image_resolves(site, page_names):
    """No broken links: every relative href/src must exist on disk."""
    broken = []
    for name in page_names:
        soup = soup_of(site, name)
        targets = []
        for anchor in soup.find_all("a", href=True):
            targets.append(anchor["href"])
        for tag, attribute in (("img", "src"), ("link", "href"), ("script", "src")):
            for element in soup.find_all(tag):
                value = element.get(attribute)
                if value:
                    targets.append(value)

        for target in targets:
            if target.startswith(("data:", "mailto:", "#", "javascript:")):
                continue
            parsed = urllib.parse.urlparse(target)
            if parsed.scheme or parsed.netloc:
                continue          # absolute URL -- cannot check offline
            path = parsed.path
            if not path:
                continue
            if not (site / path).is_file():
                broken.append("%s -> %s" % (name, path))

    assert not broken, "broken local links: %s" % sorted(set(broken))


# --------------------------------------------------------------------------- #
# HTML quality
# --------------------------------------------------------------------------- #

def test_no_bare_ampersands(site, page_names):
    """A raw & that is not an entity makes the HTML invalid."""
    pattern = re.compile(r"&(?!#[0-9]+;|[a-zA-Z][a-zA-Z0-9]*;)")
    offenders = []
    for name in page_names:
        text = text_of(site, name)
        for match in pattern.finditer(text):
            line = text[: match.start()].count("\n") + 1
            offenders.append("%s:%d: %s" % (name, line, text[match.start():match.start() + 30]))
    assert not offenders, "unescaped '&' found: %s" % offenders[:5]


def test_html_parses_without_serious_errors(site, page_names):
    problems = {}
    for name in page_names:
        parser = html5lib.HTMLParser(strict=False)
        parser.parse(text_of(site, name))
        errors = [
            code for (_pos, code, _data) in parser.errors
            if code not in TOLERATED_HTML5LIB_ERRORS
        ]
        if errors:
            problems[name] = sorted(set(errors))
    assert not problems, "HTML5 parse errors: %s" % problems


def test_every_page_has_a_title_and_the_stylesheet(site, page_names):
    for name in page_names:
        soup = soup_of(site, name)
        assert soup.title and soup.title.get_text(strip=True), "%s has no <title>" % name
        assert soup.find("h1"), "%s has no <h1>" % name
        stylesheets = [l.get("href") for l in soup.find_all("link", rel="stylesheet")]
        assert "css/site.css" in stylesheets, "%s does not load the site stylesheet" % name
        assert soup.find(id="footer"), "%s has no footer" % name


# --------------------------------------------------------------------------- #
# MathJax
# --------------------------------------------------------------------------- #

def test_mathjax_is_loaded_on_every_page(site, page_names):
    for name in page_names:
        text = text_of(site, name)
        assert "MathJax-script" in text, "%s does not load MathJax" % name
        assert "tex-mml-chtml.js" in text, "%s has no MathJax build URL" % name
        assert "inlineMath" in text, "%s does not configure inline math" % name


def test_mathjax_test_page_has_inline_and_display_equations(site):
    text = text_of(site, "mathjax-test.html")
    assert r"\(E" in text or r"\(\gamma_k" in text, "no inline equation found"
    assert r"\[" in text and r"\]" in text, "no display equation found"
    # jemdoc converts $...$ to \(...\) and keeps \(...\) for display math.
    assert "$" not in BeautifulSoup(text, "lxml").get_text(), (
        "a raw $ survived conversion -- inline math was not processed"
    )


def test_home_page_has_an_equation(site):
    text = text_of(site, "index.html")
    assert r"\(" in text, "the home page lost its inline equation"
    assert "text-align:center" in text, "the home page lost its display equation"


# --------------------------------------------------------------------------- #
# publications
# --------------------------------------------------------------------------- #

def test_every_bibtex_block_reaches_the_download_file(site):
    page = text_of(site, "publications.html")
    bib = (site / "files" / "publications.bib").read_text(encoding="utf-8")

    page_blocks = page.count('class="codeblock"')
    bib_entries = len(re.findall(r"^@\w+\{", bib, flags=re.MULTILINE))

    assert page_blocks > 0, "the publications page has no code blocks"
    assert page_blocks == bib_entries, (
        "the page shows %d BibTeX blocks but the .bib file has %d entries"
        % (page_blocks, bib_entries)
    )


def test_publications_are_grouped_by_year_newest_first(site):
    soup = soup_of(site, "publications.html")
    years = [
        int(h.get_text(strip=True))
        for h in soup.find_all("h2")
        if h.get_text(strip=True).isdigit()
    ]
    assert years, "no year headings on the publications page"
    assert years == sorted(years, reverse=True), "years are not newest-first: %s" % years


def test_publication_entries_are_split_into_journal_and_conference(site):
    soup = soup_of(site, "publications.html")
    headings = [h.get_text(strip=True) for h in soup.find_all("h3")]
    assert "Journal papers" in headings
    assert "Conference papers" in headings


# --------------------------------------------------------------------------- #
# the placeholder documents
# --------------------------------------------------------------------------- #

def test_placeholder_pdfs_are_valid_pdf_files(site):
    pdfs = sorted((site / "files").glob("*.pdf"))
    assert pdfs, "no placeholder PDFs were generated"
    for path in pdfs:
        data = path.read_bytes()
        assert data.startswith(b"%PDF-"), "%s is not a PDF" % path.name
        assert data.rstrip().endswith(b"%%EOF"), "%s is truncated" % path.name
        assert len(data) > 300, "%s looks too small to be valid" % path.name


# --------------------------------------------------------------------------- #
# repository configuration
# --------------------------------------------------------------------------- #

def test_github_actions_workflow_is_valid_yaml():
    workflow = os.path.join(ROOT, ".github", "workflows", "pages.yml")
    assert os.path.isfile(workflow), "the Pages workflow is missing"
    with open(workflow, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert "jobs" in data
    assert "build" in data["jobs"] and "deploy" in data["jobs"]
    steps = [s.get("uses", "") for s in data["jobs"]["build"]["steps"]]
    assert any("upload-pages-artifact" in s for s in steps)


def test_build_normalizes_crlf_line_endings(tmp_path):
    """build.py must neutralise CRLF, because jemdoc reads blank lines to find
    paragraph boundaries and a CRLF blank line breaks that (this is a Windows
    trap that we hit for real while building this site)."""
    module = load_build_module()
    source = tmp_path / "sample.jemdoc"
    source.write_bytes(b"# comment\r\n= Title\r\nFirst paragraph\r\n\r\nSecond\r\n")
    assert module.read_text_lf(str(source)) == (
        "# comment\n= Title\nFirst paragraph\n\nSecond\n"
    )


def test_every_source_page_is_staged_with_lf(tmp_path):
    """The staging step must convert CRLF sources before jemdoc sees them."""
    module = load_build_module()
    staging = tmp_path / "staging"
    staging.mkdir()
    module.SRC = str(tmp_path / "fake-www")

    fake = tmp_path / "fake-www"
    fake.mkdir()
    (fake / "probe.jemdoc").write_bytes(b"= Probe\r\nA line.\r\n\r\nAnother.\r\n")
    (fake / module.CONF).write_text("[firstbit]\n", encoding="utf-8")

    module.stage_sources(str(staging), ["probe.jemdoc"])
    staged = (staging / "probe.jemdoc").read_bytes()
    assert b"\r\n" not in staged
    assert staged == b"= Probe\nA line.\n\nAnother.\n"
