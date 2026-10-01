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

#: The one page tools/build_publications.py writes, from www/data/publications.bib.
#: It sits in a subfolder of www/ like every other source, so the layout is named
#: here once instead of in each test. Nothing else is generated: the news and the
#: pages that list patents, awards, projects and theses are hand-written.
PUBLICATIONS_SRC = os.path.join(SRC, "profile", "publications.jemdoc")
GENERATED_SOURCES = (
    ("www/profile/publications.jemdoc", PUBLICATIONS_SRC),
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

    The Home page is checked beside the generated one. A source written entirely
    in ASCII is skipped rather than failed: there is nothing in it to compare,
    and what the test is for is non-ASCII text that IS there surviving the build.
    At least one source has to carry some, or it is checking nothing at all.
    """
    sources = list(GENERATED_SOURCES) + [
        ("www/home/index.jemdoc", os.path.join(SRC, "home", "index.jemdoc")),
    ]
    checked = 0
    for label, path in sources:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
        expected = sorted({char for char in source if ord(char) > 127})
        if not expected:
            continue
        checked += 1

        built = text_of(site, os.path.basename(label).replace(".jemdoc", ".html"))
        for char in expected:
            assert char in built, (
                "%s: %r did not survive the build" % (label, char)
            )
    assert checked, "no source carries a non-ASCII character to check"


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


def test_the_lab_pages_are_pages_of_the_main_site(site):
    """The lab has no sidebar of its own any more: it is a section of the site,
    reached from the main menu like Research or Teaching.

    It used to be a site of its own with ``www/menu-lab.jemdoc``, which meant a
    reader could be inside the lab and unable to see the publications.
    """
    main = [a.get("href") for a in soup_of(site, "index.html").select("#layout-menu a")]
    for name in ("lab.html", "members.html", "projects.html", "news.html"):
        links = [a.get("href") for a in soup_of(site, name).select("#layout-menu a")]
        assert links == main, "%s does not show the main site's menu" % name
        assert "publications.html" in links, (
            "a lab page cannot reach the publications"
        )
    assert not os.path.isfile(os.path.join(SRC, "menu-lab.jemdoc")), (
        "the lab still has a sidebar of its own"
    )


def test_the_blog_pages_use_the_blog_menu(site):
    """The blog has a sidebar of its own; the main menu has one entry for it."""
    links = [a.get("href") for a in soup_of(site, "linear-programming.html").select("#layout-menu a")]
    assert "index.html" in links, "the blog's first post has no Home entry"
    assert "publications.html" not in links, (
        "a blog post is inside the blog but shows the main site's menu"
    )

    main = [a.get("href") for a in soup_of(site, "index.html").select("#layout-menu a")]
    assert "linear-programming.html" in main, "the main menu no longer lists the blog"

def test_a_page_shows_the_sidebar_of_its_own_site(site, page_names):
    """A page wears the sidebar of the site it belongs to.

    One section has a menu of its own -- the blog -- and every other page carries
    ``www/menu.jemdoc``, whatever folder its source sits in. The lab and the
    course pages are ordinary pages of the main site now: a course reads like the
    Interests page, not like a site of its own.
    """
    main = [a.get("href") for a in soup_of(site, "index.html").select("#layout-menu a")]
    assert main, "the home page has no menu"

    blog = {"linear-programming.html", "convex-functions.html", "convex-optimization.html", "first-order-algorithms.html", "duality.html"}
    assert blog <= set(page_names), "the blog posts are not where we expect"

    for name in page_names:
        links = [a.get("href") for a in soup_of(site, name).select("#layout-menu a")]
        if name in blog:
            assert links != main, (
                "%s belongs to another site but shows the main menu" % name
            )
        else:
            assert links == main, "%s does not show the main site's menu" % name
        assert "index.html" in links, "%s has no way home in its menu" % name


def test_every_page_shows_something(site, page_names):
    """Every page carries content, and it is the page's own, not an empty shell.

    Whether a page opens with a heading is the site owner's to decide: the blog
    posts are titled by tools/latex_to_page.py, several pages are written without
    a ``= Title`` line at all, and the Research Interests page is a bare list.
    What no page may be is blank, so this holds on to content that is there and
    is longer than a stray label. The blog posts take their title from
    tools/latex_to_page.py, which writes it as the page's ``<h1>``.
    """
    for name in page_names:
        soup = soup_of(site, name)
        content = soup.find(id="layout-content")
        assert content is not None, "%s has no content area" % name

        blocks = content.select("p, ul, ol, dl, table, figure, pre, h1, h2, h3, h4")
        assert blocks, "%s shows nothing but its sidebar" % name

        text = content.get_text(" ", strip=True)
        assert len(text) > 80, "%s has almost no words on it" % name


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
    for expected in ("Home", "Blog", "Interests", "Publications", "Supervision",
                     "Lab", "Members", "Projects", "News",
                     "Algorithm Optimization", "Thesis"):
        assert expected in labels, "menu entry %r is missing" % expected

    # The site name and the group names are headings, not links: the owner asked
    # for a separate "Home" entry, and that is the way home. Blog is not among
    # them: it is one entry, like the lab pages, because the blog has a sidebar of
    # its own.
    headings = [c.get_text(strip=True).replace("\xa0", " ")
                for c in menu.select(".menu-category")]
    for expected in ("Phuong Vo", "Research", "Teaching"):
        assert expected in headings, (
            "menu heading %r is missing: %s" % (expected, headings)
        )

    # These pages were merged into other pages, left the menu or were deleted, so
    # they must not be advertised any more. A long label must also not be wrapped
    # in {{braces}}, which is what used to push it onto a second row.
    for gone in ("Biography", "Faculty", "For Students", "Blogs",
                 "Awards & Grants", "IT545", "Research Interests",
                 "Awards", "Patents", "Gallery"):
        assert gone not in labels, "menu entry %r should be gone" % gone

    # Both courses are listed under Teaching, each one page of its own.
    assert "Regression Analysis" in labels, (
        "the Regression Analysis course is not in the menu"
    )

    # The profile pages sit under the site name, above the Research heading, and
    # the lab's pages under it: that is the order the owner asked for.
    assert labels.index("Publications") < labels.index("Lab"), (
        "the publications are not listed above the lab"
    )
    assert headings.index("Phuong Vo") < headings.index("Research"), (
        "the group order changed"
    )


def test_blog_is_a_group_with_a_post_under_it(site):
    """The blog's own sidebar is a heading with one line per post below it.

    The posts are renamed as they are written, so this checks the shape rather
    than the titles. It also checks that the heading is a heading: jemdoc can
    only nest entries under a line with no brackets.
    """
    menu = soup_of(site, "linear-programming.html").find(id="layout-menu")
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
    assert "linear-programming.html" in main, "the main menu has no Blog entry"

    links = [a.get("href") for a in soup_of(site, "linear-programming.html").select("#layout-menu a")]
    assert links != main, "a blog post shows the main site's menu instead of its own"
    assert "index.html" in links, "the blog's sidebar has no Home to get back with"
    assert "linear-programming.html" in links, "the blog's own sidebar does not list the first post"
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
    for name in ("linear-programming.html", "convex-functions.html", "convex-optimization.html", "first-order-algorithms.html", "duality.html"):
        soup = soup_of(site, name)
        assert not soup.select("#layout-content iframe"), (
            "%s shows something in a frame" % name
        )
        assert not soup.select("#layout-content a[href$='.pdf']"), (
            "%s still offers a PDF" % name
        )
        # The contents list is the rail in the sidebar, not a list at the top of
        # the post, and every entry in it leads to a heading on the page.
        assert not soup.select("#layout-content .toc"), (
            "%s still opens with a list of its own" % name
        )
        entries = soup.select("#layout-content .rail a")
        assert len(entries) >= 2, (
            "%s has no contents rail" % name
        )
        for entry in entries:
            assert entry["href"].startswith("#"), (
                "%s: contents entry %s does not point into the page"
                % (name, entry["href"])
            )
            assert soup.select_one(entry["href"]), (
                "%s: contents points at %s, which is not on the page"
                % (name, entry["href"])
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
    for name in ("linear-programming.html", "convex-functions.html", "convex-optimization.html", "first-order-algorithms.html", "duality.html"):
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
    # The publications list carries no links at all any more -- the DOIs and the
    # Scholar/ORCID row were removed at the owner's request -- so what is left is
    # the profile header and the two course pages.
    assert checked >= 3, "expected several external links in the demo content"


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


def test_home_page_is_the_profile_and_its_sections(site):
    """Home is the profile: a hero header, and the sections the owner keeps there.

    What the page contains is the site owner's to change -- sections have been
    merged into it and taken out of it -- so what this holds on to is the shape
    the rest of the site depends on: the hero header, an About section, and the
    Contact section. The news list, when there is one, is hand-written, and this
    pins down the shape of its lines:

        - 05/2025: Dr. Nguyen has been promoted to a Full Professor.
    """
    soup = soup_of(site, "index.html")

    assert soup.select_one(".hero"), "the home page lost its profile header"

    headings = [h.get_text(strip=True) for h in soup.select("#layout-content h1, "
                                                           "#layout-content h2")]
    assert any("about" in heading.lower() for heading in headings), (
        "the home page has no About section: %s" % headings
    )
    assert "Contact information" in headings, (
        "the home page lost its Contact section: %s" % headings
    )

    news = [heading for heading in headings if heading.lower() == "news"]
    if news:
        heading = soup.find(["h1", "h2"], string="News")
        items = []
        for sibling in heading.find_next_siblings():
            if sibling.name in ("h1", "h2"):
                break
            if sibling.name == "ul":
                items.extend(sibling.find_all("li", recursive=False))
        assert items, "the News section on the home page is empty"

        for item in items:
            text = re.sub(r"\s+", " ", item.get_text(" ")).strip()
            assert re.match(r"^(\d{2}/\d{4}|\d{4}):\s", text), (
                "a news line should start with MM/YYYY: or YYYY: -- got %r" % text[:70]
            )


# --------------------------------------------------------------------------- #
# publications
# --------------------------------------------------------------------------- #

def publication_sections(soup):
    """The publications page as {heading: [(year, [entry, ...]), ...]}.

    tools/build_publications.py writes one <h2> per kind of work, a <h3> per year
    under it, and that year's <ul class="pubs"> under the heading of each, so all
    three are read together here.
    """
    sections = {}
    heading = None
    for node in soup.select("#layout-content > h2, #layout-content > h3, "
                            "#layout-content > ul"):
        if node.name == "h2":
            heading = node.get_text(strip=True)
            sections[heading] = []
        elif node.name == "h3":
            sections[heading].append((node.get_text(strip=True), []))
        else:
            if not sections[heading]:
                sections[heading].append(("", []))
            sections[heading][-1][1].extend(node.select("li"))
    return sections


def test_publications_are_one_section_per_kind_of_work(site):
    """Journals, conferences, chapters, and the national ones after them.

    The page was a single list with the kind of work stamped on every entry.
    Splitting it is what the site owner asked for, and the kind comes from the
    BibTeX entry type, so no entry is sorted by hand and none can end up in two
    sections or in none.
    """
    soup = soup_of(site, "publications.html")
    headings = [h.get_text(strip=True) for h in soup.select("#layout-content > h2")]
    assert headings == ["Journal Articles", "Conference Papers", "Book Chapters",
                        "National Journal Articles", "National Conference Papers"], (
        "the sections are not the five kinds of work, in order: %s" % headings
    )

    sections = publication_sections(soup)
    assert set(sections) == set(headings), "a heading has no list under it"
    for heading, years in sections.items():
        assert years, "%s has no entries" % heading
        for year, members in years:
            assert members, "%s, %s has an empty year" % (heading, year)

    assert len(sections["Journal Articles"]) >= 5, (
        "the journals are not grouped by year"
    )
    journals = sum(len(m) for _y, m in sections["Journal Articles"])
    assert journals > 10, "only %d journal articles" % journals

    # Every entry is on the page once, in one section or another.
    total = sum(len(m) for years in sections.values() for _y, m in years)
    assert total == len(soup.select("#layout-content li")), (
        "the sections do not add up to the list on the page"
    )
    assert total > 40, "only %d references" % total


def test_publications_are_grouped_by_year_newest_first(site):
    """Inside a section the years run downwards, and every entry sits under its
    own year, so the heading above a reference is the year that reference ends
    with. That is what makes the page scannable without reading every title.
    """
    soup = soup_of(site, "publications.html")
    sections = publication_sections(soup)
    assert len(sections) == 5

    for heading, years in sections.items():
        labels = [int(year) for year, _members in years if year.isdigit()]
        assert labels == sorted(labels, reverse=True), (
            "%s is not newest-first: %s" % (heading, [y for y, _m in years])
        )
        for year, members in years:
            for entry in members:
                text = re.sub(r"\s+", " ", entry.get_text(" ", strip=True))
                assert text, "an empty reference sits under %s, %s" % (heading, year)
                assert ", %s" % year in text, (
                    "%s holds a reference that does not end in %s: %s"
                    % (heading, year, text[:80])
                )


def test_every_reference_is_a_complete_citation(site):
    """Authors, title, venue, pages and year on every entry: the page is a
    reference list, and a reference missing half of itself is worse than no entry.

    There are no links at all. A DOI used to be printed after each entry and was
    removed at the owner's request: the list is for reading, and a bare URL in
    jemdoc prose is a trap besides -- its "/" pairs with the "/" of the italics
    that follow and quietly italicises the rest of the page.
    """
    soup = soup_of(site, "publications.html")
    entries = soup.select("#layout-content li")
    assert len(entries) > 40, (
        "expected the BibTeX list, found only %d entries" % len(entries)
    )

    assert not soup.select('#layout-content a[href^="https://doi.org/"]'), (
        "the reference list still links DOIs"
    )

    for entry in entries:
        text = re.sub(r"\s+", " ", entry.get_text(" ", strip=True))
        assert entry.find("i") is not None, "an entry has no venue: %s" % text[:60]
        assert entry.find("b") is not None, (
            "an entry does not mark the owner's name: %s" % text[:60]
        )
        assert "\u201c" in text, "an entry has no quoted title: %s" % text[:60]
        assert re.search(r", (19|20)\d\d", text), (
            "an entry does not end in a year: %s" % text[:60]
        )


def test_the_owner_is_the_only_name_set_in_bold(site):
    """Bold marks the site owner's own name in the author list, wherever it sits
    in it. A co-author whose surname is also Vo must not go bold with it.
    """
    soup = soup_of(site, "publications.html")
    bold = soup.select("#layout-content li b")
    assert len(bold) > 40, "only %d entries mark her name" % len(bold)

    wrong = [b.get_text(strip=True) for b in bold
             if "Vo" not in b.get_text() or "Phuong" not in b.get_text()]
    assert not wrong, "these names are bold and are not hers: %s" % wrong[:5]


# --------------------------------------------------------------------------- #
# the builder (tools/build_publications.py), tested without writing anything
# --------------------------------------------------------------------------- #

BUILDER = os.path.join(ROOT, "tools", "build_publications.py")


def load_publications_module():
    """Import tools/build_publications.py so its helpers can be tested on their
    own, without writing a file."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_publications", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_builder_reads_bibtex_entries():
    """The file is BibTeX: entries, fields, %-comments, and a brace in a value."""
    module = load_publications_module()
    entries = module.parse_entries(
        "% a comment, not an entry\n"
        "@article{key1,\n"
        "  author  = {Vo, Phuong Luu and Le, Tuan Anh},\n"
        "  title   = {A {LoRA} study},\n"
        "  journal = {Some Journal},\n"
        "  year    = {2026},\n"
        "}\n"
        "@inproceedings{key2,\n"
        "  title = {Another}, year = {2025}, doi = {10.1/x}}\n")

    assert [kind for kind, _fields in entries] == ["article", "inproceedings"], (
        "the entry types were not read"
    )
    assert entries[0][1]["key"] == "key1"
    assert entries[0][1]["title"] == "A {LoRA} study", (
        "braces inside a value are part of the title"
    )
    assert entries[0][1]["author"] == "Vo, Phuong Luu and Le, Tuan Anh"
    assert entries[1][1]["doi"] == "10.1/x", (
        "an entry whose closing brace is on the last line was cut short"
    )


def test_the_builder_reads_both_name_orders():
    """Pasted from a publisher the names read 'Family, Given'; typed by hand they
    are often 'Given Family'. Both are understood and both print the same way."""
    module = load_publications_module()
    assert module.split_names("Vo, Phuong Luu and Le, Tuan Anh") == [
        ("Vo", "Phuong Luu"), ("Le", "Tuan Anh")]
    assert module.split_names("Phuong Luu Vo and Tuan Anh Le") == [
        ("Vo", "Phuong Luu"), ("Le", "Tuan Anh")]
    assert module.render_authors("Nguyen, Toan Van and Vo, Phuong Luu") == (
        "Toan Van Nguyen, *Phuong Luu Vo*")


def test_the_builder_bolds_her_name_and_not_a_namesake():
    module = load_publications_module()
    assert module.is_owner("Vo", "Phuong Luu") is True
    assert module.is_owner("Vo", "P. L.") is True
    assert module.is_owner("Vo-Thi-Luu", "Phuong") is True
    assert module.is_owner("Vo", "Minh") is False, (
        "a co-author whose surname is Vo went bold"
    )
    assert module.is_owner("Nguyen", "Phuong") is False


def test_the_builder_takes_the_date_from_the_entry():
    module = load_publications_module()
    assert module.entry_date({"year": "2026", "month": "6"}) == (2026, 6)
    assert module.entry_date({"date": "2026-02-14"}) == (2026, 2), (
        "a date field knows more than the year"
    )
    assert module.entry_date({"year": "2019", "month": "sep"}) == (2019, 9)
    assert module.entry_date({"year": "2019"}) == (2019, 0)
    assert module.entry_date({}) == (0, 0)


def test_the_builder_prints_no_links():
    """The reference list is for reading: a DOI field does not become a link, and
    a reference with one ends at its year like any other."""
    module = load_publications_module()
    reference = module.render_reference({
        "author": "Le, Long Tan and Vo, Phuong Luu", "title": "A paper",
        "journal": "A Journal", "year": "2026", "volume": "12",
        "pages": "1--9", "doi": "10.1000/x", "note": "Nafosted 1"})
    assert "doi" not in reference.lower(), reference
    assert "http" not in reference
    assert reference.endswith("2026 (Nafosted 1)."), (
        "the note should still be printed after the year: %r" % reference
    )


def test_the_builder_escapes_what_it_prints():
    """jemdoc reads markup in the text it is given, and passes an entity through.

    A journal whose name holds an ampersand, or a title holding a slash -- "high
    speed and/or long delay" is a real one -- would otherwise turn into markup.
    The slash and the hash are escaped with a backslash rather than as an entity,
    because jemdoc reads the # of &#47; as a comment and dropped the rest of the
    line: half of one title never reached the page that way.
    """
    module = load_publications_module()
    assert module.escape("Telecommunications & Computing") == (
        "Telecommunications &amp; Computing")
    assert module.escape("high speed and/or long delay") == (
        "high speed and\\/or long delay")
    assert module.escape("no #1") == "no \\#1"
    assert "&#" not in module.escape("a/b #c")

    page, total = module.render_page([
        ("article", {"key": "k", "author": "Vo, Phuong Luu", "title": "A & B",
                     "journal": "R & D", "year": "2026"})])
    assert total == 1
    assert "R &amp; D" in page and "A &amp; B" in page


def test_the_builder_never_starts_a_line_with_jemdoc_markup():
    """A wrapped line that begins with "-" is a new bullet to jemdoc, however it
    is indented: one reference, whose conference name had a dash in the middle of
    a line, came out as two entries because of it."""
    module = load_publications_module()
    reference = module.render_reference({
        "author": "Vo, Phuong Luu", "title": "A paper",
        "booktitle": "2011 IEEE Global Telecommunications Conference - GLOBECOM 2011",
        "year": "2011", "pages": "1--5"})
    wrapped = module.wrap(reference)
    continuations = wrapped.splitlines()[1:]
    assert continuations, "the reference did not wrap at all"
    for line in continuations:
        assert line[:1].isspace(), "a continuation is not indented: %r" % line
        assert line.strip()[:1] not in "-.=+*{", (
            "a continuation starts with jemdoc markup: %r" % line
        )


def test_the_builder_writes_one_section_per_kind_and_keeps_the_national_ones_apart():
    """The kind of work comes from the entry type, and kind = {national} moves a
    journal or a conference to the national sections at the end."""
    module = load_publications_module()
    page, total = module.render_page([
        ("inproceedings", {"key": "a", "title": "A conference paper",
                           "booktitle": "Some Conference", "year": "2020"}),
        ("article", {"key": "b", "title": "A journal paper",
                     "journal": "Some Journal", "year": "2021"}),
        ("article", {"key": "c", "title": "A national journal paper",
                     "journal": "Some National Journal", "year": "2019",
                     "kind": "national"}),
    ])

    assert total == 3
    order = [page.index("== %s" % title) for title in (
        "Journal Articles", "Conference Papers", "National Journal Articles")]
    assert order == sorted(order), "the sections are not in the order asked for"
    assert order[0] < page.index("A journal paper") < order[1], (
        "a journal article is not under the journal heading"
    )
    assert page.index("A conference paper") < order[2], (
        "a conference paper is not under the conference heading"
    )
    assert page.index("A national journal paper") > order[2], (
        "kind = {national} did not move the entry to the national section"
    )
    assert "=== 2021" in page and "=== 2019" in page, (
        "the years are not sub-headings of their section"
    )


def test_the_builder_refuses_to_write_an_empty_page():
    """A parse failure must not empty the live page: the tool says so and stops."""
    module = load_publications_module()
    _page, total = module.render_page([])
    assert total == 0

    result = subprocess.run([sys.executable, BUILDER, "--check"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, "the committed page is not the one it renders"


def test_the_publications_page_is_what_the_bibtex_file_says():
    """The page is committed, so it can go stale while the .bib moves on. This is
    the check that catches that, and the one the CI job runs."""
    module = load_publications_module()
    with open(module.SOURCE, "r", encoding="utf-8") as handle:
        page, total = module.render_page(module.parse_entries(handle.read()))
    with open(module.OUTPUT, "r", encoding="utf-8") as handle:
        committed = handle.read()

    assert total > 40, "only %d entries in the source" % total
    assert committed == page, (
        "www/profile/publications.jemdoc is not what %s says: run "
        "python tools/build_publications.py"
        % os.path.relpath(module.SOURCE, ROOT)
    )


def test_the_builder_runs_offline_and_says_whether_the_page_is_current():
    """--check is what CI runs, and the tool has no network code at all: the page
    has to be buildable on a machine with no route to anywhere."""
    with open(BUILDER, "r", encoding="utf-8") as handle:
        source = handle.read()
    for module_name in ("urllib", "requests", "http.client", "socket"):
        assert module_name not in source, (
            "the builder reaches for %s; it has to work offline" % module_name
        )

    result = subprocess.run([sys.executable, BUILDER, "--check"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, (
        "the committed page is out of date:\n%s%s" % (result.stdout, result.stderr)
    )
    assert "up to date" in result.stdout


def test_the_generated_page_does_not_talk_about_the_build(site):
    """The Publications page carries the papers and nothing else: no sentence
    explaining which script writes the file.

    The page used to open with one, and it had to avoid every "/" because jemdoc
    reads /text/ as italics and silently swallowed the paths written into it.
    Taking the sentence out removed that trap with it; the file header still says
    who writes the file, where only the owner looks.
    """
    for name in ("publications.html",):
        text = soup_of(site, name).select_one("#layout-content").get_text(" ", strip=True)
        for word in ("generated", "script", "build.py", "BibTeX file"):
            assert word not in text, (
                "%s tells the reader about the build: %r" % (name, word)
            )


def test_the_generated_sources_say_that_they_are_generated():
    for label, path in GENERATED_SOURCES:
        with open(path, "r", encoding="utf-8") as handle:
            head = handle.read(500)
        assert "GENERATED by tools/build_publications.py" in head, (
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


def test_ci_checks_that_the_generated_pages_are_current():
    """The Publications page is generated and committed, so CI has to notice when
    the committed copy and the BibTeX file have drifted apart.

    It must not try to refresh anything from the network: the list is a file in
    this repository, and the tool that renders it fetches nothing.
    """
    workflow = os.path.join(ROOT, ".github", "workflows", "pages.yml")
    with open(workflow, "r", encoding="utf-8") as handle:
        text = handle.read()

    assert "update_site.py" not in text, (
        "the workflow still calls the ORCID updater, which no longer exists"
    )
    assert "build_publications.py" in text, (
        "the workflow does not check the generated Publications page"
    )
    assert "curl" not in text and "wget" not in text, (
        "the workflow reaches for the network to build the site"
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
