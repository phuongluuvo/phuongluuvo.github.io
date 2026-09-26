#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_site.py -- regenerate the two generated pages from their sources.

WHAT IT DOES
    1. Reads the list of works from the public ORCID API of *one* ORCID iD.
    2. Optionally enriches every work that has a DOI with the authoritative
       metadata from Crossref (full author list, journal, volume, issue, pages,
       month). This is what makes the page complete rather than "title + year".
    3. Drops arXiv/preprint duplicates of a work that is already published.
    4. Merges anything pasted into ``www/publications-extra.bib`` -- the place to
       put a paper that ORCID does not have. Duplicates are skipped.
    5. Writes ``www/publications.jemdoc``: one collapsible section per year,
       newest first, each entry ending in a DOI link.
    6. Writes ``www/news.jemdoc``: every publication becomes an announcement, and
       anything typed into ``www/news-extra.txt`` is added on top. The two most
       recent years are shown in full, older years are collapsed.
    7. Refreshes the "Latest news" block of the Home page, but only when the
       GENERATED markers are present in ``www/index.jemdoc``.

Nothing is written when the result would be worse than what is already there:
see MIN_KEEP_RATIO.

The generated files are committed, so the site still builds with no network.
Run this script when you want to refresh them.

USAGE
    python tools/update_site.py                  # ORCID + Crossref (normal)
    python tools/update_site.py --no-crossref    # ORCID only, fast
    python tools/update_site.py --offline        # only the local extra files
    python tools/update_site.py --dry-run        # print, write nothing
    python tools/update_site.py --force          # write even a much shorter list

WHY ORCID AND NOT GOOGLE SCHOLAR
    Google Scholar has no public API and actively blocks automated access, so
    there is no legitimate way for a build script to read it. ORCID publishes
    the same list under an open API, and you can edit your ORCID record when a
    paper is missing.

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #

#: The ORCID iD whose works are published. Change this one line for someone else.
ORCID_ID = "0000-0003-3909-4385"

#: Contact address sent to Crossref/ORCID. The Crossref API gives faster and
#: more reliable service to callers that identify themselves ("polite pool").
CONTACT = "vtlphuong@hcmiu.edu.vn"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTPUT = os.path.join(ROOT, "www", "publications.jemdoc")

ORCID_API = "https://pub.orcid.org/v3.0/%s/works" % ORCID_ID
CROSSREF_API = "https://api.crossref.org/works/%s"

USER_AGENT = "phuongluuvo.github.io site updater (mailto:%s)" % CONTACT

#: Refuse to write a publication list with fewer than this fraction of the
#: entries that are already published. A partial ORCID or Crossref response
#: should never silently shrink the live page; --force overrides this.
MIN_KEEP_RATIO = 0.6

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

#: ORCID work types mapped to the label shown on the page.
TYPE_LABELS = {
    "journal-article": "Journal",
    "conference-paper": "Conference",
    "book-chapter": "Book chapter",
    "book": "Book",
    "other": "Preprint",
    "preprint": "Preprint",
    "report": "Report",
    "dissertation": "Thesis",
}

#: Types that are never treated as "published" when looking for duplicates.
PREPRINT_TYPES = {"other", "preprint"}

#: The name highlighted in the author list on the page.
OWN_SURNAMES = {"vo"}
OWN_GIVEN_PREFIXES = ("phuong", "luu")


# --------------------------------------------------------------------------- #
# fetching
# --------------------------------------------------------------------------- #

def get_json(url: str, timeout: int = 30):
    """GET *url* and parse the JSON body, or return None on any failure."""
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as error:
        print("  ! %s: %s" % (url, error), file=sys.stderr)
        return None


# --------------------------------------------------------------------------- #
# ORCID
# --------------------------------------------------------------------------- #

def _value(node):
    """ORCID wraps scalars as {"value": x}; unwrap them, tolerating None."""
    if isinstance(node, dict):
        return node.get("value")
    return node


