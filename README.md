# phuongluuvo.github.io

The personal and research-group website of **Assoc. Prof. Phuong Luu Vo**.

The site is written in plain-text [jemdoc](http://jemdoc.jaboc.net/) markup, is rendered by
**jemdoc + MathJax** (so all mathematical notation is typeset by MathJax in the visitor's
browser), and is published with **GitHub Pages**.

> **Not a developer?** You do not need this file. Read **[GUIDE.md](GUIDE.md)** instead — it
> explains, in plain language, which file controls which part of the site and how to change it.

---

## 1. What is in this repository

```
.
├── www/                        <-- SOURCES: this is the only place you normally edit
│   ├── mysite.conf             jemdoc + MathJax + CSS configuration
│   ├── menu.jemdoc             the shared navigation menu (used by every page)
│   ├── index.jemdoc            Home                 -> index.html
│   ├── biography.jemdoc        Biography            -> biography.html
│   ├── news.jemdoc             News                 -> news.html
│   ├── about.jemdoc            About me             -> about.html
│   ├── faculty.jemdoc          Faculty              -> faculty.html
│   ├── students.jemdoc         PhD / Master students-> students.html
│   ├── honors.jemdoc           Honors students      -> honors.html
│   ├── interns.jemdoc          Interns              -> interns.html
│   ├── prospective.jemdoc      Prospective Students -> prospective.html
│   ├── gallery.jemdoc          Gallery              -> gallery.html
│   ├── publications.jemdoc     Publications         -> publications.html
│   ├── awards.jemdoc           Awards & Grants      -> awards.html
│   ├── courses.jemdoc          Courses              -> courses.html
│   ├── mathjax-test.jemdoc     MathJax test page    -> mathjax-test.html
│   ├── css/site.css            the stylesheet (copied to css/ on build)
│   ├── files/                  CV and course materials (copied to files/ on build)
│   └── images/                 portrait and gallery images (copied to images/ on build)
│
├── build.py                    THE BUILD SCRIPT -- python build.py
├── Makefile                    convenience wrapper around build.py (optional)
├── environment.yml             conda environment "vtlp" for building and testing
├── pytest.ini                  test configuration
├── tests/test_site.py          23 tests that validate the generated site
│
├── tools/
│   ├── jemdoc                  jemdoc + MathJax (vendored, with local fixes -- see §5)
│   ├── latexmath2png.py        equation helper shipped with jemdoc (unused by this site)
│   ├── make_placeholder_pdfs.py regenerates the dummy PDFs in www/files/
│   ├── notes                   upstream developer notes for jemdoc
│   └── README-jemdoc.md        upstream README of jemdoc + MathJax
│
├── .github/workflows/pages.yml GitHub Actions: build + deploy on every push
├── .gitattributes              forces LF line endings for the sources
├── .gitignore                  ignores _site/, __pycache__, ...
├── CNAME                        custom domain (phuongluuvo.me)
├── .nojekyll                    tells GitHub Pages not to run Jekyll
│
├── *.html                      GENERATED, committed -- this is what GitHub Pages serves
├── css/site.css                GENERATED (copy of www/css/site.css)
├── files/                      GENERATED (copy of www/files/)
└── images/                     GENERATED (copy of www/images/)
```

The HTML files are generated, but they **are committed on purpose**: that way the site also
works with the simplest possible deployment ("deploy from the `main` branch"), and a push
updates the live site even if you forget to build locally.

---

## 2. Requirements

Only Python is needed. `build.py` uses nothing but the standard library, so any Python 3.9+
works (Python 3.11 is used in CI and in the conda environment).

The test-suite additionally uses `beautifulsoup4`, `lxml`, `html5lib`, `pytest`, `requests`
and `pyyaml`. A ready-made conda environment is provided:

```bash
conda env create -f environment.yml      # creates the environment named "vtlp"
conda activate vtlp
```

Or, with plain Python:

```bash
python -m pip install beautifulsoup4 lxml html5lib pytest requests pyyaml
```

---

## 3. Build, preview and test

All commands are run from the repository root.

| What you want | Command |
| --- | --- |
| Rebuild the whole site into the repository root | `python build.py` |
| Build and preview at <http://localhost:8000> | `python build.py --serve` |
| Build into a separate folder (clean deploy tree) | `python build.py --out _site` |
| Delete the generated `*.html` files | `python build.py --clean` |
| Build without regenerating `files/publications.bib` | `python build.py --no-bib` |
| Run the test-suite | `python -m pytest` |

Every `make` target is a one-line wrapper around the same commands:

```bash
make          # == python build.py
make serve    # == python build.py --serve
make site     # == python build.py --out _site
make clean    # == python build.py --clean
make test     # == python -m pytest
```

### What `python build.py` prints

```
Build finished.
  output folder : /path/to/phuongluuvo.github.io
  pages written : 14
                  about.html
                  awards.html
                  biography.html
                  courses.html
                  faculty.html
                  gallery.html
                  honors.html
                  index.html
                  interns.html
                  mathjax-test.html
                  news.html
                  prospective.html
                  publications.html
                  students.html
  assets copied : css/, files/, images/
  bibtex export : files/publications.bib (9 entries)
```

### What the build actually does

1. Collects every `www/*.jemdoc` file except `menu.jemdoc`.
2. Copies the sources **and** `www/mysite.conf` into a temporary staging directory, converting
   CRLF to LF line endings on the way (see §5 — this matters a lot on Windows).
3. Runs `tools/jemdoc -c mysite.conf <pages>` inside that directory.
4. Copies the resulting `*.html` into the output folder (the repository root by default).
5. Copies `www/css/`, `www/files/` and `www/images/` to the output folder, and writes
   `.nojekyll` and `CNAME`.
6. Re-scans `www/publications.jemdoc` for `{...}{bibtex}` code blocks and rewrites
   `files/publications.bib`, so the downloadable BibTeX file can never drift away from the
   page.

Nothing else is touched: `python build.py --clean` removes only the generated HTML.

---

## 4. Local verification (exact commands and expected output)

Performed on Windows with the conda environment `vtlp` (Python 3.11.16):

```console
$ conda env create -f environment.yml
$ conda activate vtlp
$ python build.py
Build finished.
  output folder : D:\Code\phuongluuvo.github.io
  pages written : 14
  ...
  bibtex export : files\publications.bib (9 entries)

$ python -m pytest
.......................                                                  [100%]
23 passed in 1.08s

$ python tools/make_placeholder_pdfs.py
wrote www\files\cv.pdf
wrote www\files\syllabus.pdf
wrote www\files\lecture-01.pdf
wrote www\files\lecture-02.pdf
wrote www\files\lecture-03.pdf

Done. 5 placeholder PDF(s) in www/files/.
```

After a successful build the repository root contains:

```
index.html  biography.html  news.html  about.html  faculty.html  students.html
honors.html  interns.html  prospective.html  gallery.html  publications.html
awards.html  courses.html  mathjax-test.html
css/site.css
files/cv.pdf  files/publications.bib  files/syllabus.pdf  files/lecture-0{1,2,3}.pdf
images/portrait.svg  images/gallery-{1,2,3,4}.svg
.nojekyll  CNAME
```

### What the tests check

`tests/test_site.py` builds the site into a temporary folder and then asserts, among others:

* every `.jemdoc` source produced an `.html` page;
* all pages share exactly the same menu, and each page highlights its own menu entry;
* **no broken links** — every relative `href`/`src` resolves to a file that exists;
* only external links carry `target="blank"` (internal links must stay in the same tab);
* no unescaped `&` and no HTML5 parse errors (obsolete `align=...` attributes excepted);
* MathJax is loaded on every page, and the test page really contains inline (`\(...\)`) and
  display (`\[...\]`) equations with no leftover `$`;
* publications are grouped by year, newest first, and split into journal/conference;
* the number of BibTeX blocks on the publications page equals the number of entries in
  `files/publications.bib`;
* the placeholder files really are valid PDFs;
* the GitHub Actions workflow is valid YAML;
* `build.py` normalises CRLF sources to LF.

---

## 5. Local changes to the vendored jemdoc

`tools/jemdoc` is the vendored [jemdoc+MathJax](https://github.com/wsshin/jemdoc_mathjax)
script (`jemdoc version 0.7.3`), with five small local fixes. They are all marked in the file
with a `LOCAL FIX` comment, so they are easy to re-apply if you ever update jemdoc from
upstream.

| # | Fix | Why it is needed |
| --- | --- | --- |
| 1 | `--version` decodes subprocess output as text | upstream crashes with `TypeError` on Python 3 |
| 2 | Internal links no longer get `target="blank"` | upstream forces **every** link into a new browser tab |
| 3 | `target="blank"` is written with escaped quotes | otherwise the "smart quotes" pass turns it into `target=&ldquo;blank&rdquo;` |
| 4 | `<img width="175">` instead of `<img width="175px">` | `175px` is not a valid HTML `width` and is silently ignored by browsers, which broke the portrait layout |
| 5 | Generated HTML is written with LF line endings | otherwise Windows produces CRLF, which is noisy in `git diff` |

`build.py` copes with CRLF in the *sources* as well, because jemdoc decides where a paragraph
ends by looking for a blank line, and a CRLF blank line is not recognised as a blank line. The
symptom is content being swallowed into the previous paragraph, so the build normalises the
line endings before jemdoc ever sees the files.

---

## 6. Deploying to GitHub Pages

### Method A (recommended) — GitHub Actions builds and deploys on every push

This is what `.github/workflows/pages.yml` does: on every push to `main` it runs
`python build.py --out _site` and publishes `_site` to GitHub Pages.

1. Push the repository to GitHub.
2. Open the repository on GitHub → **Settings** → **Pages**.
3. Under **Build and deployment** → **Source**, choose **GitHub Actions**.
4. Push any change to `main`. Watch the run under the **Actions** tab.
5. Your site is at `https://<user>.github.io/<repo>/`, or at the custom domain in `CNAME`.

The workflow can also be started manually: **Actions** → *Build and deploy the website* →
**Run workflow**.

### Method B — deploy the committed HTML from a branch

Because the generated HTML is committed, you can let GitHub Pages serve it directly.

1. Build locally and commit the result:
   ```bash
   python build.py
   git add -A
   git commit -m "Update website"
   git push
   ```
2. **Settings** → **Pages** → **Source**: `Deploy from a branch`.
3. Branch: `main`, folder: `/ (root)`. Save.
4. *(Optional)* Delete or disable `.github/workflows/pages.yml`; otherwise the workflow will
   also try to deploy and the two mechanisms can fight over the site.

> For a repository named `<username>.github.io`, the `main` branch root **is** the site, so
> Method B needs no folder configuration at all.

### Method C — publish only the `docs/` folder

If you prefer to keep the repository root tidy, build into `docs/` and point GitHub Pages at
that folder:

```bash
python build.py --out docs
git add -A && git commit -m "Publish site" && git push
```

Then **Settings** → **Pages** → **Source**: `Deploy from a branch`, branch `main`, folder
`/docs`, **Save**. `CNAME` and `.nojekyll` are written into `docs/` as well, so the custom
domain keeps working.

> Use **one** of the three methods. Methods B and C deploy HTML that is committed; Method A
> builds on GitHub. Running more than one at a time makes it unclear which version is live.

### Custom domain

`CNAME` contains `phuongluuvo.me`, and `build.py` copies it into the build output (and
`build.py --out _site` copies it too, so both deployment methods work).

* To keep the domain: in **Settings** → **Pages** → **Custom domain**, enter the domain and
  enable *Enforce HTTPS*.
* To drop the custom domain: delete the `CNAME` file, and remove the domain from the same
  settings page.

DNS for `phuongluuvo.me` should point at GitHub Pages (four `A` records for the apex domain,
or a `CNAME` record for a `www` subdomain). See GitHub's documentation, *"Managing a custom
domain for your GitHub Pages site"*.

---

## 7. Placeholders that ship with the demo

Everything below is dummy content, chosen so that the site is complete and every link works.
Replace it with the real data; [GUIDE.md](GUIDE.md) lists the exact file for each item.

| Placeholder | Where |
| --- | --- |
| `Example University`, `Example Transactions on ...` | all pages |
| Email `phuong.luuvo@example.edu` | `www/index.jemdoc`, `www/about.jemdoc` |
| Google Scholar id `XXXXXXXX`, ORCID `0000-0000-0000-0000` | `www/index.jemdoc`, `www/about.jemdoc` |
| Portrait photo | `www/images/portrait.svg` |
| Gallery photos | `www/images/gallery-{1..4}.svg` |
| CV | `www/files/cv.pdf` |
| Course materials | `www/files/syllabus.pdf`, `www/files/lecture-0{1,2,3}.pdf` |
| Students, faculty, news, publications, awards, courses | the matching `.jemdoc` page |

---

## 8. Licence and credits

* The website content is © Assoc. Prof. Phuong Luu Vo.
* `tools/jemdoc` is **jemdoc + MathJax** by Jacob Mattingley and Wonseok Shin, distributed
  under the **GNU GPL v3** (see the header of the file). `tools/README-jemdoc.md` is its
  original README.
* MathJax is loaded from the jsDelivr CDN and is licensed under Apache-2.0.
