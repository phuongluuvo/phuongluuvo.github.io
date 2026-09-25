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


def test_generated_html_is_valid_utf8(site, page_names):
    """jemdoc writes its HTML with the platform code page unless it is told
    otherwise. On Windows that turned the en dashes and curly quotes in the
    sources into cp1252 bytes, so the page was no longer valid UTF-8."""
    for name in page_names:
        try:
            (site / name).read_bytes().decode("utf-8")
        except UnicodeDecodeError as error:
            pytest.fail("%s is not valid UTF-8: %s" % (name, error))


def test_non_ascii_text_survives_the_build_unchanged(site):
    """A character in a source page must come out of the build as itself, not
    as a code-page lookalike."""
    for name in ("publications.jemdoc", "news.jemdoc"):
        with open(os.path.join(SRC, name), "r", encoding="utf-8") as handle:
            source = handle.read()
        expected = sorted({char for char in source if ord(char) > 127})
        assert expected, "%s has no non-ASCII character to check" % name

        built = text_of(site, name[: -len(".jemdoc")] + ".html")
        for char in expected:
            assert char in built, (
                "%s: %r did not survive the build" % (name, char)
            )


def test_static_assets_are_copied(site):
    for relative in (
        "css/site.css",
        "images/portrait.svg",
        "files/cv.pdf",
        ".nojekyll",
    ):
        assert (site / relative).is_file(), "missing asset: %s" % relative


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
        "Biography", "News", "Faculty", "For Students", "Publications",
        "Courses",
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


def test_every_news_item_has_a_date_and_they_run_newest_first(site):
    soup = soup_of(site, "news.html")
    items = soup.select("ul.news > li")
    assert len(items) > 20, (
        "expected the generated news list, found only %d announcements" % len(items)
    )

    years = []
    for item in items:
        date = item.select_one(".news-date")
        assert date is not None, (
            "an announcement has no date: %s" % item.get_text(strip=True)[:60]
        )
        label = date.get_text(strip=True)
        assert NEWS_DATE_RE.match(label), "bad announcement date %r" % label
        assert item.select_one(".news-text") is not None, (
            "announcement %r has no text" % label
        )
        years.append(int(label[:4]))

    assert years == sorted(years, reverse=True), (
        "announcements are not newest-first: %s" % years
    )
    assert any(len(d.get_text(strip=True)) > 4 for d in soup.select(".news-date")), (
        "no announcement shows a month, although the publications have months"
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


def test_home_page_latest_news_matches_the_news_page(site):
    home = soup_of(site, "index.html")
    news = soup_of(site, "news.html")

    headlines = [flat(i.get_text(" ")) for i in home.select("ul.news > li")]
    listed = [flat(i.get_text(" ")) for i in news.select("ul.news > li")]

    assert headlines, "the home page has no latest-news block"
    assert len(headlines) <= 4, (
        "the home page shows %d headlines; keep it to a handful" % len(headlines)
    )
    assert headlines == listed[:len(headlines)], (
        "the home-page headlines are not the newest announcements"
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


def test_the_date_shows_the_month_and_day_when_they_are_known():
    module = load_update_module()
    assert module.format_date({"year": 2026, "month": 0, "day": 0}) == "2026"
    assert module.format_date({"year": 2026, "month": 6, "day": 0}) == "2026-06"
    assert module.format_date({"year": 2026, "month": 6, "day": 1}) == "2026-06"
    assert module.format_date({"year": 2026, "month": 6, "day": 1}, with_day=True) == (
        "2026-06-01"
    )
    assert module.format_date({"year": 0}) == ""


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


def test_the_generated_pages_have_one_clean_note(site):
    """The note heading a generated page is the only sentence on it that is not
    inside the generated markup, and it must survive jemdoc untouched: jemdoc
    reads /text/ as italics, so a path such as tools/update_site.py written into
    that sentence silently swallowed its own slashes."""
    for name in ("news.html", "publications.html"):
        soup = soup_of(site, name)
        notes = [p for p in soup.select("#layout-content > p") if not p.get("class")]
        assert len(notes) == 1, (
            "%s should have exactly one generated note, found %d" % (name, len(notes))
        )

        note = notes[0]
        stray = note.find(["i", "em", "b", "strong", "tt", "code"])
        assert stray is None, (
            "%s: the note came out as <%s>, so jemdoc ate a character: %r"
            % (name, stray.name, note.get_text()[:100])
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
    assert "<li>" in result.stdout, "the news page has no announcements"


def test_news_extra_ships_with_every_line_commented_out():
    """Only the documented examples are committed, so no announcement reaches the
    site that the site owner did not write."""
    with open(os.path.join(SRC, "news-extra.txt"), "r", encoding="utf-8") as handle:
        active = [
            line for line in handle.read().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    assert not active, "www/news-extra.txt ships with live lines: %s" % active


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
    for name in ("publications.jemdoc", "news.jemdoc"):
        with open(os.path.join(SRC, name), "r", encoding="utf-8") as handle:
            head = handle.read(500)
        assert "GENERATED by tools/update_site.py" in head, (
            "%s does not warn that it is generated" % name
        )


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