def fetch_orcid_works() -> list[dict]:
    """Return one normalised record per work in the ORCID record."""
    payload = get_json(ORCID_API)
    if not payload:
        return []

    records = []
    for group in payload.get("group", []):
        summaries = group.get("work-summary") or []
        if not summaries:
            continue
        summary = summaries[0]          # ORCID returns one summary per group

        title = _value((summary.get("title") or {}).get("title")) or ""
        title = " ".join(str(title).split())      # collapse the nbsp runs

        date = summary.get("publication-date") or {}
        doi = ""
        for external in ((summary.get("external-ids") or {}).get("external-id") or []):
            if external.get("external-id-type") == "doi":
                doi = (external.get("external-id-value") or "").strip()
                break

        # ORCID also carries a URL for most works, but in this record it is
        # always the same Scopus record page -- 37 identical "link" labels that
        # add nothing to a DOI. Extra links are therefore opt-in: they come from
        # www/publications-extra.bib, where you choose them (see BIB_LINKS).
        records.append({
            "title": title,
            "type": summary.get("type") or "other",
            "year": _int(_value(date.get("year"))),
            "month": _int(_value(date.get("month"))),
            "day": _int(_value(date.get("day"))),
            "venue": " ".join(str(_value(
                (summary.get("journal-title") or {})
            ) or "").split()),
            "doi": doi,
            "links": [],
            "put_code": summary.get("put-code"),
            "source": "orcid",
            "enriched": False,
        })
    return records


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Crossref
# --------------------------------------------------------------------------- #

def enrich_from_crossref(record: dict) -> None:
    """Fill in authors, venue, volume, issue, pages and month from Crossref."""
    if not record["doi"]:
        return
    payload = get_json(CROSSREF_API % urllib.parse.quote(record["doi"]))
    if not payload:
        return
    message = payload.get("message") or {}

    authors = []
    for author in message.get("author") or []:
        name = format_author(author.get("given") or "", author.get("family") or "")
        if not name:
            continue
        authors.append({
            "name": name,
            "own": is_own_author(author.get("given") or "", author.get("family") or "",
                                 author.get("ORCID") or ""),
        })
    if authors:
        record["authors"] = authors

    container = message.get("container-title") or []
    if container and container[0]:
        record["venue"] = " ".join(str(container[0]).split())

    record["volume"] = (message.get("volume") or "").strip()
    record["issue"] = (message.get("issue") or "").strip()
    record["page"] = (message.get("page") or "").strip()

    # ORCID's year is authoritative for this record. Only fill in the month and
    # day, and only from a Crossref date that agrees on the year, so that a
    # "first published online" date can never move a paper to another year.
    candidates = []
    for key in ("published-print", "published-online", "issued", "published"):
        parts = ((message.get(key) or {}).get("date-parts") or [[]])[0]
        if parts and parts[0]:
            candidates.append(parts)
    if candidates:
        if record["year"] is None:
            record["year"] = candidates[0][0]
        for parts in candidates:
            if parts[0] != record["year"]:
                continue
            if record["month"] is None and len(parts) > 1:
                record["month"] = parts[1]
            if record["day"] is None and len(parts) > 2:
                record["day"] = parts[2]
            if record["month"] is not None:
                break

    record["enriched"] = True


def format_author(given: str, family: str) -> str:
    """Render an author as deposited: given names first, then the family name.

    Crossref records vary in quality -- some give initials, some the full name,
    and a few split multi-part family names oddly -- so the safest readable
    option is to reproduce the name rather than to re-derive initials.
    """
    given, family = " ".join(given.split()), " ".join(family.split())
    if not family:
        return given
    return ("%s %s" % (given, family)).strip()


def is_own_author(given: str, family: str, orcid: str) -> bool:
    """Is this the site owner? Prefer the ORCID iD, fall back to the name."""
    if orcid and ORCID_ID in orcid:
        return True
    if family.strip().lower() in OWN_SURNAMES:
        return given.strip().lower().startswith(OWN_GIVEN_PREFIXES)
    return False


# --------------------------------------------------------------------------- #
# sorting, de-duplication and formatting
# --------------------------------------------------------------------------- #

def sort_key(record: dict):
    return (-(record.get("year") or 0),
            -(record.get("month") or 0),
            -(record.get("day") or 0),
            record.get("title", "").lower())


def normalise_title(title: str) -> str:
    """Collapse a title so that near-identical versions compare equal."""
    text = re.sub(r"[^a-z0-9]+", " ", title.lower())
    return " ".join(text.split())


def drop_preprint_duplicates(records: list[dict]) -> tuple[list[dict], int]:
    """Remove a preprint whose title already appears as a published work.

    ORCID usually holds both the arXiv version and the published version of the
    same paper. Listing both looks like two papers, so the preprint goes.
    """
    published = {
        normalise_title(r["title"])
        for r in records
        if r["type"] not in PREPRINT_TYPES
    }
    kept, dropped = [], 0
    for record in records:
        if record["type"] in PREPRINT_TYPES:
            if normalise_title(record["title"]) in published:
                dropped += 1
                continue
        kept.append(record)
    return kept, dropped


