# Makefile -- a thin convenience wrapper around build.py.
#
#   make            build the whole site into _site/ (what CI does)
#   make serve      build, then preview at http://localhost:8000
#   make clean      delete the generated .html files
#   make test       run the test-suite
#   make verify     rebuild into _site/ and then run the test-suite
#   make publications   rebuild the Publications page from its BibTeX file, then build
#   make update         alias of "make publications"
#
# You do NOT need make: every target is a one-line command that you can also
# type directly, e.g.  python build.py
#
# On Windows, "make" is often not installed. Use the python commands instead,
# or run them from the VS Code terminal.

PYTHON ?= python
OUT    ?= _site

.PHONY: all build site serve clean test verify update publications

all: build

build:
	$(PYTHON) build.py --out $(OUT)

# Alias: "make site" used to be the build that CI deployed.
site: build

serve:
	$(PYTHON) build.py --serve

clean:
	$(PYTHON) build.py --clean

test:
	$(PYTHON) -m pytest

# Rebuild from scratch and then check the result. This is the one command to
# run before committing: it catches broken links, missing pages, a menu that
# points at a renamed file, and stale BibTeX.
verify:
	$(PYTHON) build.py --out _site
	$(PYTHON) -m pytest

# Rebuild the Publications page from www/data/publications.bib and then rebuild
# the site. Everything is local: the list is a file you edit, and nothing is
# fetched. Commit the regenerated www/profile/publications.jemdoc.
publications:
	$(PYTHON) tools/build_publications.py
	$(PYTHON) build.py

update: publications
