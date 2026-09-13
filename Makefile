# Makefile -- a thin convenience wrapper around build.py.
#
#   make            build the site into the repository root
#   make serve      build, then preview at http://localhost:8000
#   make site       build into _site/  (this is what GitHub Actions deploys)
#   make clean      delete the generated .html files
#   make test       run the test-suite
#
# You do NOT need make: every target is a one-line command that you can also
# type directly, e.g.  python build.py
#
# On Windows, "make" is often not installed. Use the python commands instead,
# or run them from the VS Code terminal.

PYTHON ?= python
OUT    ?= .

.PHONY: all build site serve clean test

all: build

build:
	$(PYTHON) build.py --out $(OUT)

site:
	$(PYTHON) build.py --out _site

serve:
	$(PYTHON) build.py --serve

clean:
	$(PYTHON) build.py --clean

test:
	$(PYTHON) -m pytest