def format_date(record: dict) -> str:
    """'2026-02' when the month is known, otherwise '2026'.

    This is the precise form shown on the page itself, in the metadata line of a
    publication. The news feed uses the compact ``short_date`` stamp instead.
    """
    year = record.get("year")
    if not year:
        return ""
    month = record.get("month")
    if not month or not 1 <= int(month) <= 12:
        return str(year)
    return "%d-%02d" % (year, int(month))


def render_entry(record: dict) -> str:
    """One <li> of publication markup."""
    esc = html.escape

    authors = record.get("authors")
    if authors:
        rendered = ", ".join(
            "<b>%s</b>" % esc(a["name"]) if a["own"] else esc(a["name"])
            for a in authors
        )
    else:
        rendered = ""

    bits = []
    if record.get("venue"):
        bits.append("<i>%s</i>" % esc(record["venue"]))
    if record.get("volume"):
        bits.append("vol. %s" % esc(record["volume"]))
    if record.get("issue"):
        bits.append("no. %s" % esc(record["issue"]))
    if record.get("page"):
        # 970-973 -> 970-973 with an en dash, but only between digits.
        page = re.sub(r"(?<=\d)-(?=\d)", "\u2013", record["page"])
        bits.append("pp. %s" % esc(page))
    date = format_date(record)
    if date:
        bits.append(date)
    if record["doi"]:
        bits.append('<a href="https://doi.org/%s" target="blank">doi</a>'
                    % esc(record["doi"]))
    for link in record.get("links") or []:
        bits.append('<a href="%s" target="blank">%s</a>'
                    % (esc(link["href"]), esc(link["label"])))
    if record.get("note"):
        bits.append('<span class="pub-note">%s</span>' % esc(record["note"]))

    type_label = TYPE_LABELS.get(record["type"], "Publication")
    source = record.get("source", "orcid")
    lines = ['<li data-source="%s">' % source]
    if rendered:
        lines.append('<p class="pub-authors">%s</p>' % rendered)
    lines.append('<p class="pub-title">%s</p>' % esc(record["title"]))
    if bits:
        lines.append('<p class="pub-meta"><span class="pub-type">%s</span> %s</p>'
                     % (esc(type_label), ", ".join(bits)))
    lines.append("</li>")
    return "\n".join(lines)


def build_page(records: list[dict], dropped: int, added: int = 0) -> str:
    """Render the whole www/publications.jemdoc file."""
    by_year: dict[int, list[dict]] = {}
    for record in sorted(records, key=sort_key):
        by_year.setdefault(record.get("year") or 0, []).append(record)

    blocks = []
    for index, year in enumerate(sorted(by_year, reverse=True)):
        entries = by_year[year]
        count = len(entries)
        label = "%d" % count
        open_attr = " open" if index < OPEN_YEARS else ""
        blocks.append('<details class="year"%s>' % open_attr)
        blocks.append('<summary>%d<span class="pub-count">%s %s</span></summary>'
                      % (year, label, "entry" if count == 1 else "entries"))
        blocks.append('<ul class="pubs">')
        blocks.extend(render_entry(entry) for entry in entries)
        blocks.append('</ul>')
        blocks.append('</details>')

    total = len(records)
    years = len(by_year)
    note = ("%d entries across %d years" % (total, years)) if total else "no entries"
    if added:
        note += ", %d added by hand from publications-extra.bib" % added
    if dropped:
        note += ", %d preprint duplicate%s hidden" % (dropped, "" if dropped == 1 else "s")

    return HEADER % {"orcid": ORCID_ID, "note": note} + "\n".join(blocks) + FOOTER


HEADER = """# jemdoc: menu{menu.jemdoc}{publications.html}, notime
# GENERATED by tools/update_site.py -- do not edit this file by hand.
# To add a paper ORCID does not have, paste its BibTeX into www/publications-extra.bib.
= Publications
Journal articles, conference papers and book chapters, newest first

Generated automatically from my [https://orcid.org/%(orcid)s ORCID record] plus a local BibTeX
file -- %(note)s. The two most recent years are shown in full and older years open when you
click them. Entries link to their DOI, and hand-added ones can also carry a PDF or a talk.

~~~
{}{raw}
"""

FOOTER = """
~~~
"""


# --------------------------------------------------------------------------- #
# the manual BibTeX overlay
# --------------------------------------------------------------------------- #
# Not everything ends up in ORCID (a book chapter, a workshop paper, a patent, a
# paper the publisher never deposited). Anything pasted into BIB_INPUT is merged
# into the same page and sorted into the right year with the ORCID entries.

