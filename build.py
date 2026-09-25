#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py -- build the website of Assoc. Prof. Phuong Luu Vo.

WHAT IT DOES
    1. Collects every ``www/*.jemdoc`` file (except the shared ``menu.jemdoc``).
    2. Copies them plus ``www/mysite.conf`` into a temporary staging folder,
       normalising line endings to LF. (jemdoc is sensitive to Windows CRLF
       line endings, so this step makes the build work the same everywhere.)
    3. Runs ``tools/jemdoc`` on every page, which produces ``*.html``.
    4. Copies the generated HTML plus the static folders
       (``css/``, ``files/``, ``images/``) into the output folder, and writes the
       ``.nojekyll`` marker that stops GitHub Pages from running Jekyll.

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


def find_pages() -> list[str]:
    """Return the names of all .jemdoc pages, alphabetically."""
    pages = [
        name
        for name in sorted(os.listdir(SRC))
        if name.endswith(".jemdoc") and name not in NOT_A_PAGE
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


def copy_assets(outdir: str) -> list[str]:
    """Copy css/, files/ and images/ from www/ to the output folder."""
    copied = []
    for name in ASSET_DIRS:
        source = os.path.join(SRC, name)
        if not os.path.isdir(source):
            continue
        target = os.path.join(outdir, name)
        shutil.copytree(source, target, dirs_exist_ok=True)
        copied.append(name + "/")
    return copied


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

def build(outdir: str) -> None:
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
            shutil.copyfile(os.path.join(staging, html), os.path.join(outdir, html))
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

    assets = copy_assets(outdir)

    # GitHub Pages must not run Jekyll over the output.
    with open(os.path.join(outdir, ".nojekyll"), "w", encoding="utf-8") as handle:
        handle.write("")

    print("Build finished.")
    print("  output folder : %s" % outdir)
    print("  pages written : %d" % len(written))
    for name in written:
        print("                  %s" % name)
    if assets:
        print("  assets copied : %s" % ", ".join(assets))
    if stale:
        print("  stale removed : %s" % ", ".join(stale))


def serve(outdir: str) -> None:
    """Build and then serve the site on http://localhost:8000."""
    import functools
    import http.server
    import socketserver
    import threading
    import webbrowser

    build(outdir)
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
    args = parser.parse_args()

    if not os.path.isfile(JEMDOC):
        sys.exit("error: %s not found. Are you running build.py from the "
                 "repository root?" % JEMDOC)

    if args.clean:
        clean(os.path.abspath(args.out), find_pages())
        return

    if args.serve:
        serve(args.out)
        return

    build(args.out)


if __name__ == "__main__":
    main()
