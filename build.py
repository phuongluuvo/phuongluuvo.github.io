#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py -- build the website of Assoc. Prof. Phuong Luu Vo.

WHAT IT DOES
    1. Collects every ``www/*.jemdoc`` file that is a page: `mysite.conf` and
       every ``menu*.jemdoc`` are skipped, because a menu is included by the
       pages that use it rather than built into one of its own.
    2. Copies them plus ``www/mysite.conf`` into a temporary staging folder,
       normalising line endings to LF. (jemdoc is sensitive to Windows CRLF
       line endings, so this step makes the build work the same everywhere.)
    3. Runs ``tools/jemdoc`` on every page, which produces ``*.html``.
    4. Indents that HTML so that a person can read it. jemdoc writes its own
       tags at column zero and passes the tags copied from a page through with
       the page's own indentation, so the two run together. Only the whitespace
       in front of a line is touched, never the text itself.
    5. Copies the generated HTML plus the static folders
       (``css/``, ``files/``, ``images/``) into the output folder, and writes the
       ``.nojekyll`` marker that stops GitHub Pages from running Jekyll. The
       static folders are mirrored, so a file you delete from ``www/`` also
       disappears from the output.

USAGE
    python build.py                  build the site into ``_site/`` (default)
    python build.py --out docs       build into another folder instead
    python build.py --serve          build, then open a local preview server
    python build.py --clean          delete the generated HTML files

Everything you normally edit lives in ``www/``. The output folder is generated
and is not committed: GitHub Actions builds it and deploys it. See guide.md.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "www")
TOOLS = os.path.join(ROOT, "tools")
JEMDOC = os.path.join(TOOLS, "jemdoc")
CONF = "mysite.conf"

#: Where the generated site is written unless --out says otherwise. This folder
#: is NOT committed -- GitHub Actions builds it and deploys it. See guide.md.
OUTPUT_DIR = os.path.join(ROOT, "_site")

#: jemdoc files in www/ that are NOT standalone pages.
NOT_A_PAGE = {"menu.jemdoc", CONF}

#: Folders in www/ that are copied verbatim to the output folder.
ASSET_DIRS = ("css", "files", "images")

#: Appears in the <head> of every page this build writes (see the banner in
#: www/mysite.conf). Used to recognise -- and only then delete -- stale output
#: from an earlier build, so that a hand-written file is never removed.
GENERATED_MARKER = "GENERATED FILE"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def read_text_lf(path: str) -> str:
    """Read a file and return its contents with LF line endings."""
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return handle.read().replace("\r\n", "\n").replace("\r", "\n")


def is_menu_file(name: str) -> bool:
    """True for a ``www/menu*.jemdoc`` file, e.g. menu.jemdoc or menu-lab.jemdoc.

    Every page includes exactly one menu, and the lab pages use a different one,
    so the sidebar changes inside the lab without touching the rest of the site.
    """
    return name.startswith("menu") and name.endswith(".jemdoc")


def find_pages() -> list[str]:
    """Return the names of all .jemdoc pages, alphabetically.

    A menu file is *included* by the pages that use it, so it is not a page
    itself. There is more than one: www/menu.jemdoc for the main site and
    www/menu-lab.jemdoc for the Edge AI Lab pages, whose sidebar is different.
    """
    pages = [
        name
        for name in sorted(os.listdir(SRC))
        if name.endswith(".jemdoc")
        and name not in NOT_A_PAGE
        and not is_menu_file(name)
    ]
    if not pages:
        sys.exit("error: no .jemdoc pages found in %s" % SRC)
    return pages


# --------------------------------------------------------------------------- #
# build steps
# --------------------------------------------------------------------------- #

def run_jemdoc(staging: str, pages: list[str]) -> None:
    """Run jemdoc inside *staging* to turn every page into HTML."""
    command = [
        sys.executable,
        "-W", "ignore",          # silence harmless SyntaxWarnings from jemdoc
        JEMDOC,
        "-c", CONF,
    ] + pages

    # jemdoc writes the HTML with locale.getpreferredencoding(), which is cp1252
    # on Windows. Curly quotes and en dashes would then be encoded as single
    # cp1252 bytes, and the page would stop being valid UTF-8 -- the source
    # pages are read as UTF-8, so the text really is non-ASCII. Forcing UTF-8
    # inside the child makes Windows and Linux produce byte-identical HTML.
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"

    result = subprocess.run(command, cwd=staging, env=env,
                            capture_output=True, text=True)
    if result.returncode != 0:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        sys.exit("error: jemdoc failed (exit code %d)" % result.returncode)
    if result.stderr.strip():
        # jemdoc warnings are usually interesting enough to show.
        for line in result.stderr.strip().splitlines():
            if "SyntaxWarning" not in line:
                print("jemdoc: " + line)


# --------------------------------------------------------------------------- #
# tidying the generated HTML
# --------------------------------------------------------------------------- #

#: One level of indentation in the generated HTML.
INDENT = "  "

#: Elements whose body the browser lays out as written: every space inside them
#: counts, so their contents are passed through untouched.
VERBATIM_ELEMENTS = ("pre", "textarea")

#: Elements whose body is code. Leading whitespace means nothing to the browser
#: inside them, so the block is moved sideways by one amount and keeps the
#: layout it has.
CODE_ELEMENTS = ("script", "style")

#: Elements that never take a closing tag, so they cannot change the level.
VOID_ELEMENTS = frozenset((
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
))

#: Elements that begin a block of the page. Only these move the level: <a> and
#: <span> sit *inside* a line of text, and breaking the line around them would
#: push a space into the middle of a sentence.
BLOCK_ELEMENTS = frozenset((
    "html", "head", "body", "table", "thead", "tbody", "tfoot", "tr", "td", "th",
    "div", "p", "ul", "ol", "li", "dl", "dt", "dd",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "section", "article", "aside", "nav", "header", "footer", "main",
    "figure", "figcaption", "details", "summary", "blockquote",
    "form", "fieldset", "video", "audio", "canvas", "svg",
))

#: A tag: a comment, a doctype, a closing tag, or an opening tag. An attribute
#: value may hold a ">", so quoted values are matched before the ">" that ends
#: the tag.
_TAG = re.compile(
    r"<!--.*?-->"
    r"|<!\[CDATA\[.*?\]\]>"
    r"|<!DOCTYPE[^>]*>"
    r"|</\s*([A-Za-z][A-Za-z0-9:._-]*)\s*>"
    r"|<\s*([A-Za-z][A-Za-z0-9:._-]*)(?:[^>\"']|\"[^\"]*\"|'[^']*')*>",
    re.DOTALL,
)


def _tags_in(line: str) -> list[tuple[str, str]]:
    """The tags on *line*, each as a ``(kind, name)`` pair.

    *kind* is ``"open"``, ``"close"``, ``"void"`` for a tag that takes no
    closing tag, or ``"other"`` for a comment or a doctype.
    """
    found: list[tuple[str, str]] = []
    for match in _TAG.finditer(line):
        tag = match.group(0)
        if tag.startswith("</"):
            found.append(("close", match.group(1).lower()))
        elif tag.startswith("<!"):
            found.append(("other", ""))
        else:
            name = match.group(2).lower()
            void = name in VOID_ELEMENTS or tag[:-1].rstrip().endswith("/")
            found.append(("void" if void else "open", name))
    return found


def _moved(line: str, shift: int) -> str:
    """Move *line* sideways by *shift* columns, leaving its own layout alone."""
    if not line.strip():
        return ""
    return " " * max(len(line) - len(line.lstrip()) + shift, 0) + line.lstrip()


def tidy_html(text: str) -> str:
    """Indent generated HTML so that it can be read, without changing it.

    jemdoc writes its own tags at column zero, and passes the tags copied from a
    .jemdoc page through with whatever indentation that page gave them, so the
    two conventions run into each other and the nesting is impossible to follow.

    Only the whitespace in front of a line is rewritten, and no line is ever
    split or joined, so the page itself cannot change: HTML turns a run of
    spaces into one, and every line break stays where jemdoc put it.
    """
    out: list[str] = []
    level = 0
    opaque = None   # the comment or element whose body is being left alone
    shift = 0       # how far sideways that body is being moved

    for raw in text.split("\n"):
        stripped = raw.strip()

        if opaque is not None:
            out.append(raw if not shift else _moved(raw, shift))
            if opaque == "comment":
                if "-->" in raw:
                    opaque = None
            elif "</%s" % opaque in raw.lower():
                opaque = None
            continue

        if not stripped:
            out.append("")
            continue

        events = _tags_in(stripped)

        # A line that begins by closing a block belongs one level further out.
        here = level
        if events and events[0][0] == "close" and events[0][1] in BLOCK_ELEMENTS:
            here = max(level - 1, 0)
        indent = INDENT * max(here, 0)
        out.append(indent + stripped)

        column = len(raw) - len(raw.lstrip())

        # A comment that runs over several lines is a drawing: move the whole
        # thing by a single amount so that its edges stay lined up.
        start = stripped.find("<!--")
        if start == 0 and "-->" not in stripped:
            opaque, shift = "comment", len(indent) - column
            continue

        for kind, name in events:
            if kind == "open":
                if name in BLOCK_ELEMENTS:
                    level += 1
                if name in VERBATIM_ELEMENTS + CODE_ELEMENTS and opaque is None:
                    opaque = name
                    if name in VERBATIM_ELEMENTS:
                        shift = 0
                    else:
                        at_start = stripped.lower().startswith("<" + name)
                        shift = len(indent) - column if at_start else 0
            elif kind == "close":
                if name in BLOCK_ELEMENTS:
                    level = max(level - 1, 0)
                if name == opaque:
                    opaque = None

    return "\n".join(out)


def write_page(source: str, target: str, tidy: bool) -> None:
    """Copy one generated page to *target*, indenting it on the way."""
    with open(source, "r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(tidy_html(text) if tidy else text)


def stage_sources(staging: str, pages: list[str]) -> None:
    """Copy the .jemdoc sources (and the menu) into *staging* with LF endings."""
    names = sorted(
        name for name in os.listdir(SRC) if name.endswith(".jemdoc")
    ) + [CONF]
    for name in names:
        source = os.path.join(SRC, name)
        if not os.path.isfile(source):
            continue
        text = read_text_lf(source)
        with open(os.path.join(staging, name), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)


def copy_assets(outdir: str) -> tuple[list[str], list[str]]:
    """Mirror css/, files/ and images/ from www/ into the output folder.

    The output is made to *match* the source, not merely added to: a file you
    delete from ``www/images/`` or ``www/files/`` is deleted from the output as
    well. Copying alone is not enough -- ``shutil.copytree`` adds and overwrites
    but never removes, so a picture or a PDF taken out of ``www/`` used to sit in
    the output folder for ever, and every later build left it there.

    Returns ``(copied, removed)``, both in report form such as "images/old.png".
    """
    copied: list[str] = []
    removed: list[str] = []

    for name in ASSET_DIRS:
        source = os.path.join(SRC, name)
        target = os.path.join(outdir, name)

        if not os.path.isdir(source):
            # The whole folder is gone from www/: so is its output copy.
            if os.path.isdir(target):
                removed.extend(_list_files(target, name))
                shutil.rmtree(target)
            continue

        wanted = set(_list_files(source, ""))
        if os.path.isdir(target):
            for relative in _list_files(target, ""):
                if relative not in wanted:
                    os.remove(os.path.join(target, relative))
                    removed.append("%s/%s" % (name, relative.replace(os.sep, "/")))

        shutil.copytree(source, target, dirs_exist_ok=True)
        copied.append(name + "/")

    return copied, removed


def _list_files(folder: str, prefix: str) -> list[str]:
    """Every file under *folder*, as paths relative to it."""
    found = []
    for root, _dirs, files in os.walk(folder):
        for entry in files:
            found.append(os.path.relpath(os.path.join(root, entry), folder))
    return found


def clean(outdir: str, pages: list[str]) -> None:
    """Remove the generated HTML files."""
    removed = 0
    for name in pages:
        html = os.path.join(outdir, name[:-len(".jemdoc")] + ".html")
        if os.path.isfile(html):
            os.remove(html)
            removed += 1
    print("clean: removed %d generated HTML file(s) from %s" % (removed, outdir))


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def build(outdir: str, tidy: bool = True) -> None:
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    pages = find_pages()

    staging = tempfile.mkdtemp(prefix="jemdoc-build-")
    try:
        stage_sources(staging, pages)
        run_jemdoc(staging, pages)

        written = []
        for name in pages:
            html = name[:-len(".jemdoc")] + ".html"
            write_page(os.path.join(staging, html),
                       os.path.join(outdir, html), tidy)
            written.append(html)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    # Delete pages that a previous build wrote but which no longer have a
    # source, so that removing a www/*.jemdoc file cannot leave a stale page
    # behind in the output folder. Only files this build generated are touched.
    stale = []
    for name in sorted(os.listdir(outdir)):
        if not name.endswith(".html") or name in written:
            continue
        path = os.path.join(outdir, name)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                head = handle.read(600)
        except OSError:
            continue
        if GENERATED_MARKER in head:
            os.remove(path)
            stale.append(name)

    assets, stale_assets = copy_assets(outdir)
    stale.extend(stale_assets)

    # GitHub Pages must not run Jekyll over the output.
    with open(os.path.join(outdir, ".nojekyll"), "w", encoding="utf-8") as handle:
        handle.write("")

    # A file an earlier version of this build wrote into the output root and no
    # longer produces. `CNAME` went away when the custom domain did; a stale one
    # left behind in the output folder is confusing, and on a branch deploy it
    # would still be served.
    for name in ("CNAME",):
        path = os.path.join(outdir, name)
        if not os.path.isfile(os.path.join(ROOT, name)) and os.path.isfile(path):
            os.remove(path)
            stale.append(name)

    print("Build finished.")
    print("  output folder : %s" % outdir)
    print("  pages written : %d" % len(written))
    for name in written:
        print("                  %s" % name)
    if assets:
        print("  assets copied : %s" % ", ".join(assets))
    if stale:
        print("  stale removed : %s" % ", ".join(stale))


def serve(outdir: str, tidy: bool = True) -> None:
    """Build and then serve the site on http://localhost:8000."""
    import functools
    import http.server
    import socketserver
    import threading
    import webbrowser

    build(outdir, tidy=tidy)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=outdir)
    with socketserver.TCPServer(("127.0.0.1", 8000), handler) as httpd:
        url = "http://localhost:8000/"
        print("\nPreview server running at %s  (press Ctrl+C to stop)" % url)
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nPreview server stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the website from the .jemdoc sources in www/."
    )
    parser.add_argument(
        "-o", "--out",
        default=OUTPUT_DIR,
        help="output folder (default: _site/ in the repository root)",
    )
    parser.add_argument(
        "--serve", action="store_true",
        help="build, then serve the site locally on port 8000",
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="delete the generated HTML files instead of building",
    )
    parser.add_argument(
        "--no-tidy", action="store_true",
        help="write the HTML exactly as jemdoc produces it, without indenting it",
    )
    args = parser.parse_args()

    if not os.path.isfile(JEMDOC):
        sys.exit("error: %s not found. Are you running build.py from the "
                 "repository root?" % JEMDOC)

    if args.clean:
        clean(os.path.abspath(args.out), find_pages())
        return

    if args.serve:
        serve(args.out, tidy=not args.no_tidy)
        return

    build(args.out, tidy=not args.no_tidy)


if __name__ == "__main__":
    main()