BIB_INPUT = os.path.join(ROOT, "www", "publications-extra.bib")

#: BibTeX entry types mapped onto the ORCID type names, so that a single table of
#: labels serves both sources.
BIB_TYPES = {
    "article": "journal-article",
    "inproceedings": "conference-paper",
    "conference": "conference-paper",
    "incollection": "book-chapter",
    "inbook": "book-chapter",
    "book": "book",
    "phdthesis": "dissertation",
    "mastersthesis": "dissertation",
    "techreport": "report",
    "unpublished": "preprint",
    "misc": "other",
}

BIB_MONTHS = {name: number for number, name in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

#: LaTeX that is tidied up before the value is shown as HTML.
BIB_REPLACEMENTS = (
    (r"\\&", "&"),
    (r"\\%", "%"),
    (r"\\_", "_"),
    (r"\\#", "#"),
    (r"\\textendash", "\u2013"),
    (r"\\textemdash", "\u2014"),
    ("---", "\u2014"),
    ("--", "\u2013"),
    ("~", " "),
)

#: Optional extra links a hand-added BibTeX entry may carry, in the order they are
#: shown on the Publications page. Put the field in an entry in
#: www/publications-extra.bib and it appears next to the DOI link:
#:
#:     arxiv  = {2401.01234}          -> https://arxiv.org/abs/2401.01234
#:     pdf    = {https://.../p.pdf}   -> used exactly as written
#:     slides = {https://.../s.pdf}
#:     code   = {https://github.com/...}
#:     video  = {https://...}
#:     url    = {https://...}         -> shown as "link"
#:
#: Values are NOT run through the LaTeX tidy-up, because a URL may contain
#: characters that tidy-up would rewrite.
BIB_LINKS = (
    ("arxiv", "arXiv"),
    ("pdf", "pdf"),
    ("slides", "slides"),
    ("code", "code"),
    ("video", "video"),
    ("url", "link"),
)


def bib_links(fields: dict) -> list[dict]:
    """The optional extra links on one BibTeX entry, ready for render_entry."""
    links = []
    for field, label in BIB_LINKS:
        value = (fields.get(field) or "").strip().replace("{", "").replace("}", "")
        value = value.strip('"').strip()
        if not value:
            continue
        if field == "arxiv" and not value.lower().startswith("http"):
            value = "https://arxiv.org/abs/" + value
        if not value.lower().startswith("http"):
            continue        # a bare DOI here would be a mistake, so ignore it
        links.append({"label": label, "href": value})
    return links


def strip_bib_comments(text: str) -> str:
    """Drop every line whose first non-blank character is ``%``.

    That is what lets the header of publications-extra.bib explain itself, and
    lets you keep an entry commented out until you are ready to publish it.
    """
    return "\n".join(
        line for line in text.splitlines()
        if not line.lstrip().startswith("%")
    )


def parse_bibtex(text: str) -> list[dict]:
    """Parse a .bib file into ``[{type, key, fields}]``.

    This is deliberately forgiving rather than a complete BibTeX implementation:
    it understands the ``@type{key, field = {value}, ...}`` form that every
    publisher, Zotero and Google Scholar emit.
    """
    text = strip_bib_comments(text)
    entries: list[dict] = []
    position = 0

    while True:
        at = text.find("@", position)
        if at < 0:
            break
        head = re.match(r"@([A-Za-z]+)\s*([{(])", text[at:])
        if not head:
            position = at + 1
            continue

        start = at + head.end()
        comma = text.find(",", start)
        if comma < 0:
            break
        key = text[start:comma].strip()

        # Walk the body, tracking {} nesting and "..." quoting, until the entry
        # closes. Everything in between is the field list.
        depth, quotes, index = 1, False, comma + 1
        while index < len(text) and depth > 0:
            char = text[index]
            if quotes:
                if char == '"':
                    quotes = False
            elif char == '"' and depth == 1:
                quotes = True
            elif char in "{(":
                depth += 1
            elif char in "})":
                depth -= 1
            index += 1

        entries.append({
            "type": head.group(1).lower(),
            "key": key,
            "fields": split_bib_fields(text[comma + 1:index - 1]),
        })
        position = index

    return entries


def split_bib_fields(body: str) -> dict:
    """Split ``a = {x}, b = {y}`` into ``{"a": "x", "b": "y"}``."""
    parts, current = [], []
    depth, quotes = 0, False

    for char in body:
        if quotes:
            if char == '"':
                quotes = False
        elif char == '"' and depth == 0:
            quotes = True
        elif char in "{(":
            depth += 1
        elif char in "})":
            depth -= 1

        if char == "," and depth == 0 and not quotes:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    parts.append("".join(current))

    fields = {}
    for part in parts:
        if "=" not in part:
            continue
        name, _, value = part.partition("=")
        name, value = name.strip().lower(), value.strip()
        if len(value) >= 2 and value[0] + value[-1] in ("{}", '""'):
            value = value[1:-1]
        if name:
            fields[name] = value
    return fields


def clean_bib_value(value: str) -> str:
    """Turn a raw BibTeX field into display text."""
    for pattern, replacement in BIB_REPLACEMENTS:
        value = re.sub(pattern, replacement, value)
    value = value.replace("{", "").replace("}", "")
    return " ".join(value.split())


def bib_month(value: str):
    """``jun`` / ``June`` / ``6`` -> 6."""
    text = clean_bib_value(value).strip().lower()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    for name, number in BIB_MONTHS.items():
        if text.startswith(name):
            return number
    return None


def bib_author_list(value: str) -> list[dict]:
    """``Vo, Phuong L. and Tran, Nguyen H.`` -> the shared author structure."""
    people = []
    for raw in re.split(r"\s+and\s+", value):
        raw = clean_bib_value(raw).strip()
        if not raw:
            continue
        if "," in raw:
            family, _, given = raw.partition(",")
            family, given = family.strip(), given.strip()
        else:
            bits = raw.split()
            family, given = (bits[-1], " ".join(bits[:-1])) if bits else (raw, "")
        given_first = ("%s %s" % (given, family)).strip()
        people.append({
            "name": given_first,
            "own": (family.lower() in OWN_SURNAMES
                    and given.lower().startswith(OWN_GIVEN_PREFIXES)),
        })
    return people


def bib_entry_to_record(entry: dict):
    """Convert one parsed entry into the same record shape ORCID produces."""
    fields = entry["fields"]
    title = clean_bib_value(fields.get("title", ""))
    if not title or not entry["key"]:
        return None

    venue = clean_bib_value(
        fields.get("journal") or fields.get("booktitle")
        or fields.get("publisher") or ""
    )
    doi = fields.get("doi", "").strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    year = clean_bib_value(fields.get("year", ""))[:4]

    return {
        "title": title,
        "type": BIB_TYPES.get(entry["type"], "other"),
        "year": _int(year),
        "month": bib_month(fields.get("month", "")),
        "day": None,
        "venue": venue,
        "doi": doi,
        "authors": bib_author_list(fields.get("author", "")),
        "volume": clean_bib_value(fields.get("volume", "")),
        "issue": clean_bib_value(fields.get("number", "")),
        "page": clean_bib_value(fields.get("pages", "")),
        "note": clean_bib_value(fields.get("note", "")),
        "links": bib_links(fields),
        "key": entry["key"],
        "source": "bib",
        "enriched": True,
    }


def read_extra_bibtex() -> list[dict]:
    """Read www/publications-extra.bib, or return nothing if there is no file."""
    if not os.path.isfile(BIB_INPUT):
        return []

    with open(BIB_INPUT, "r", encoding="utf-8") as handle:
        text = handle.read()

    records = []
    for entry in parse_bibtex(text):
        record = bib_entry_to_record(entry)
        if record is None:
            print("  ! ignored an entry with no title or no citation key",
                  file=sys.stderr)
            continue
        records.append(record)
    return records


def merge_records(records: list[dict], extras: list[dict]) -> tuple[list[dict], int]:
    """Add the manual entries, skipping any that ORCID already lists.

    Matching is on DOI first and on the normalised title second, so you can paste
    something today and let ORCID pick it up later without getting it twice.
    """
    seen_dois = {(r.get("doi") or "").lower() for r in records if r.get("doi")}
    seen_titles = {normalise_title(r["title"]) for r in records}

    added = 0
    for record in extras:
        doi = (record.get("doi") or "").lower()
        title = normalise_title(record["title"])
        if (doi and doi in seen_dois) or title in seen_titles:
            continue
        seen_dois.add(doi)
        seen_titles.add(title)
        records.append(record)
        added += 1
    return records, added


# --------------------------------------------------------------------------- #
# the news feed
# --------------------------------------------------------------------------- #
# News comes from two places:
#   * every publication on the Publications page becomes a news item, so a paper
#     that arrives through ORCID, or that you paste into publications-extra.bib,
#     shows up in the news by itself;
#   * anything you type into www/news-extra.txt -- grants, talks, new students.
#
# The two most recent years are shown in full; older years are collapsed.

NEWS_INPUT = os.path.join(ROOT, "www", "news-extra.txt")
NEWS_OUTPUT = os.path.join(ROOT, "www", "news.jemdoc")
HOME_PAGE = os.path.join(ROOT, "www", "index.jemdoc")

#: Markers around the "Latest news" block on the Home page. The block is only
#: rewritten when both markers are present, so deleting them stops the sync.
HOME_NEWS_BEGIN = "# BEGIN GENERATED latest-news"
HOME_NEWS_END = "# END GENERATED latest-news"

#: How many of the newest years keep their entries open; every older year is
#: collapsed into a click-to-open dropdown. The same rule is used for the
#: Publications page and for the News page, so the two behave alike.
OPEN_YEARS = 2

#: How many items the Home page shows.
HOME_NEWS_LIMIT = 4

#: The verb that joins a title to its venue. Every publication announcement has
#: the same shape, with the month and year in brackets at the end:
#:
#:     "Title of the paper" accepted by IEEE INFOCOM 2023 (12/22).
NEWS_VERB = {
    "journal-article": "published in",
    "conference-paper": "accepted by",
    "book-chapter": "published in",
    "book": "published by",
    "dissertation": "published by",
    "other": "posted to",
}

#: `[label](https://...)` inside a news-extra.txt line becomes a link.
NEWS_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")

#: One news-extra.txt line: `2026-10-01 | Some announcement`.
NEWS_LINE_RE = re.compile(r"^\s*(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?\s*\|(.*)$")


def text_to_parts(text: str) -> list[dict]:
    """Split plain text into display parts, turning `[label](url)` into a link."""
    parts, position = [], 0
    for match in NEWS_LINK_RE.finditer(text):
        if match.start() > position:
            parts.append({"text": text[position:match.start()]})
        parts.append({"link": match.group(2), "label": match.group(1)})
        position = match.end()
    if position < len(text):
        parts.append({"text": text[position:]})
    return parts or [{"text": text}]


def render_parts(parts: list[dict]) -> str:
    """Render parts as HTML, escaping everything that came from the outside."""
    out = []
    for part in parts:
        if "text" in part:
            out.append(html.escape(part["text"]))
        elif "italic" in part:
            out.append("<i>%s</i>" % html.escape(part["italic"]))
        else:
            out.append('<a href="%s" target="blank">%s</a>'
                       % (html.escape(part["link"]), html.escape(part["label"])))
    return "".join(out)


def parts_to_text(parts: list[dict]) -> str:
    """Flatten parts to plain text, for sorting ties and for the console."""
    return "".join(
        part.get("text") or part.get("italic") or part.get("label") or ""
        for part in parts
    )


def short_date(year: int, month: int) -> str:
    """December 2022 -> ``12/22``, the compact stamp used in an announcement."""
    if not year or not month:
        return ""
    return "%02d/%02d" % (month, year % 100)


def publication_news_item(record: dict) -> dict:
    """Turn one publication into a news item.

    The shape, and the reason there is no separate date column, is::

        "Title of the paper" accepted by IEEE INFOCOM 2023 (12/22).

    The title comes first in quotes, then the verb, the venue and the year, then
    the month and year in brackets. A DOI link is appended where there is one.
    """
    year = record.get("year") or 0
    venue = (record.get("venue") or "").strip()

    parts = [
        {"text": "\u201c%s\u201d " % record["title"]},
        {"text": NEWS_VERB.get(record["type"], "accepted by") + " "},
    ]

    if venue:
        parts.append({"text": venue})
        # A conference venue usually carries the year already
        # ("2024 International Conference on ..."); never write it twice.
        if year and str(year) not in venue:
            parts.append({"text": " %d" % year})
    elif year:
        parts.append({"text": "%d" % year})

    stamp = short_date(year, record.get("month") or 0)
    parts.append({"text": " (%s)." % stamp if stamp else "."})

    if record.get("doi"):
        parts.append({"text": " "})
        parts.append({"link": "https://doi.org/%s" % record["doi"], "label": "doi"})

    return {
        "date_label": format_date(record),
        "sort": (year, record.get("month") or 0, record.get("day") or 0),
        "year": year,
        "parts": parts,
        "source": record.get("source", "orcid"),
    }


def read_extra_news() -> list[dict]:
    """Read www/news-extra.txt: one ``YYYY-MM-DD | text`` item per line."""
    if not os.path.isfile(NEWS_INPUT):
        return []

    items = []
    with open(NEWS_INPUT, "r", encoding="utf-8") as handle:
        for number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            match = NEWS_LINE_RE.match(line)
            if not match:
                print("  ! news-extra.txt line %d has no 'YYYY-MM-DD |' date; skipped"
                      % number, file=sys.stderr)
                continue

            year = int(match.group(1))
            month = int(match.group(2) or 0)
            day = int(match.group(3) or 0)
            text = match.group(4).strip()
            if not text:
                continue

            label = "%04d" % year
            if month:
                label += "-%02d" % month
                if day:
                    label += "-%02d" % day

            stamp = short_date(year, month)
            parts = text_to_parts(text)
            if stamp:
                # Your own items are dated the same way as the rest of the feed.
                parts.insert(0, {"text": "(%s) " % stamp})

            items.append({
                "date_label": label,
                "sort": (year, month, day),
                "year": year,
                "parts": parts,
                "source": "manual",
            })
    return items


def build_news_items(records: list[dict], manual: list[dict]) -> list[dict]:
    """Publication items plus manual items, newest first."""
    items = [publication_news_item(r) for r in records if r.get("year")]
    items.extend(manual)
    items.sort(key=lambda item: (
        tuple(-value for value in item["sort"]),
        parts_to_text(item["parts"]).lower(),
    ))
    return items


def render_news_item(item: dict) -> str:
    """One announcement.

    There is no separate date column: the date is part of the sentence, which is
    the shape the site owner asked for and how Duy H. N. Nguyen's news reads. The
    full date is still there on hover, in the ``title`` attribute.
    """
    return '<li title="%s">%s</li>' % (html.escape(item["date_label"]),
                                       render_parts(item["parts"]))


NEWS_HEADER = """# jemdoc: menu{menu.jemdoc}{news.html}, notime
# GENERATED by tools/update_site.py -- do not edit this file by hand.
# Announcements come from the publication list; add your own in www/news-extra.txt.
= News
Announcements, newest first

%(note)s

~~~
{}{raw}
"""

NEWS_FOOTER = """
~~~
"""


def build_news_page(items: list[dict]) -> str:
    """Render the whole www/news.jemdoc file."""
    by_year: dict[int, list[dict]] = {}
    for item in items:
        by_year.setdefault(item["year"], []).append(item)
    years = sorted(by_year, reverse=True)

    blocks = []
    for index, year in enumerate(years):
        entries = by_year[year]
        count = len(entries)

        listing = ['<ul class="news">']
        listing.extend(render_news_item(entry) for entry in entries)
        listing.append('</ul>')

        if index < OPEN_YEARS:
            blocks.append('<h2 class="news-year">%d</h2>' % year)
            blocks.extend(listing)
        else:
            blocks.append('<details class="year">')
            blocks.append('<summary>%d<span class="pub-count">%d %s</span></summary>'
                          % (year, count, "entry" if count == 1 else "entries"))
            blocks.extend(listing)
            blocks.append('</details>')

    if items:
        note = ("%d announcements across %d years. The %d most recent years are shown "
                "in full; older years open when you click them."
                % (len(items), len(years), min(OPEN_YEARS, len(years))))
    else:
        note = "No announcements yet."
    # Careful: jemdoc treats /.../ as italics, so this line must contain no
    # slash at all. Paths are named in the comments above instead.
    note = ("Generated by the update_site.py script from my publications (ORCID plus a "
            "local BibTeX file) and from my local news file. " + note)

    return NEWS_HEADER % {"note": note} + "\n".join(blocks) + NEWS_FOOTER


def sync_home_news(items: list[dict]):
    """Rewrite the marked "Latest news" block on the Home page.

    Returns ``(items, changed)``, or None when the markers are absent -- in which
    case the Home page is left completely alone.
    """
    if not os.path.isfile(HOME_PAGE):
        return None
    with open(HOME_PAGE, "r", encoding="utf-8") as handle:
        text = handle.read()

    start = text.find(HOME_NEWS_BEGIN)
    end = text.find(HOME_NEWS_END)
    if start < 0 or end < 0 or end < start:
        return None

    count = len(items[:HOME_NEWS_LIMIT])
    body = ["~~~", "{}{raw}", '<ul class="news">']
    body.extend(render_news_item(item) for item in items[:HOME_NEWS_LIMIT])
    body.append("</ul>")
    body.append("~~~")

    updated = (text[:start + len(HOME_NEWS_BEGIN)] + "\n"
               + "\n".join(body) + "\n" + text[end:])
    if updated == text:
        return count, False
    with open(HOME_PAGE, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)
    return count, True


# --------------------------------------------------------------------------- #
# output helpers
# --------------------------------------------------------------------------- #

def write_text(path: str, text: str) -> bool:
    """Write *text* only when it differs, so unchanged runs leave no diff."""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as handle:
            if handle.read() == text:
                return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return True


def count_entries(path: str, marker: str) -> int:
    """How many entries a page generated by an earlier run contains."""
    if not os.path.isfile(path):
        return 0
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read().count(marker)


def would_shrink_the_list(new_count: int, previous: int) -> bool:
    """True when writing *new_count* entries would throw away a large part of the
    *previous* count -- the signature of a partial ORCID or Crossref response.

    Losing half a publication list to a timeout is worse than publishing a list
    that is one day stale, so the caller refuses to write in that case.
    """
    if not previous:
        return False        # nothing published yet to compare against
    return new_count < previous * MIN_KEEP_RATIO


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--no-crossref", action="store_true",
                        help="do not ask Crossref for full metadata (faster, less detail)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the result instead of writing it")
    parser.add_argument("--force", action="store_true",
                        help="write the pages even if the new list is much shorter "
                             "than the one already published")
    parser.add_argument("--offline", action="store_true",
                        help="skip ORCID and Crossref; rebuild the page from "
                             "www/publications-extra.bib alone")
    parser.add_argument("--delay", type=float, default=0.2,
                        help="seconds to wait between Crossref requests (default 0.2)")
    args = parser.parse_args()

    dropped = 0
    if args.offline:
        records = []
        print("Offline: ORCID and Crossref are skipped.")
    else:
        print("Reading ORCID %s ..." % ORCID_ID)
        records = fetch_orcid_works()
        if not records:
            print("error: could not read any works from ORCID. Nothing was written.\n"
                  "       Re-run with --offline to build the page from "
                  "publications-extra.bib on its own.", file=sys.stderr)
            return 1
        print("  %d work(s) in the ORCID record" % len(records))

        records, dropped = drop_preprint_duplicates(records)
        if dropped:
            print("  dropped %d preprint duplicate(s) of a published paper" % dropped)

        if args.no_crossref:
            print("Skipping Crossref (--no-crossref); entries carry title, venue, date and DOI.")
        else:
            todo = [r for r in records if r["doi"]]
            print("Enriching %d entries from Crossref ..." % len(todo))
            for number, record in enumerate(todo, start=1):
                enrich_from_crossref(record)
                if number % 10 == 0 or number == len(todo):
                    print("  %d/%d" % (number, len(todo)))
                time.sleep(args.delay)

    extras = read_extra_bibtex()
    if extras:
        print("  %d entr%s read from %s" % (
            len(extras), "y" if len(extras) == 1 else "ies",
            os.path.relpath(BIB_INPUT, ROOT)))
    records, added = merge_records(records, extras)
    if added < len(extras):
        print("  %d of them are already in ORCID and were skipped" % (len(extras) - added))

    if not records:
        print("error: there is nothing to publish. The page was not written.",
              file=sys.stderr)
        return 1

    # A partial ORCID or Crossref response must not silently shrink the live
    # publication list. Refuse and keep whatever is already published.
    previous = count_entries(OUTPUT, '<li data-source=')
    if not args.force and not args.offline and would_shrink_the_list(len(records), previous):
        print("error: only %d entries this time, against %d already published.\n"
              "       ORCID or Crossref may be having a bad day, so nothing was "
              "written and the current page is untouched.\n"
              "       Re-run with --force if the shorter list really is correct."
              % (len(records), previous), file=sys.stderr)
        return 1

    page = build_page(records, dropped, added)
    news_items = build_news_items(records, read_extra_news())
    news_page = build_news_page(news_items)

    if args.dry_run:
        sys.stdout.write(page)
        sys.stdout.write("\n" + "-" * 72 + "\n\n")
        sys.stdout.write(news_page)
        return 0

    changed = write_text(OUTPUT, page)
    print("%s %s (%d entries)" % ("Wrote" if changed else "Unchanged",
                                  os.path.relpath(OUTPUT, ROOT), len(records)))

    changed = write_text(NEWS_OUTPUT, news_page)
    print("%s %s (%d announcements)" % ("Wrote" if changed else "Unchanged",
                                        os.path.relpath(NEWS_OUTPUT, ROOT),
                                        len(news_items)))

    home = sync_home_news(news_items)
    if home is None:
        print("Home page: no latest-news markers, so the Home page was left alone.")
    else:
        count, changed = home
        print("%s Home page latest-news block (%d items)."
              % ("Wrote" if changed else "Unchanged", count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
