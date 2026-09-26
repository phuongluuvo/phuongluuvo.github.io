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

#: The two pages tools/update_site.py writes, and the file your own announcements
#: go in. They sit in subfolders of www/ like every other source, so the layout is
#: named here once instead of in each test.
PUBLICATIONS_SRC = os.path.join(SRC, "research", "publications.jemdoc")
NEWS_SRC = os.path.join(SRC, "home", "news.jemdoc")
NEWS_EXTRA_SRC = os.path.join(SRC, "data", "news-extra.txt")
GENERATED_SOURCES = (
    ("www/research/publications.jemdoc", PUBLICATIONS_SRC),
    ("www/home/news.jemdoc", NEWS_SRC),
)

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
    """The .html names the sources should produce.

    A ``menu*.jemdoc`` file is *included* by the pages that use it rather than
    built into a page of its own, so it is not one of these -- the same rule
    build.py applies. A source may sit in a subfolder of ``www/``; the folder is
    organisation only and the built address is flat, so what matters is the file
    name.
    """
    module = load_build_module()
    return sorted(module.output_name(relative) for relative in module.find_pages())


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


def test_generated_html_is_valid_utf8(site, page_names):
    """jemdoc writes its HTML with the platform code page unless it is told
    otherwise. On Windows that turned the en dashes and curly quotes in the
    sources into cp1252 bytes, so the page was no longer valid UTF-8."""
    for name in page_names:
        try:
            (site / name).read_bytes().decode("utf-8")
        except UnicodeDecodeError as error:
            pytest.fail("%s is not valid UTF-8: %s" % (name, error))


# --------------------------------------------------------------------------- #
# the indentation of the generated HTML
# --------------------------------------------------------------------------- #

