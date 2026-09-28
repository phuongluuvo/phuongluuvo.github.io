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

#: The one page tools/update_site.py writes. It sits in a subfolder of www/
#: like every other source, so the layout is named here once instead of in each
#: test. The news is no longer generated into a page of its own: it is written
#: by hand on the Home page, so there is nothing to keep in step with the
#: publication list and nothing to refresh from ORCID except the papers.
PUBLICATIONS_SRC = os.path.join(SRC, "research", "publications.jemdoc")
GENERATED_SOURCES = (
    ("www/research/publications.jemdoc", PUBLICATIONS_SRC),
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
    as a code-page lookalike.

    The Home page is checked beside the generated one: its news lines carry
    curly quotes, and it is the page with the most non-ASCII text on the site.
    """
    sources = list(GENERATED_SOURCES) + [
        ("www/home/index.jemdoc", os.path.join(SRC, "home", "index.jemdoc")),
    ]
    for label, path in sources:
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

    # Two things that are not in www/ at all: a file dropped straight into the
    # output, and one inside a folder that www/files/ really does have.
    leftover = out / "images" / "deleted-long-ago.png"
    leftover.write_bytes(b"stale")
    ghost = out / "files" / "old.pdf"
    ghost.parent.mkdir(parents=True, exist_ok=True)
    ghost.write_bytes(b"%PDF-1.4 stale")

    module.build(str(out))

    assert not leftover.exists(), "a stale image survived the rebuild"
    assert not ghost.exists(), "a stale PDF survived the rebuild"
    assert (out / "images" / "portrait.jpg").is_file(), "a live asset was removed"

    # And the other direction: a folder wiped from the output has to come back
    # from www/, which is what makes this a mirror and not a one-way dump.
    module.shutil.rmtree(out / "pdf")
    module.build(str(out))
    assert (out / "pdf" / "courses" / "algorithm-optimization" / "lec1.pdf").is_file(), (
        "the rebuild did not restore a folder that www/ still has"
    )


# --------------------------------------------------------------------------- #
# the shared navigation menu
# --------------------------------------------------------------------------- #

def test_pages_sharing_a_menu_render_it_identically(site, page_names):
    """Every page that includes the same menu must render the same links.

    There is one menu for the main site (www/menu.jemdoc), one for the Edge AI
    Lab pages (www/menu-lab.jemdoc) and one for the blog (www/menu-blog.jemdoc),
    so the number of distinct rendered menus must equal the number of
    www/menu*.jemdoc files: no more, and no fewer.
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


def test_the_blog_pages_use_the_blog_menu(site):
    """The blog has a sidebar of its own; the main menu has one entry for it."""
    links = [a.get("href") for a in soup_of(site, "chap1.html").select("#layout-menu a")]
    assert "index.html" in links, "the blog's first post has no Home entry"
    assert "publications.html" not in links, (
        "a blog post is inside the blog but shows the main site's menu"
    )

    main = [a.get("href") for a in soup_of(site, "index.html").select("#layout-menu a")]
    assert "chap1.html" in main, "the main menu no longer lists the blog"


def test_a_page_shows_the_sidebar_of_its_own_site(site, page_names):
    """A page wears the sidebar of the site it belongs to.

    Two sections have a menu of their own -- the Edge AI Lab and the blog -- and
    every other page carries ``www/menu.jemdoc``, whatever folder its source sits
    in. The course pages are ordinary pages of the main site: a course reads like
    the Interests page, not like a site of its own.
    """
    main = [a.get("href") for a in soup_of(site, "index.html").select("#layout-menu a")]
    assert main, "the home page has no menu"

    lab = {name for name in page_names if name.startswith("lab")}
    blog = {"chap1.html", "chap2.html", "chap3.html", "chap4.html", "chap5.html"}
    assert lab, "no lab pages found"
    assert blog <= set(page_names), "the blog posts are not where we expect"

    for name in page_names:
        links = [a.get("href") for a in soup_of(site, name).select("#layout-menu a")]
        if name in lab or name in blog:
            assert links != main, (
                "%s belongs to another site but shows the main menu" % name
            )
        else:
            assert links == main, "%s does not show the main site's menu" % name
        assert "index.html" in links, "%s has no way home in its menu" % name


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
        # Either another site, or a folder of this repository ("pdf/blogs"). A
        # PDF shown inside a page has to come from the same site, which is why
        # the blog and the lecture slides live here rather than on
        # raw.githubusercontent.com -- GitHub will not let a page display those.
        assert address.startswith("https://") or os.path.isdir(
            os.path.join(SRC, *address.split("/"))
        ), "%s: %r is neither a site nor a folder of this repository" % (name, address)
        assert not address.endswith("/"), (
            "%s: the address should not end with a slash: %r" % (name, address)
        )


def test_every_materials_placeholder_is_filled_in(site, page_names):
    """No %%NAME%% may survive into a page, and every course-file link has to
    start at one of the addresses the conf file names.

    A leftover placeholder is a dead link that nothing else notices, because
    "%%ALGORITHM-OPTIMIZATION%%/lec1.pdf" is a relative path that simply does not exist.
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


def test_every_course_page_offers_its_slides_as_downloads(site, page_names):
    """A course page lists its lectures as files, one line each, to download.

    A strip of buttons over a shared frame was tried and dropped: a framed PDF
    hands the reader the browser's own viewer, and these are wanted as files to
    keep. Nothing opens inside the page now, so a course page needs no script and
    no frame at all.
    """
    checked = 0
    for name in page_names:
        soup = soup_of(site, name)
        headings = [h.get_text(strip=True) for h in soup.select("#layout-content h2")]
        if "Slides" not in headings:
            continue
        checked += 1

        assert not soup.select("#layout-content iframe"), (
            "%s shows a PDF in a frame instead of offering it" % name
        )
        assert not soup.select("#layout-content .lectures button"), (
            "%s still carries the old strip of buttons" % name
        )

        links = soup.select("#layout-content a[href$='.pdf']")
        assert len(links) >= 5, (
            "%s offers only %d lecture files" % (name, len(links))
        )
        for link in links:
            label = link.get_text(strip=True)
            assert link.has_attr("download"), (
                "%s: %r is not marked as a download" % (name, label)
            )
            assert (site / link["href"]).is_file(), (
                "%s links to a missing %s" % (name, link["href"])
            )

        jumps = [a.get("href") for a in soup.select("#layout-menu a") if "#" in a.get("href")]
        assert not jumps, (
            "%s: the sidebar should not jump inside the page: %s" % (name, jumps)
        )
    assert checked, "no page has a Slides section, so nothing was checked"


def test_the_first_menu_entry_is_the_link_home(site, page_names):
    """The first line of every menu is the way home, so a visitor on any page
    can get back to it without using the browser button.

    The entry is called "Home". Above it the main menu shows the site name, but
    as a plain heading -- a heading is not a link -- which is why this checks the
    address and not the wording.
    """
    for name in page_names:
        menu = soup_of(site, name).select("#layout-menu .menu-item")
        assert menu, "%s has an empty menu" % name

        first = menu[0].find("a")
        assert first is not None, "%s: the first menu entry is not a link" % name
        assert first.get("href") == "index.html", (
            "%s: the first menu entry should link to the home page" % name
        )


def test_menu_contains_the_expected_entries(site):
    soup = soup_of(site, "index.html")
    menu = soup.find(id="layout-menu")
    # jemdoc replaces spaces in menu labels with non-breaking spaces.
    labels = [a.get_text(strip=True).replace("\xa0", " ") for a in menu.find_all("a")]
    for expected in ("Home", "Blog", "Lab", "Interests", "Publications",
                     "Algorithm Optimization", "Thesis"):
        assert expected in labels, "menu entry %r is missing" % expected

    # The site name and the group names are headings, not links: the owner asked
    # for a separate "Home" entry, and that is the way home. Blog is not among
    # them: it is one entry, like Lab, because the blog has a sidebar of its own.
    headings = [c.get_text(strip=True).replace("\xa0", " ")
                for c in menu.select(".menu-category")]
    for expected in ("Phuong Vo", "Research", "Teaching"):
        assert expected in headings, (
            "menu heading %r is missing: %s" % (expected, headings)
        )

    # These pages were merged into the Home page or renamed, so they must not be
    # advertised any more. A long label must also not be wrapped in {{braces}},
    # which is what used to push it onto a second row.
    for gone in ("Biography", "Faculty", "For Students", "Blogs", "News",
                 "Awards & Grants", "IT545", "Research Interests"):
        assert gone not in labels, "menu entry %r should be gone" % gone

    # Both courses are listed under Teaching, each one page of its own.
    assert "Regression Analysis" in labels, (
        "the Regression Analysis course is not in the menu"
    )


def test_the_lab_sidebar_has_a_heading_and_a_way_home(site):
    """Inside the lab, the sidebar is shaped like the blog's: a Home entry, a
    heading for the section, then one line per page of it."""
    menu = soup_of(site, "lab.html").find(id="layout-menu")
    blocks = menu.find_all("div", recursive=False)
    kinds = ["category" if "menu-category" in (b.get("class") or []) else "item"
             for b in blocks]
    labels = [b.get_text(strip=True).replace("\xa0", " ") for b in blocks]

    assert labels[0] == "Home", "the lab sidebar does not start with Home"
    assert "Edge AI Lab" in labels, "the lab sidebar has no heading: %s" % labels
    at = labels.index("Edge AI Lab")
    assert kinds[at] == "category", "the section name should be a heading"
    assert kinds[at + 1:at + 2] == ["item"], (
        "the lab heading has nothing under it: %s" % labels[at:at + 3]
    )


def test_blog_is_a_group_with_a_post_under_it(site):
    """The blog's own sidebar is a heading with one line per post below it.

    The posts are renamed as they are written, so this checks the shape rather
    than the titles. It also checks that the heading is a heading: jemdoc can
    only nest entries under a line with no brackets.
    """
    menu = soup_of(site, "chap1.html").find(id="layout-menu")
    blocks = menu.find_all("div", recursive=False)
    kinds = ["category" if "menu-category" in (b.get("class") or []) else "item"
             for b in blocks]
    labels = [b.get_text(strip=True).replace("\xa0", " ") for b in blocks]

    assert "Blog" in labels, "the Blog heading is missing: %s" % labels
    at = labels.index("Blog")
    assert kinds[at] == "category", "Blog should be a heading, not a link"
    assert kinds[at + 1:at + 2] == ["item"], (
        "the Blog heading has no post under it: %s" % labels[at:at + 3]
    )


def test_blog_has_a_sidebar_of_its_own_like_the_lab(site):
    """Blog is a site of its own, reached from the main menu like the Lab:
    clicking *Blog* on the main site lands you in the blog, whose own sidebar
    lists the posts and carries a way home."""
    main = [a.get("href") for a in soup_of(site, "index.html").select("#layout-menu a")]
    assert "chap1.html" in main, "the main menu has no Blog entry"

    links = [a.get("href") for a in soup_of(site, "chap1.html").select("#layout-menu a")]
    assert links != main, "a blog post shows the main site's menu instead of its own"
    assert "index.html" in links, "the blog's sidebar has no Home to get back with"
    assert "chap1.html" in links, "the blog's own sidebar does not list the first post"
    assert "publications.html" not in links, "the blog leaked the main site's menu"


def test_the_current_menu_item_is_highlighted(site, page_names):
    """A page highlights its own menu entry, and only that one.

    mathjax-test.html is deliberately not a menu entry -- it is a utility page --
    so nothing must be highlighted when you are on it. The Home page highlights
    the "Home" entry; the site name above it is a heading, not a link.
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

def test_a_blog_post_is_written_text_with_real_mathematics(site):
    """A post is a page of the site, written from its LaTeX chapter.

    It used to be a frame showing a PDF, and then a page built out of pictures
    taken from that PDF. Now the prose is the page's own markup and the
    mathematics is left as LaTeX for MathJax -- selectable, searchable, and
    readable at any size -- with the figures the source names (see
    tools/latex_to_page.py).
    """
    for name in ("chap1.html", "chap2.html", "chap3.html", "chap4.html", "chap5.html"):
        soup = soup_of(site, name)
        assert not soup.select("#layout-content iframe"), (
            "%s shows something in a frame" % name
        )
        assert not soup.select("#layout-content a[href$='.pdf']"), (
            "%s still offers a PDF" % name
        )
        assert soup.select_one("#layout-content .post-meta"), (
            "%s has no line under the title" % name
        )

        prose = soup.select("#layout-content p, #layout-content li")
        assert len(prose) > 20, (
            "%s has almost no text of its own: %d blocks" % (name, len(prose))
        )

        # Mathematics is left as LaTeX for MathJax: the delimiters are in the
        # page, and the page loads MathJax (checked on every page elsewhere).
        assert "$$" in text_of(site, name), (
            "%s has no display mathematics" % name
        )
        assert soup.select("#layout-content .equation"), (
            "%s has no numbered equations" % name
        )

        for image in soup.select("#layout-content figure img"):
            assert (site / image["src"]).is_file(), (
                "%s: figure %s was not published" % (name, image["src"])
            )


def test_a_blog_post_keeps_its_figures_with_their_captions(site):
    """Every figure the chapters refer to is on the page, with its caption."""
    captions = 0
    for name in ("chap1.html", "chap2.html", "chap3.html", "chap4.html", "chap5.html"):
        captions += len(soup_of(site, name).select("#layout-content figcaption"))
    assert captions >= 20, "only %d figure captions on the blog" % captions


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

def test_no_page_counts_visitors(site, page_names):
    """The visit and visitor totals are gone: the footer carries the date only.

    Both a blocked service and a live one used to leave their mark on every
    page, so both spellings are checked here: the script, the spans it wrote
    into, and the placeholder a different counter would have needed. A jemdoc
    section ends at the first BLANK line, so a stray blank line in www/mysite.conf
    silently drops what follows it -- this catches that too.
    """
    for name in page_names:
        text = text_of(site, name)
        lowered = text.lower()
        assert "busuanzi" not in lowered, (
            "%s still loads the visitor counter" % name
        )
        assert "goatcounter" not in lowered, "%s is wired to GoatCounter" % name
        assert "YOURCODE" not in text, (
            "%s: a placeholder is still in the page" % name
        )

        footer = soup_of(site, name).select_one("#footer")
        assert footer is not None, "%s has no footer" % name
        line = footer.get_text(" ", strip=True)
        assert line.startswith("Last updated:"), (
            "%s: the footer is not the date and nothing else: %r" % (name, line)
        )
        assert "visit" not in line.lower(), (
            "%s: the footer still carries a total: %r" % (name, line)
        )


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


def test_home_page_is_the_profile_the_news_and_the_awards(site):
    """Home is the whole front page: a hero, About, the News list and the awards.

    The news used to be generated into a page of its own and the awards into
    another; both were merged here at the site owner's request. The news lines
    are hand-written, so this also pins down the shape they have to keep:

        - 05/2025: Dr. Nguyen has been promoted to a Full Professor.
    """
    soup = soup_of(site, "index.html")

    assert soup.select_one(".hero"), "the home page lost its profile header"

    sections = [h.get_text(strip=True) for h in soup.select("#layout-content h2")]
    assert sections == ["About", "News", "Awards & Grants", "Contact information"], (
        "the home page sections changed: %s" % sections
    )

    for heading in ("Research grants", "Awards and honours", "Patent"):
        assert soup.find("h3", string=heading), (
            "the merged awards list lost its %r part" % heading
        )

    heading = soup.find("h2", string="News")
    assert heading is not None, "the home page has no News section"

    items = []
    for sibling in heading.find_next_siblings():
        if sibling.name == "h2":
            break
        if sibling.name == "ul":
            items.extend(sibling.find_all("li", recursive=False))
    assert items, "the News section on the home page is empty"

    for item in items:
        text = re.sub(r"\s+", " ", item.get_text(" ")).strip()
        assert re.match(r"^(\d{2}/\d{4}|\d{4}):\s", text), (
            "a news line should start with MM/YYYY: or YYYY: -- got %r" % text[:70]
        )

    assert not soup.select("#layout-content .infoblock"), (
        "the student-recruitment box was removed from the home page"
    )


# --------------------------------------------------------------------------- #
# publications
# --------------------------------------------------------------------------- #

def publication_groups(soup):
    """The publications page as {heading: [entry, ...]}, in page order.

    tools/update_site.py writes one <h2> per kind of work, immediately followed
    by that group's <ul class="pubs">, so the heading is the list's own sibling.
    """
    groups = {}
    for head in soup.select("#layout-content h2"):
        title = head.get_text(strip=True)
        listing = head.find_next_sibling("ul")
        assert listing is not None and "pubs" in (listing.get("class") or []), (
            "the %r section has no publication list under it" % title
        )
        groups[title] = listing.select("li")
    return groups


def test_publications_are_one_section_per_kind_of_work(site):
    """Journal articles and conference papers are separate lists, in that order.

    The page was a single list with the kind of work stamped on every entry.
    Splitting it is what the site owner asked for, and the split follows ORCID's
    own work type, so no entry has to be sorted by hand -- and an entry cannot
    end up in two sections or in none.
    """
    soup = soup_of(site, "publications.html")
    headings = [h.get_text(strip=True) for h in soup.select("#layout-content h2")]
    assert headings[:2] == ["Journal articles", "Conference papers"], (
        "the page does not open with the journals and then the conferences: %s"
        % headings
    )

    groups = publication_groups(soup)
    assert set(groups) == set(headings), "a heading has no list under it"
    for heading in ("Journal articles", "Conference papers"):
        assert len(groups[heading]) > 5, (
            "%s holds only %d entries" % (heading, len(groups[heading]))
        )

    # Every entry is on the page once, in one section or another, and no entry
    # is in two lists.
    assert sum(len(v) for v in groups.values()) == len(soup.select("ul.pubs > li"))

    # Where the heading names the kind of work, the entry does not repeat it.
    for heading in ("Journal articles", "Conference papers"):
        repeated = [e for e in groups[heading] if e.select_one(".pub-type")]
        assert not repeated, (
            "%s repeats what its heading already says on %d entries"
            % (heading, len(repeated))
        )


def test_publications_run_newest_first_with_the_date_leading(site):
    """Each section is newest-first, and every entry starts with its date.

    The page used to put each year behind a click-to-open row. A date leading
    every entry does that job now -- the newest work is the first thing seen --
    without making the reader open anything to read a title. The sections are
    separate, so each one is checked on its own.
    """
    soup = soup_of(site, "publications.html")
    assert not soup.select("details.year"), (
        "the publications page still has collapsible year sections"
    )

    groups = publication_groups(soup)
    entries = soup.select("ul.pubs > li")
    assert len(entries) > 20, (
        "expected the generated list, found only %d entries" % len(entries)
    )

    for title, members in groups.items():
        dates = []
        for entry in members:
            ref = entry.select_one(".pub-ref")
            assert ref is not None, (
                "a publication entry is not one reference line: %s" % entry
            )
            date = ref.select_one(".pub-date")
            assert date is not None, "a publication entry has no leading date"
            label = date.get_text(strip=True)
            assert re.match(r"^\((?:\d{2}/\d{4}|\d{4})\)$", label), (
                "a publication date is not (MM/YYYY) or (YYYY): %r" % label
            )
            assert ref.get_text(strip=True).startswith(label), (
                "the date is not the first thing in %r"
                % ref.get_text(strip=True)[:60]
            )
            dates.append(label.strip("()"))

        # A bare year and a month sort together once written as YYYY-MM.
        keys = [p if len(p) == 4 else p[3:] + "-" + p[:2] for p in dates]
        assert keys == sorted(keys, reverse=True), (
            "%s is not newest-first: %s" % (title, dates[:8])
        )


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
        assert entry.select_one(".pub-ref") is not None, (
            "a publication entry is not a single reference line: %s"
            % title.get_text(strip=True)[:60]
        )
        if entry.get("data-source") == "orcid":
            from_orcid += 1
            if not entry.find("a", href=lambda h: h and h.startswith("https://doi.org/")):
                missing.append(title.get_text(strip=True)[:60])

    assert from_orcid, "no ORCID-sourced publication entries found"
    assert not missing, "these ORCID entries have no DOI link: %s" % missing


def test_orcid_entries_link_to_their_doi_and_nothing_else(site):
    """Extra links (pdf, arXiv, slides, code) are opt-in, taken from
    www/publications-extra.bib. A paper imported from ORCID stays clean: one DOI."""
    soup = soup_of(site, "publications.html")
    offenders = []
    for entry in soup.select('ul.pubs > li[data-source="orcid"]'):
        labels = [a.get_text(strip=True) for a in entry.select(".pub-ref a")]
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


def test_the_doi_decides_the_date_and_orcid_only_fills_gaps(monkeypatch):
    """The publisher's date is taken from Crossref, keyed on the DOI.

    ORCID often holds only a year, or the year the entry was deposited, or
    January when the real month was never recorded -- which produced entries
    reading "(2013)" with no month, and a run of (01/YYYY). Crossref has the
    publisher's own date, so it wins whenever there is one; the ORCID date is
    the fallback. This is the bug that made the two disagree.
    """
    module = load_update_module()

    def fake(payload):
        monkeypatch.setattr(module, "get_json", lambda url, timeout=30: payload)

    fake({"message": {"published-print": {"date-parts": [[2014, 6]]},
                      "issued": {"date-parts": [[2013, 1]]}}})
    record = {"doi": "10.1000/x", "year": 2013, "month": 1, "day": None}
    module.enrich_from_crossref(record)
    assert (record["year"], record["month"]) == (2014, 6), (
        "the DOI's date should replace the ORCID one, print before issued"
    )

    # A book chapter whose book is dated 2027 while the chapter itself went
    # online on 9 July 2026: print knows only a year, online knows the day, so
    # the precise one wins. This is what used to print as "(2027)".
    fake({"message": {"published-print": {"date-parts": [[2027]]},
                      "published-online": {"date-parts": [[2026, 7, 9]]},
                      "issued": {"date-parts": [[2026, 7, 9]]}}})
    record = {"doi": "10.1007/978-x", "year": 2027, "month": None, "day": None}
    module.enrich_from_crossref(record)
    assert (record["year"], record["month"]) == (2026, 7), (
        "the most precise date should win over a bare print year"
    )

    # A Crossref date with no month clears an ORCID month rather than leaving a
    # date on the page that nobody can confirm.
    fake({"message": {"issued": {"date-parts": [[2015]]}}})
    record = {"doi": "10.1000/y", "year": 2014, "month": 1, "day": None}
    module.enrich_from_crossref(record)
    assert (record["year"], record["month"]) == (2015, None)

    # With no DOI, and when Crossref has no date at all, ORCID is left alone.
    record = {"doi": "", "year": 2013, "month": 1, "day": None}
    module.enrich_from_crossref(record)
    assert (record["year"], record["month"]) == (2013, 1)

    fake({"message": {}})
    record = {"doi": "10.1000/z", "year": 2013, "month": 1, "day": None}
    module.enrich_from_crossref(record)
    assert (record["year"], record["month"]) == (2013, 1)


def test_the_date_leads_an_entry_in_the_same_shape_as_the_news():
    module = load_update_module()
    assert module.date_label({"year": 2026, "month": 0}) == "(2026)"
    assert module.date_label({"year": 2026, "month": 6}) == "(06/2026)"
    assert module.date_label({"year": 2026, "month": 13}) == "(2026)"
    assert module.date_label({"year": 0}) == ""


def test_the_generator_groups_the_publications_by_kind_of_work():
    """Journal articles, then conference papers, then book chapters, with every
    work under the heading that names it."""
    module = load_update_module()
    page = module.build_page([
        {"type": "conference-paper", "title": "A conference paper", "year": 2020,
         "month": 3, "source": "orcid", "doi": "10.1/x", "venue": "Some Conference"},
        {"type": "journal-article", "title": "A journal paper", "year": 2021,
         "month": 5, "source": "orcid", "doi": "10.1/y", "venue": "Some Journal"},
        {"type": "book-chapter", "title": "A book chapter", "year": 2019,
         "month": 1, "source": "orcid", "doi": "10.1/z", "venue": "A Book"},
        {"type": "preprint", "title": "A preprint", "year": 2022, "month": 2,
         "source": "orcid", "doi": "", "venue": ""},
    ], 0)

    at = {t: page.index("<h2>%s</h2>" % t) for t in
          ("Journal articles", "Conference papers", "Book chapters")}
    order = [at[t] for t in ("Journal articles", "Conference papers",
                             "Book chapters")]
    assert order == sorted(order), "the sections are not in the order asked for"

    assert at["Journal articles"] < page.index("A journal paper") < at["Conference papers"]
    assert at["Conference papers"] < page.index("A conference paper") < at["Book chapters"]
    assert at["Book chapters"] < page.index("A book chapter")

    # The heading names the kind of work, so the entry does not repeat it ...
    journal = page[at["Journal articles"]:at["Conference papers"]]
    assert "pub-type" not in journal, "the section repeats its own heading"

    # ... and a type no section names still reaches the page, saying what it is.
    other = page[page.index("<h2>Other work</h2>"):]
    assert "A preprint" in other, "a work ORCID types as 'preprint' fell off the page"
    assert "pub-type" in other, "the catch-all section does not say what each entry is"


def test_the_generated_page_does_not_talk_about_the_build(site):
    """The Publications page carries the papers and nothing else: no sentence
    explaining which script writes the file.

    The page used to open with one, and it had to avoid every "/" because jemdoc
    reads /text/ as italics and silently swallowed the paths written into it.
    Taking the sentence out removed that trap with it; the file header still says
    who writes the file, where only the owner looks.
    """
    for name in ("publications.html",):
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
    """`--offline --dry-run` walks the whole rendering path using only
    publications-extra.bib, so a broken generator is caught here rather than by
    the deployed site.

    It must also leave the news alone: that list is hand-written on the Home
    page now, so a generator that still emitted one would either duplicate it or
    overwrite it.
    """
    result = subprocess.run(
        [sys.executable, UPDATE, "--offline", "--dry-run"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, "the generator failed:\n%s" % result.stderr
    assert "= Publications" in result.stdout, "no publication page was rendered"
    assert "= News" not in result.stdout, "the generator still writes a news page"


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
    committed would silently disappear from the deployed site.

    Both live in subfolders of www/ now; the paths come from the constants at the
    top of this file so a move only has to be made once.
    """
    names = [label for label, _path in GENERATED_SOURCES]
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