def _plain_text(html):
    """What a page says: no comments, no code, no tags, no runs of whitespace."""
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.DOTALL)
    html = re.sub(r"<(script|style)\b.*?</\1\s*>", " ", html, flags=re.DOTALL | re.I)
    html = re.sub(r"<[^>]*>", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def test_the_generated_pages_are_indented(site, page_names):
    """jemdoc writes its own tags at column zero and passes the tags copied from
    a page through with whatever indentation the page gave them, so the two
    styles ran into each other and the nesting could not be followed.

    A page that is already in the form the build writes must not move at all,
    which is what makes this a check of every page at once.
    """
    module = load_build_module()
    for name in page_names:
        text = text_of(site, name)
        assert module.tidy_html(text) == text, (
            "%s is not in the indented form build.py writes" % name
        )


def test_the_nesting_can_be_followed(site):
    """A cell of the layout table is a child of its row, so it is deeper in."""
    lines = text_of(site, "index.html").split("\n")
    table = next(line for line in lines if 'id="tlayout"' in line)
    menu = next(line for line in lines if 'id="layout-menu"' in line)
    depth = lambda line: len(line) - len(line.lstrip())
    assert menu.startswith(" "), "the menu cell is still at the left margin"
    assert depth(menu) > depth(table), "the menu cell is not inside the table"


def test_indenting_the_html_does_not_change_what_a_page_says(tmp_path):
    """The tidier rewrites the whitespace in front of each line and nothing
    else, so every page has to read the same with it as without it."""
    module = load_build_module()
    plain, tidy = tmp_path / "plain", tmp_path / "tidy"
    module.build(str(plain), tidy=False)
    module.build(str(tidy), tidy=True)

    for name in module.find_pages():
        html = module.output_name(name)
        before = (plain / html).read_text(encoding="utf-8")
        after = (tidy / html).read_text(encoding="utf-8")
        assert _plain_text(before) == _plain_text(after), (
            "%s says something different once it is indented" % html
        )
        assert before.count("\n") == after.count("\n"), (
            "%s gained or lost a line" % html
        )


def test_the_tidier_leaves_a_preformatted_block_alone():
    """A browser keeps every space inside <pre>, so its body must not move."""
    module = load_build_module()
    block = "<pre>a\n   b\n\tc</pre>\n"
    assert block in module.tidy_html("<div>\n" + block + "</div>\n")


def test_the_tidier_never_breaks_a_line_of_text():
    """<a> and friends sit *inside* a line, and splitting the line around one of
    them would push a space into the middle of a sentence."""
    module = load_build_module()
    line = '<p>see <a href="x.html">this</a> and that</p>'
    assert module.tidy_html(line + "\n").strip() == line


def test_the_tidier_is_idempotent():
    module = load_build_module()
    html = "<html>\n<body>\n<div>\n<p>text</p>\n</div>\n</body>\n</html>\n"
    once = module.tidy_html(html)
    assert module.tidy_html(once) == once


def test_non_ascii_text_survives_the_build_unchanged(site):
    """A character in a source page must come out of the build as itself, not
    as a code-page lookalike."""
    for label, path in GENERATED_SOURCES:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
        expected = sorted({char for char in source if ord(char) > 127})
        assert expected, "%s has no non-ASCII character to check" % label

        built = text_of(site, os.path.basename(label).replace(".jemdoc", ".html"))
        for char in expected:
            assert char in built, (
                "%s: %r did not survive the build" % (label, char)
            )


def test_static_assets_are_copied(site):
    for relative in (
        "css/site.css",
        "images/portrait.jpg",
        ".nojekyll",
    ):
        assert (site / relative).is_file(), "missing asset: %s" % relative


def test_a_file_deleted_from_www_disappears_from_the_output(tmp_path):
    """The output is made to *mirror* www/, not merely added to.

    build.py copied the asset folders with shutil.copytree, which writes and
    overwrites but never deletes. A picture or a PDF removed from www/images/ or
    www/files/ therefore sat in the output folder for ever, and every later build
    left it there -- which is how the stale PNGs and PDFs piled up.
    """
    module = load_build_module()
    out = tmp_path / "site"
    module.build(str(out))

    leftover = out / "images" / "deleted-long-ago.png"
    leftover.write_bytes(b"stale")
    ghost = out / "files"
    ghost.mkdir(exist_ok=True)
    (ghost / "old.pdf").write_bytes(b"%PDF-1.4 stale")

    module.build(str(out))

    assert not leftover.exists(), "a stale image survived the rebuild"
    assert not ghost.exists(), (
        "www/files/ is gone, so its output copy should be gone too"
    )
    assert (out / "images" / "portrait.jpg").is_file(), "a live asset was removed"


# --------------------------------------------------------------------------- #
# the shared navigation menu
# --------------------------------------------------------------------------- #

def test_pages_sharing_a_menu_render_it_identically(site, page_names):
    """Every page that includes the same menu must render the same links.

    There is one menu for the main site (www/menu.jemdoc) and one for the Edge
    AI Lab pages (www/menu-lab.jemdoc), so the number of distinct rendered menus
    must equal the number of www/menu*.jemdoc files: no more, and no fewer.
    """
    groups = {}
    for name in page_names:
        soup = soup_of(site, name)
        menu = soup.find(id="layout-menu")
        assert menu is not None, "%s has no menu" % name
        key = tuple(a.get("href") for a in menu.find_all("a"))
        groups.setdefault(key, []).append(name)

    expected = len([
        name for name in os.listdir(SRC)
        if name.endswith(".jemdoc") and name.startswith("menu")
    ])
    assert len(groups) == expected, (
        "expected %d different menus, found %d: %s"
        % (expected, len(groups), [sorted(pages) for pages in groups.values()])
    )
    for links, pages in groups.items():
        assert links, "the menu used by %s has no links" % pages


def test_the_lab_pages_use_the_lab_menu(site):
    """The lab has its own sidebar, and it stays inside the lab."""
    for name in ("lab.html", "lab-members.html", "lab-projects.html", "lab-news.html"):
        links = [a.get("href") for a in soup_of(site, name).select("#layout-menu a")]
        assert "lab.html" in links, "%s has no link back to the lab home" % name
        assert "publications.html" not in links, (
            "%s is a lab page but shows the main site's menu" % name
        )

    main = [a.get("href") for a in soup_of(site, "index.html").select("#layout-menu a")]
    assert "lab.html" in main, "the main menu has no Edge AI Lab entry"
    assert "lab-news.html" not in main, "the main menu leaked the lab menu"


def test_every_page_outside_the_lab_shows_the_main_menu(site, page_names):
    """A page wears the sidebar of the site it belongs to.

    The lab pages carry ``www/menu-lab.jemdoc``; every other page carries
    ``www/menu.jemdoc``, whatever folder its source sits in. A course is an
    ordinary page of the main site -- there is no course sidebar any more.
    """
    lab = {name for name in page_names if name.startswith("lab")}
    assert lab, "no lab pages found"

    main = [a.get("href") for a in soup_of(site, "index.html").select("#layout-menu a")]
    assert main, "the home page has no menu"

    for name in page_names:
        links = [a.get("href") for a in soup_of(site, name).select("#layout-menu a")]
        if name in lab:
            assert links != main, "%s is a lab page but shows the main menu" % name
        else:
            assert links == main, (
                "%s does not show the main site's menu" % name
            )


def test_every_page_has_exactly_one_page_heading(site, page_names):
    """One ``= Title`` per page.

    A stray second one -- from a section typed as ``= Section`` rather than
    ``== Section`` -- makes a second ``<h1>``: invalid, and a heading as loud as
    the page title itself.
    """
    for name in page_names:
        headings = soup_of(site, name).select("h1")
        assert len(headings) == 1, (
            "%s has %d <h1> headings: %s"
            % (name, len(headings), [h.get_text(strip=True) for h in headings])
        )


def test_no_separate_course_section_survives(site):
    """The course list page and the course section menu are both gone."""
    assert not (site / "courses.html").exists(), (
        "courses.html is still in the output"
    )
    assert not os.path.isfile(os.path.join(SRC, "menu-courses.jemdoc")), (
        "www/menu-courses.jemdoc is still there, so a course section still exists"
    )


def test_the_materials_addresses_are_read_from_the_conf_file():
    """Each place the course files live is named once, in www/mysite.conf."""
    module = load_build_module()
    materials = module.read_materials()
    assert materials, "www/mysite.conf has no [materials] settings"
    for name, address in sorted(materials.items()):
        assert address.startswith("https://"), (
            "%s: %r is not an address" % (name, address)
        )
        assert not address.endswith("/"), (
            "%s: the address should not end with a slash: %r" % (name, address)
        )


def test_every_materials_placeholder_is_filled_in(site, page_names):
    """No %%NAME%% may survive into a page, and every course-file link has to
    start at one of the addresses the conf file names.

    A leftover placeholder is a dead link that nothing else notices, because
    "%%IT545%%/lec1.pdf" is a relative path that simply does not exist.
    """
    module = load_build_module()
    addresses = list(module.read_materials().values())
    assert addresses, "no [materials] addresses to check against"

    for name in page_names:
        text = text_of(site, name)
        leftover = module.MATERIALS_TOKEN.findall(text)
        assert not leftover, "%s still contains %s" % (
            name, ", ".join("%%%s%%" % word for word in leftover)
        )
        for target in re.findall(r'href="(https://raw\.githubusercontent\.com[^"]*)"', text):
            assert any(target.startswith(address + "/") for address in addresses), (
                "%s links to %s, which is not under any address in www/mysite.conf"
                % (name, target)
            )


def test_every_course_page_holds_its_own_material(site, page_names):
    """A course is one page: the course information and its own slides, with the
    material in collapsible dropdowns.

    A page qualifies by carrying a Slides heading; there is no course list and no
    course sidebar any more, so this looks at the pages themselves.
    """
    checked = 0
    for name in page_names:
        soup = soup_of(site, name)
        headings = [h.get_text(strip=True) for h in soup.select("#layout-content h2")]
        if "Slides" not in headings:
            continue
        checked += 1
        assert soup.select("#layout-content ul li a[target=blank]"), (
            "%s has a Slides section but no links to the course files" % name
        )
        jumps = [a.get("href") for a in soup.select("#layout-menu a") if "#" in a.get("href")]
        assert not jumps, (
            "%s: the sidebar should not jump inside the page: %s" % (name, jumps)
        )
    assert checked, "no page has a Slides section, so nothing was checked"


def test_every_menu_starts_with_the_site_name_linking_home(site, page_names):
    """There is no "Home" entry: the first line of every menu is the site name,
    and it is the link home."""
    for name in page_names:
        menu = soup_of(site, name).select("#layout-menu .menu-item")
        assert menu, "%s has an empty menu" % name

        first = menu[0].find("a")
        assert first is not None, "%s: the first menu entry is not a link" % name
        assert first.get("href") == "index.html", (
            "%s: the first menu entry should link to the home page" % name
        )
        # jemdoc replaces spaces in menu labels with non-breaking spaces.
        label = first.get_text(strip=True).replace("\xa0", " ")
        assert label == "Phuong Luu Vo", (
            "%s: the first menu entry should be the site name, not %r" % (name, label)
        )


def test_menu_contains_the_expected_entries(site):
    soup = soup_of(site, "index.html")
    menu = soup.find(id="layout-menu")
    # jemdoc replaces spaces in menu labels with non-breaking spaces.
    labels = [a.get_text(strip=True).replace("\xa0", " ") for a in menu.find_all("a")]
    for expected in (
        "Phuong Luu Vo", "News", "Awards & Grants", "Lab",
        "Research Interests", "Publications", "IT545", "Thesis",
    ):
        assert expected in labels, "menu entry %r is missing" % expected

    # These pages were merged away, so they must not be advertised any more.
    for gone in ("Biography", "Faculty", "For Students", "Home"):
        assert gone not in labels, "menu entry %r should be gone" % gone


def test_the_current_menu_item_is_highlighted(site, page_names):
    """A page highlights its own menu entry, and only that one.

    mathjax-test.html is deliberately not a menu entry -- it is a utility page --
    so nothing must be highlighted when you are on it. The site name is a menu
    entry now, so the home page highlights it like any other page would.
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


def test_home_page_is_the_profile_and_nothing_else(site):
    """Home merges the old Home and Biography pages: a hero, About, Contact.

    News has its own page, teaching lives in the course sites, and research lives
    on the Research Interests page, so none of those belongs here.
    """
    soup = soup_of(site, "index.html")

    assert soup.select_one(".hero"), "the home page lost its profile header"

    sections = [h.get_text(strip=True) for h in soup.select("#layout-content h2")]
    assert sections == ["About", "Contact information"], (
        "the home page sections changed: %s" % sections
    )

    assert not soup.select("#layout-content ul.news"), (
        "news has its own page and should not be repeated on the home page"
    )
    assert not soup.select("#layout-content .infoblock"), (
        "the student-recruitment box was removed from the home page"
    )


# --------------------------------------------------------------------------- #
# publications
# --------------------------------------------------------------------------- #

def test_publications_are_grouped_by_year_newest_first(site):
    """Each year is a collapsible <details class="year">, newest first."""
    soup = soup_of(site, "publications.html")
    sections = soup.select("details.year")
    assert sections, "no year sections on the publications page"

    years = []
    for section in sections:
        summary = section.find("summary")
        assert summary is not None, "a year section has no summary"
        text = summary.get_text(strip=True)
        assert text[:4].isdigit(), "year section %r does not start with a year" % text
        years.append(int(text[:4]))

    assert years == sorted(years, reverse=True), "years are not newest-first: %s" % years


def test_every_orcid_publication_links_to_its_doi(site):
    """Entries from ORCID always carry a DOI; hand-added ones may not.

    Each entry records where it came from, so a paper pasted into
    www/publications-extra.bib without a DOI is allowed.
    """
    soup = soup_of(site, "publications.html")
    entries = soup.select("ul.pubs > li")
    assert len(entries) > 20, (
        "expected the generated publication list, found only %d entries" % len(entries)
    )

    missing = []
    from_orcid = 0
    for entry in entries:
        title = entry.select_one(".pub-title")
        assert title is not None, "a publication entry has no title: %s" % entry
        assert entry.select_one(".pub-meta") is not None, (
            "a publication entry has no venue line: %s"
            % title.get_text(strip=True)[:60]
        )
        if entry.get("data-source") == "orcid":
            from_orcid += 1
            if not entry.find("a", href=lambda h: h and h.startswith("https://doi.org/")):
                missing.append(title.get_text(strip=True)[:60])

    assert from_orcid, "no ORCID-sourced publication entries found"
    assert not missing, "these ORCID entries have no DOI link: %s" % missing


def test_publication_year_summaries_agree_with_their_entries(site):
    """A year summary says "N entries"; N entries must really be listed."""
    soup = soup_of(site, "publications.html")
    for section in soup.select("details.year"):
        summary = section.find("summary").get_text(strip=True)
        listed = len(section.select("ul.pubs > li"))
        assert str(listed) in summary, (
            "year summary %r disagrees with the %d entries listed" % (summary, listed)
        )


def test_orcid_entries_link_to_their_doi_and_nothing_else(site):
    """Extra links (pdf, arXiv, slides, code) are opt-in, taken from
    www/publications-extra.bib. A paper imported from ORCID stays clean: one DOI."""
    soup = soup_of(site, "publications.html")
    offenders = []
    for entry in soup.select('ul.pubs > li[data-source="orcid"]'):
        labels = [a.get_text(strip=True) for a in entry.select(".pub-meta a")]
        if labels != ["doi"]:
            title = entry.select_one(".pub-title").get_text(strip=True)[:48]
            offenders.append((title, labels))
    assert not offenders, (
        "ORCID entries should carry only their DOI: %s" % offenders[:5]
    )


def test_extra_links_can_be_added_from_bibtex():
    """arxiv/pdf/slides/code/video/url on a hand-added entry become links."""
    module = load_update_module()
    assert module.bib_links({}) == []

    assert module.bib_links({"arxiv": "{2401.01234}"}) == [
        {"label": "arXiv", "href": "https://arxiv.org/abs/2401.01234"}
    ]
    assert module.bib_links({"pdf": "https://example.org/p.pdf"}) == [
        {"label": "pdf", "href": "https://example.org/p.pdf"}
    ]
    # The order is fixed by BIB_LINKS, and a field that is not a URL is ignored
    # rather than turned into a broken link. `url` is shown as "link".
    assert [l["label"] for l in module.bib_links(
        {"url": "https://a", "code": "https://b", "slides": "10.1000/x"}
    )] == ["code", "link"]


def test_publications_open_the_two_newest_years(site):
    """The current year and the one before it are expanded; the rest collapse.

    This is the same rule the News page uses, so the two pages behave alike.
    """
    soup = soup_of(site, "publications.html")
    sections = soup.select("details.year")
    assert len(sections) > 2, "expected several publication years"

    assert all(s.has_attr("open") for s in sections[:2]), (
        "the two newest years should be open"
    )
    assert not any(s.has_attr("open") for s in sections[2:]), (
        "only the two newest years should be open"
    )


# --------------------------------------------------------------------------- #
# news
# --------------------------------------------------------------------------- #

#: A news date is a year, or a year and month, optionally with a day.
NEWS_DATE_RE = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")


def flat(text):
    """Collapse whitespace so titles can be compared between two pages."""
    return re.sub(r"\s+", " ", text).strip()


def test_news_groups_announcements_by_year_newest_first(site):
    soup = soup_of(site, "news.html")
    years = []
    for element in soup.select("h2.news-year, details.year"):
        head = element.find("summary") if element.name == "details" else element
        text = head.get_text(strip=True)
        assert text[:4].isdigit(), "news section %r does not start with a year" % text
        years.append(int(text[:4]))

    assert years, "the news page has no years"
    assert years == sorted(years, reverse=True), (
        "news years are not newest-first: %s" % years
    )


def test_news_shows_the_recent_years_and_collapses_the_rest(site):
    """The two most recent years are open; older ones sit behind a dropdown."""
    soup = soup_of(site, "news.html")
    open_years = [int(h.get_text(strip=True)[:4]) for h in soup.select("h2.news-year")]
    collapsed = soup.select("details.year")

    assert len(open_years) == 2, (
        "expected exactly two open years, found %d" % len(open_years)
    )
    assert collapsed, "no older year is collapsed"

    collapsed_years = [
        int(d.find("summary").get_text(strip=True)[:4]) for d in collapsed
    ]
    assert set(open_years).isdisjoint(collapsed_years), (
        "a year appears both open and collapsed"
    )
    assert min(open_years) > max(collapsed_years), (
        "a collapsed year is newer than an open one"
    )


def test_news_year_summaries_agree_with_their_entries(site):
    soup = soup_of(site, "news.html")
    for section in soup.select("details.year"):
        summary = section.find("summary").get_text(strip=True)
        listed = len(section.select("ul.news > li"))
        assert listed, "a collapsed year has no announcements"
        assert str(listed) in summary, (
            "year summary %r disagrees with the %d announcements listed"
            % (summary, listed)
        )


def test_every_news_item_is_one_sentence_carrying_its_date(site):
    """Announcements read like this, with the date inside the sentence:

        "Title of the paper" accepted by IEEE INFOCOM 2023 (12/22).

    There is no separate date column, so the date has to be in the text.
    """
    soup = soup_of(site, "news.html")
    items = soup.select("ul.news > li")
    assert len(items) > 20, (
        "expected the generated news list, found only %d announcements" % len(items)
    )

    stamped = 0
    for item in items:
        assert not item.select_one(".news-date"), (
            "the date belongs in the sentence, not in its own column"
        )

        text = flat(item.get_text(" "))
        assert text.endswith(".") or "doi" in text, (
            "an announcement should be one sentence: %r" % text[:80]
        )

        match = re.search(r"\((\d{2})/(\d{2})\)\.", text)
        if match:
            stamped += 1
            assert 1 <= int(match.group(1)) <= 12, (
                "bad month in the stamp of %r" % text[:80]
            )

    assert stamped > 10, (
        "expected most announcements to carry a (MM/YY) stamp, found %d" % stamped
    )


def test_news_runs_newest_first(site):
    """Every announcement carries its full date for reference, and they descend."""
    dates = [item.get("title") for item in soup_of(site, "news.html").select("ul.news > li")]
    assert dates and all(dates), "every announcement should record its date"
    assert dates == sorted(dates, reverse=True), (
        "announcements are not newest-first: %s" % dates[:8]
    )


def test_every_publication_becomes_a_news_item(site):
    """A paper added to ORCID, or pasted into publications-extra.bib, must show
    up in the news by itself -- that is the whole point of generating both pages
    from one source."""
    pubs = soup_of(site, "publications.html")
    news = soup_of(site, "news.html")

    titles = [flat(t.get_text()) for t in pubs.select(".pub-title")]
    assert titles, "no publications found"

    news_text = flat(news.get_text(" "))
    missing = [t for t in titles if t not in news_text]
    assert not missing, (
        "these publications are missing from the news page: %s" % missing[:5]
    )


# --------------------------------------------------------------------------- #
# the generator (tools/update_site.py), tested without any network access
# --------------------------------------------------------------------------- #

UPDATE = os.path.join(ROOT, "tools", "update_site.py")


def load_update_module():
    """Import tools/update_site.py as a module so its helpers can be tested."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("site_update", UPDATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_date_shows_the_month_when_it_is_known():
    module = load_update_module()
    assert module.format_date({"year": 2026, "month": 0}) == "2026"
    assert module.format_date({"year": 2026, "month": 6}) == "2026-06"
    assert module.format_date({"year": 2026, "month": 13}) == "2026"
    assert module.format_date({"year": 0}) == ""


def test_the_announcement_stamp_is_month_then_year():
    """December 2022 -> (12/22), the stamp inside an announcement."""
    module = load_update_module()
    assert module.short_date(2022, 12) == "12/22"
    assert module.short_date(2026, 6) == "06/26"
    assert module.short_date(2026, 0) == "", "no month means no stamp"
    assert module.short_date(0, 6) == ""


def test_news_extra_items_are_parsed(tmp_path):
    module = load_update_module()
    path = tmp_path / "news-extra.txt"
    path.write_text(
        "# a comment\n"
        "\n"
        "2026-10-01 | A new grant, see [the funder](https://example.org/grant).\n"
        "2025 | An announcement with only a year.\n"
        "this line has no date and must be skipped\n",
        encoding="utf-8",
    )
    module.NEWS_INPUT = str(path)
    items = module.read_extra_news()

    assert [item["date_label"] for item in items] == ["2026-10-01", "2025"]
    assert items[0]["year"] == 2026

    links = [part for part in items[0]["parts"] if "link" in part]
    assert links == [{"link": "https://example.org/grant", "label": "the funder"}]


def test_the_generated_pages_do_not_talk_about_the_build(site):
    """Publications and News carry the papers and the announcements, and nothing
    else: no sentence explaining which script writes the file.

    Both pages used to open with one, and it had to avoid every "/" because
    jemdoc reads /text/ as italics and silently swallowed the paths written into
    it. Taking the sentence out removed that trap with it; the file header still
    says who writes the file, where only the owner looks.
    """
    for name in ("publications.html", "news.html"):
        soup = soup_of(site, name)
        loose = [
            p.get_text(" ", strip=True)
            for p in soup.select("#layout-content > p")
            if not p.get("class")
        ]
        assert not loose, (
            "%s still carries a note about the build: %s" % (name, loose)
        )


def test_the_generator_runs_end_to_end_without_any_network_access():
    """`--offline --dry-run` walks the whole rendering path -- publications and
    news -- using only publications-extra.bib, so a broken generator is caught
    here rather than by the deployed site."""
    result = subprocess.run(
        [sys.executable, UPDATE, "--offline", "--dry-run"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, "the generator failed:\n%s" % result.stderr
    assert "= Publications" in result.stdout, "no publication page was rendered"
    assert "= News" in result.stdout, "no news page was rendered"
    assert '<ul class="news">' in result.stdout, "the news page has no announcements"


def test_news_extra_ships_with_every_line_commented_out():
    """Only the documented examples are committed, so no announcement reaches the
    site that the site owner did not write."""
    with open(NEWS_EXTRA_SRC, "r", encoding="utf-8") as handle:
        active = [
            line for line in handle.read().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    assert not active, "www/data/news-extra.txt ships with live lines: %s" % active


def test_home_page_is_left_alone_when_the_markers_are_missing(tmp_path):
    """The Home page is hand-written apart from the marked block. Without the
    markers it must not be touched at all."""
    module = load_update_module()
    page = tmp_path / "index.jemdoc"
    original = "= Home\n\n== Latest news\n\n- a hand-written bullet\n"
    page.write_text(original, encoding="utf-8")
    module.HOME_PAGE = str(page)

    item = {"date_label": "2026", "sort": (2026, 0, 0), "year": 2026,
            "parts": [{"text": "something"}]}
    assert module.sync_home_news([item]) is None
    assert page.read_text(encoding="utf-8") == original


def test_home_page_block_is_replaced_between_the_markers(tmp_path):
    module = load_update_module()
    page = tmp_path / "index.jemdoc"
    page.write_text(
        "= Home\n\n== Latest news\n\n" + module.HOME_NEWS_BEGIN + "\n"
        "~~~\n{}{raw}\n<ul class=\"news\">\n<li>old</li>\n</ul>\n~~~\n"
        + module.HOME_NEWS_END + "\n\n[news.html See all news]\n",
        encoding="utf-8",
    )
    module.HOME_PAGE = str(page)

    item = {"date_label": "2026-05", "sort": (2026, 5, 0), "year": 2026,
            "parts": [{"text": "a brand new paper"}]}
    count, changed = module.sync_home_news([item])

    text = page.read_text(encoding="utf-8")
    assert (count, changed) == (1, True)
    assert "<li>old</li>" not in text
    assert "a brand new paper" in text
    assert text.startswith("= Home\n\n== Latest news\n")
    assert text.rstrip().endswith("[news.html See all news]")

    # Running it again changes nothing.
    assert module.sync_home_news([item]) == (1, False)


def test_the_generator_refuses_to_shrink_the_publication_list():
    """A partial ORCID or Crossref response must never empty the live page: this
    is the guard that protects every automatic deployment."""
    module = load_update_module()
    assert module.would_shrink_the_list(60, 100) is False   # 60% is still fine
    assert module.would_shrink_the_list(59, 100) is True    # below 60% is not
    assert module.would_shrink_the_list(0, 100) is True
    assert module.would_shrink_the_list(4, 0) is False, (
        "with nothing published yet there is nothing to compare against"
    )


def test_count_entries_counts_what_a_previous_run_generated(tmp_path):
    """This count feeds the guard above."""
    module = load_update_module()
    page = tmp_path / "publications.jemdoc"
    page.write_text(
        '<li data-source="orcid">a</li>\n<li data-source="bib">b</li>\n',
        encoding="utf-8",
    )
    assert module.count_entries(str(page), '<li data-source=') == 2
    assert module.count_entries(str(tmp_path / "absent.jemdoc"), '<li data-source=') == 0


def test_write_text_leaves_an_unchanged_file_alone(tmp_path):
    """An unchanged run must not touch the file, so committing never produces a
    phantom diff."""
    module = load_update_module()
    page = tmp_path / "page.txt"
    assert module.write_text(str(page), "same\n") is True
    assert module.write_text(str(page), "same\n") is False
    assert page.read_text(encoding="utf-8") == "same\n"
    assert module.write_text(str(page), "different\n") is True


def test_the_generated_sources_say_that_they_are_generated():
    for label, path in GENERATED_SOURCES:
        with open(path, "r", encoding="utf-8") as handle:
            head = handle.read(500)
        assert "GENERATED by tools/update_site.py" in head, (
            "%s does not warn that it is generated" % label
        )


# --------------------------------------------------------------------------- #
# the placeholder documents
# --------------------------------------------------------------------------- #

def test_every_copied_asset_has_content(site):
    """A zero-byte image or download is an invisible failure: the file is linked,
    and it exists, so no link check notices that it is truncated.

    (This replaced a test for the placeholder PDFs, which were deleted along with
    the CV link. It now covers whatever is in css/, images/ and files/ -- and
    passes when files/ does not exist.)
    """
    empty = [
        str(path.relative_to(site))
        for folder in ("css", "images", "files")
        if (site / folder).is_dir()
        for path in (site / folder).rglob("*")
        if path.is_file() and path.stat().st_size == 0
    ]
    assert not empty, "these assets are empty: %s" % empty


def test_the_images_are_valid(site):
    """A broken image renders as a broken-image icon and nothing else: no build
    error, no failed link, no test failure.

    This was a real bug once: a note added to www/images/portrait.svg contained a
    double hyphen inside an XML comment, which is illegal, and the portrait
    silently disappeared from the page.

    Both kinds are covered -- an SVG has to parse as XML, and a photograph has
    to really be the format its extension claims.
    """
    import xml.etree.ElementTree as ElementTree

    magic = {
        ".jpg": (b"\xff\xd8\xff",),
        ".jpeg": (b"\xff\xd8\xff",),
        ".png": (b"\x89PNG\r\n\x1a\n",),
        ".gif": (b"GIF87a", b"GIF89a"),
        ".webp": (b"RIFF",),
    }

    images = sorted(path for path in (site / "images").iterdir() if path.is_file())
    assert images, "no images were copied into the output"

    for path in images:
        suffix = path.suffix.lower()
        if suffix == ".svg":
            try:
                ElementTree.parse(path)
            except ElementTree.ParseError as error:
                pytest.fail("%s is not valid XML/SVG: %s" % (path.name, error))
        elif suffix in magic:
            head = path.read_bytes()[:8]
            assert any(head.startswith(sig) for sig in magic[suffix]), (
                "%s is not really a %s file" % (path.name, suffix.lstrip("."))
            )
        else:
            pytest.fail("%s is an image type nothing here checks; add it to the "
                        "table in this test" % path.name)


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


def test_ci_refreshes_the_generated_pages_but_tolerates_a_failure():
    """Every push to main deploys, so the CI refresh of the two generated pages
    must be best effort: the committed copies are the fallback."""
    workflow = os.path.join(ROOT, ".github", "workflows", "pages.yml")
    with open(workflow, "r", encoding="utf-8") as handle:
        text = handle.read()

    assert "update_publications.py" not in text, (
        "the workflow still calls the old, renamed script"
    )
    runs = [line for line in text.splitlines()
            if "run:" in line and "update_site.py" in line]
    assert runs, "the workflow no longer refreshes the generated pages"
    for line in runs:
        assert "||" in line, (
            "a failed refresh would fail the deployment; make it best effort "
            "so the committed copies are used"
        )


def test_the_generated_pages_are_committed():
    """CI builds from a fresh checkout, so a generated page that was never
    committed would silently disappear from the deployed site."""
    names = ["www/publications.jemdoc", "www/news.jemdoc"]
    try:
        result = subprocess.run(["git", "ls-files", "--error-unmatch"] + names,
                                cwd=ROOT, capture_output=True, text=True)
    except FileNotFoundError:
        pytest.skip("git is not installed")
    if "not a git repository" in (result.stderr or "").lower():
        pytest.skip("not a git working tree")

    assert result.returncode == 0, (
        "these generated files are not tracked by git: %s" % result.stderr.strip()
    )


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
