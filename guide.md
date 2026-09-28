# guide.md — running, editing and publishing this website

This is the single entry point for this repository. It is written for **two readers at the same
time**:

* a **human** — the site owner or a contributor, with no programming background; and
* an **AI coding agent** picking the repository up cold.

Everything applies to both. If you are an AI agent, read
[§13 Notes for AI coding agents](#13-notes-for-ai-coding-agents) first — it is a short list of
hard rules — then use the rest as reference.

This file is the **only** manual. [`AGENTS.md`](AGENTS.md) is a deliberately short summary of
the hard rules for AI agents and links back here; there is no third document to keep in step.

---

## Start here

Four commands, run in this folder. That is the whole workflow.

```bash
python build.py              # rebuild the site into _site/
python build.py --serve      # rebuild, then look at it at http://localhost:8000
python -m pytest             # run the checks (needs the "vtlp" environment)
make verify                  # build and check, in one go
```

**To publish:** commit and push. GitHub rebuilds the site from `www/` and puts it online. There
is no upload step, and nothing is visible to anyone until you push.

**The one rule:** never edit a file inside `_site/`. It is the build's *output*; `build.py`
rewrites all 15 pages on every run, so a change made there is wiped by the next build. Edit the
matching `www/` file — the table in [§6.1](#61-which-file-do-i-edit) tells you which one for any
given page.

| | |
| --- | --- |
| **Sources** | everything you edit lives in `www/` |
| **Output** | `_site/`, generated, gitignored, never committed |
| **Publish** | `git push` — CI builds and deploys it |
| **Course files** (notes, slides) | `www/pdf/courses/<course>/`; its address is one line in `www/mysite.conf` — see [§9.4](#94-add-a-course) |
| **Generated page** | only `www/research/publications.jemdoc` is written by `tools/update_site.py`; run `make update`. The news is hand-written on the Home page |
| **The one thing that bites** | editing `_site/` instead of `www/`, and not pushing |

---

## Contents

1. [Overview](#1-overview)
2. [Folder structure](#2-folder-structure)
3. [Prerequisites](#3-prerequisites)
4. [Build](#4-build)
5. [Local preview](#5-local-preview)
6. [Adding or editing a page](#6-adding-or-editing-a-page)
7. [Math and MathJax conventions](#7-math-and-mathjax-conventions)
8. [Style and formatting conventions](#8-style-and-formatting-conventions)
9. [Task recipes](#9-task-recipes)
10. [Testing and validation checklist](#10-testing-and-validation-checklist)
11. [Deployment](#11-deployment)
12. [Troubleshooting](#12-troubleshooting)
13. [Notes for AI coding agents](#13-notes-for-ai-coding-agents)
14. [Where to learn more](#14-where-to-learn-more)

---

## 1. Overview

This repository is the personal and research-group website of **Assoc. Prof. Phuong Luu Vo**,
published at **<https://phuongluuvo.github.io>** with **GitHub
Pages**.

| Piece | What it does |
| --- | --- |
| **jemdoc** | A tiny text-to-HTML converter. Plain-text `.jemdoc` files are compiled into `.html` files. jemdoc is *not* installed from PyPI — a vendored copy lives in `tools/jemdoc`. |
| **MathJax 3** | Loaded client-side from the jsDelivr CDN. It typesets LaTeX (`$...$`, `\(...\)`) in the visitor's browser. Nothing is pre-rendered at build time, so equations need internet access to appear. |
| **`build.py`** | The one build script. It normalises line endings, runs jemdoc over every source page, copies the assets, and clears out pages whose source has gone. Standard library only — no dependencies. |
| **`tools/update_site.py`** | Regenerates the one generated page, `www/research/publications.jemdoc`, from the ORCID record, with the full author list, volume, pages and DOI from Crossref. Anything ORCID does not have yet goes into `www/data/publications-extra.bib`. Run `make update` when you publish something. It no longer touches the news: that list is hand-written on the Home page. |
| **`tests/test_site.py`** | The automated checks on the *generated* site: no broken links, identical menu on every page, a menu entry that highlights itself, valid HTML and UTF-8, MathJax present, a well-formed publication list, and a Home page whose news lines keep their `MM/YYYY:` shape. |

**The one rule that matters:** you edit the `.jemdoc` sources in `www/`, and `build.py` turns
them into the `.html` files that GitHub Pages serves. You never edit the `.html` files.

---

## 2. Folder structure

```
phuongluuvo.github.io/
│
├── www/                     ◄── SOURCES. The only place you normally edit.
│   ├── mysite.conf              jemdoc control file: <head>, MathJax config, CSS link,
│   │                            page-title suffix, footer  (= the shared "include")
│   ├── menu.jemdoc              sidebar for the main site
│   ├── menu-lab.jemdoc          sidebar for the Edge AI Lab pages
│   ├── menu-blog.jemdoc         sidebar for the blog pages
│   │   ── the pages. One file = one page, and the folder is only for your own
│   │      benefit: every page is built to the top of _site/, so its address is
│   │      still name.html and no link has to know where the source lives.
│   ├── home/
│   │   └── index.jemdoc             Home: hero + About + News + Awards + Contact
│   ├── blog/                    one page per post: a chapter, written from www/files/blog/ (see §9.12)
│   │   ├── chap1.jemdoc             Bài toán quy hoạch tuyến tính
│   │   ├── chap2.jemdoc             Hàm lồi
│   │   ├── chap3.jemdoc             Bài toán tối ưu lồi
│   │   ├── chap4.jemdoc             Các giải thuật bậc một
│   │   └── chap5.jemdoc             Lý thuyết đối ngẫu
│   ├── research/
│   │   ├── interests.jemdoc         Research Interests
│   │   ├── publications.jemdoc      Publications (GENERATED)
│   │   └── gallery.jemdoc           Gallery
│   ├── teaching/
│   │   ├── algorithm-optimization.jemdoc   IT545 -- one page, its slides are downloads
│   │   ├── regression-analysis.jemdoc      the second course
│   │   └── joining.jemdoc           Prethesis and Thesis
│   ├── lab/                     the Edge AI Lab, which has its own sidebar
│   │   ├── lab.jemdoc               Lab home
│   │   ├── lab-members.jemdoc       Members
│   │   ├── lab-projects.jemdoc      Projects
│   │   └── lab-news.jemdoc          Lab news
│   ├── misc/mathjax-test.jemdoc the MathJax check page
│   ├── data/
│   │   └── publications-extra.bib   BibTeX ORCID does not have (see §9.2)
│   ├── css/site.css             the stylesheet source
│   ├── images/                  pictures shown on a page   ┐ copied into the output
│   ├── pdf/                     the slides the courses hand ┘ on every build
│   │                            out (www/pdf/courses/…)
│   └── files/                   documents visitors download, and the LaTeX
│                                chapters the blog is written from (files/blog/)
│
├── build.py                 THE BUILD SCRIPT          →  python build.py
├── Makefile                 optional one-word wrappers (make, make serve, make verify)
├── guide.md                 this file
├── AGENTS.md                hard rules for AI coding agents
├── requirements.txt         test dependencies, pip     ┐ keep the two in sync
├── environment.yml          conda environment "vtlp"  ┘
├── pytest.ini               test configuration
├── tests/test_site.py       the automated checks
│
├── tools/                   helper scripts; jemdoc itself is third-party
│   ├── jemdoc                   vendored jemdoc + MathJax 0.7.3 with 5 local fixes (see below)
│   ├── update_site.py           regenerates www/research/publications.jemdoc
│   └── README-jemdoc.md         upstream jemdoc README (provenance and licence)
│
├── .github/workflows/pages.yml  CI: build + deploy, and a rebuild-and-test job
├── .gitattributes               forces LF line endings on the sources (important!)
├── .gitignore                   ignores the build output and caches
│
└── _site/                   GENERATED by build.py. Gitignored, never committed.
```

**One-line purpose per folder**

| Folder | Purpose |
| --- | --- |
| `www/` | All hand-edited sources: pages, sidebars, control file, stylesheet, and assets. |
| `www/home/`, `www/research/`, `www/teaching/`, `www/lab/`, `www/misc/` | The pages, grouped so the folder says what a page is for. **Organisation only** -- a page built from `www/teaching/it545.jemdoc` is still `it545.html` at the top level, and so is every link to it. |
| `www/data/` | The two files you edit by hand: your own announcements, and BibTeX for papers ORCID does not have. |
| `www/images/` | Pictures that appear **on a page**. Copied into the output on build. |
| `www/files/` | Documents visitors **download**. Copied into the output on build. Absent until you have one. |
| `tools/` | The generator, and vendored third-party tools. |
| `tests/` | Automated checks. Run them before every commit. |
| `.github/workflows/` | GitHub Actions: build, deploy, test. |
| `_site/` | **Generated.** The entire website. Ignored by git; it exists only after a build. |

### Where do I put a file?

This is worth reading carefully, because a file in the wrong place produces a broken link
instead of an error.

| The file is… | Put it in | Link to it as |
| --- | --- | --- |
| a photo, a diagram or an icon shown **on a page** | `www/images/` | `images/your-file.png` |
| a document a visitor **downloads** (CV, poster, syllabus) | `www/files/` | `files/your-file.pdf` |
| a **course** handout, slide deck or exam paper | `www/pdf/courses/<course>/` — see [§9.4](#94-add-a-course) | a button written as `%%IT545%%/lec1.pdf` |
| a new page | the folder in `www/` that fits — `teaching/`, `research/`, `lab/`… | — |

Three rules that matter:

* **Names:** lower case, hyphens, no spaces, no accents — `gallery-5.jpg`, not `Gallery 5.JPG`.
  Git and GitHub Pages are case-sensitive even though Windows is not.
* **Create the folder if it does not exist.** `www/files/` probably does not exist until you
  add your first download; `mkdir www/files` and put the file in it. The build picks up any
  folder in `ASSET_DIRS` at the top of `build.py`.
* **Add the link as well as the file.** An image with no `<img>` and a PDF with no `<a>` are
  invisible to visitors, and nothing in the test-suite can complain about a file nobody
  mentions. Conversely, a link to a file that is not there *is* caught:
  `test_every_local_link_and_image_resolves` fails with the missing path.

**Never edit anything under `_site/`.** That folder is generated from `www/` on every build,
and it is made to mirror the sources exactly — a file you delete from `www/` is deleted from
`_site/` by the next build, and a file you add to `_site/` by hand is left where it is but is
not part of the site.

### Where the generated site goes

`python build.py` writes the **whole** site into `_site/`: the HTML pages, a copy of the
stylesheet and the assets, and `.nojekyll`. Pages left over from an earlier build
whose source no longer exists are deleted from the output folder, so removing a page cannot
leave a stale one behind.

`_site/` is **not committed** and is listed in `.gitignore`. GitHub Actions runs the same build
on a clean machine and deploys the result, so the published site never comes from a committed
file. The repository therefore contains sources, tooling and documentation only — there is no
second copy of the output to keep in step by hand.

Every generated page carries a `GENERATED FILE. DO NOT EDIT` comment in its `<head>`, so that
nobody edits the output instead of the source.

> Need the output somewhere else? `python build.py --out docs` writes it into `docs/`
> instead; see [§11](#11-deployment).

### The vendored jemdoc and its five local fixes

`tools/jemdoc` is [jemdoc+MathJax](https://github.com/wsshin/jemdoc_mathjax), `jemdoc version
0.7.3`, copied into the repository because it cannot be installed from PyPI. **Five small
patches** were applied on top of upstream. Each is marked in the file with a `LOCAL FIX`
comment, which is how they can be re-applied if jemdoc is ever updated:

| # | Fix | Why it is needed |
| --- | --- | --- |
| 1 | `--version` decodes subprocess output as text | upstream crashes with `TypeError` on Python 3 |
| 2 | Internal links no longer get `target="blank"` | upstream forces **every** link into a new browser tab |
| 3 | `target="blank"` is written with escaped quotes | otherwise the "smart quotes" pass rewrites it as `target=&ldquo;blank&rdquo;` |
| 4 | `<img width="175">` instead of `<img width="175px">` | `175px` is not a valid HTML `width`, so browsers ignore it and the portrait layout breaks |
| 5 | Generated HTML is written with LF line endings | Windows would otherwise produce CRLF, which is noisy in `git diff` |

Patches 1–4 are why `test_internal_links_do_not_open_a_new_tab`, `test_external_links_open_a_new_tab`
and the portrait layout behave the way they do. Patch 5, together with the CRLF → LF
normalisation in `build.py`, is why the build behaves identically on Windows, macOS and Linux.
**Do not reformat them, and do not remove the `PYTHONUTF8=1` environment variable that
`build.py` passes to jemdoc** — without it jemdoc writes its HTML in the platform code page
(cp1252 on Windows), so curly quotes and dashes stop being valid UTF-8.

`tools/jemdoc` and `tools/README-jemdoc.md` are the only files in the repository that were not
written for this site; see [§14](#14-where-to-learn-more) for their licence.

---

## 3. Prerequisites

| Need | Notes |
| --- | --- |
| **Python 3.9 or newer** | `build.py` uses nothing but the standard library. Python 3.11 is used by CI; the site has been built with 3.11 and 3.14. |
| **jemdoc** | **Nothing to install.** The exact version used by the site is vendored at `tools/jemdoc`, with five local fixes applied (see [§2](#2-folder-structure)). Do not `pip install` jemdoc. |
| **Perl** | Not needed. |
| **`make`** | Optional. Every `make` target is a one-line wrapper around a `python` command. On Windows, `make` is usually absent — use the `python` commands directly. |

For the **test-suite** only, you also need a few packages. They are listed in exactly one
place per package manager — [`requirements.txt`](requirements.txt) for pip and
[`environment.yml`](environment.yml) for conda — so keep those two lists in sync:

```bash
conda env create -f environment.yml      # creates the environment named "vtlp"
conda activate vtlp                      # once per terminal session
```

Without conda:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt    # Windows
.venv/bin/python   -m pip install -r requirements.txt      # macOS / Linux
```

> A freshly created virtual environment contains **none** of them, so `python -m pytest` fails
> with `No module named pytest` until you run the install line. That is the single most common
> cause of a "failing" test-suite.

`build.py` itself needs **none** of these — keep it that way (see
[§13](#13-notes-for-ai-coding-agents)).

---

## 4. Build

Run every command from the **repository root** (the folder that contains `build.py`):

```bash
python build.py
```

That rebuilds the whole site into `_site/`: every `.html` page, a copy of `www/css/`,
`www/files/` and `www/images/`, plus `.nojekyll`. Nothing outside `_site/` is
touched.

Expected output:

```
Build finished.
  output folder : /path/to/phuongluuvo.github.io/_site
  pages written : 15
                  awards.html
                  ee301.html
                  ...
  assets copied : css/, images/
  stale removed : biography.html, faculty.html, students.html, files/cv.pdf
```

If `pages written` does not match the number of pages in `www/` — every `.jemdoc` file there
except the `menu*.jemdoc` files and `mysite.conf`, which is 16 at the time of writing — or a
page is missing from the list, then a source file was not picked up: check that it is directly
inside `www/` and ends in `.jemdoc`.

The `stale removed` line lists output files whose source has gone, and it is normal after a
rename or a deletion. It covers two different things:

* **pages** the build generated earlier — only files carrying the `GENERATED FILE` banner are
  removed, so a hand-written `.html` file in the output folder is never touched;
* **assets** — a file you deleted from `www/images/` or `www/files/`. The asset folders are
  *mirrored*: the output is made to match the source rather than only added to, so removing a
  picture or a PDF from `www/` removes it from the output on the next build.

`assets copied` lists the folders that exist in `www/`. A missing `files/` there is normal —
the folder only appears once you have something to download.

### What the build actually does

1. Collects every `.jemdoc` file anywhere under `www/`, skipping `mysite.conf` and every file
   whose name starts with
   `menu` (`menu.jemdoc`, `menu-lab.jemdoc`, `menu-blog.jemdoc`), because a menu is included
   by pages rather than built into a page of its own.
2. Copies the sources **and** `www/mysite.conf` into a temporary staging folder, converting
   CRLF to LF on the way. This matters: jemdoc decides where a paragraph ends by looking for a
   blank line, and a Windows CRLF blank line is not blank to jemdoc, so content silently
   merges. Keeping the sources at LF (`www/` is safe via `.gitattributes`) plus this
   normalisation makes the build identical on Windows, macOS, Linux and CI.
3. Runs `tools/jemdoc -c mysite.conf <pages>` inside the staging folder. Relative paths inside
   a page (`css/site.css`, `images/portrait.jpg`) therefore resolve from the **site root**.
4. Indents that HTML so that it can be read. jemdoc writes its own tags at column zero and
   passes the tags copied out of a page through with whatever indentation the page gave them,
   so the two styles run together and the nesting cannot be followed. Only the whitespace in
   front of a line is rewritten -- never the text, and no line is ever split or joined -- so
   the page itself cannot change. `--no-tidy` skips this step.
5. Copies the generated `*.html` into the output folder (`_site/` unless `--out` says
   otherwise).
6. Copies `www/css/`, `www/images/` and `www/files/` into the output, **mirroring** them:
   anything in the output that is no longer in `www/` is deleted, so a removed image or PDF
   cannot linger. Writes the `.nojekyll` marker that stops GitHub Pages running Jekyll.
7. Deletes pages from the output folder that an earlier build wrote but that no longer have a
   source, so that removing a page cannot leave a stale one behind.

Nothing else is touched.

### Command reference

| What you want | Command |
| --- | --- |
| Rebuild the whole site into `_site/` (normal case) | `python build.py` |
| Build and preview in a browser | `python build.py --serve` |
| Build into a different folder | `python build.py --out docs` |
| Delete the generated `*.html` files | `python build.py --clean` |
| Build without indenting the HTML | `python build.py --no-tidy` |
| Rebuild **and** run every check | `make verify` |
| Run only the checks | `python -m pytest` |
| Refresh the generated Publications page from ORCID | `make update` |

`make` wrappers: `make` = `python build.py`, `make site` = the same (an alias),
`make serve` = `--serve`, `make clean` = `--clean`, `make test` = `pytest`,
`make verify` = build to `_site/` + `pytest`, `make update` = refresh the generated Publications
page from ORCID + build. `make publications` is an alias of `make update`, and there is nothing
else to refresh: the news is hand-written.

*(`python build.py --clean` removes only the generated HTML files from the output folder; the
copies of `css/`, `files/` and `images/` are left alone.)*

---

## 5. Local preview

```bash
python build.py --serve
```

This builds the site and starts a small web server on <http://localhost:8000/>, opening your
browser automatically. Press <kbd>Ctrl</kbd>+<kbd>C</kbd> in the terminal to stop it.

Use the preview, not a local `file://` view, so that the layout and the relative paths behave
exactly as they do online.

If the site looks stale, force a reload (<kbd>Ctrl</kbd>+<kbd>F5</kbd>) — browsers cache CSS
aggressively.

**Previewing without Python:** any static server works, e.g. `python -m http.server` inside
the `_site/` folder produced by `python build.py`.

---

## 6. Adding or editing a page

**Rule of thumb: one `.jemdoc` file = one page.** You edit a page in three steps:

1. Edit (or create) the `.jemdoc` file in `www/`.
2. If the page is new, add one line to `www/menu.jemdoc`.
3. Run `python build.py`, then check with `python build.py --serve`.

### 6.1 Which file controls what

| What you want to change | Edit this file |
| --- | --- |
| The sidebar on the main-site pages | `www/menu.jemdoc` |
| The sidebar inside the Edge AI Lab | `www/menu-lab.jemdoc` |
| The sidebar inside the blog | `www/menu-blog.jemdoc` |
| Colours, fonts, spacing, page width, the profile header | `www/css/site.css` — the palette is the first block |
| The MathJax setup, the `<head>`, the page-title suffix, the footer, the favicon | `www/mysite.conf` |
| Home: the profile header, About (appointments + education), the news list, the awards, contact | `www/home/index.jemdoc` — see [§9.1](#91-add-a-news-item) and [§9.5](#95-add-an-award-or-a-grant) |
| Research interests (current / past) | `www/research/interests.jemdoc` |
| Publications | `www/research/publications.jemdoc` — **generated**, see [§9.2](#92-refresh-the-publication-list) |
| A paper that ORCID does not have yet | paste BibTeX into `www/data/publications-extra.bib`, then `make update` |
| The Blog, and where its PDFs live | `www/blog/blog.jemdoc`, plus the `blog` line in `www/mysite.conf` — see [§9.12](#912-add-a-blog-post) |
| The Edge AI Lab: description, people, projects, lab news | `www/lab/lab.jemdoc`, `www/lab/lab-members.jemdoc`, `www/lab/lab-projects.jemdoc`, `www/lab/lab-news.jemdoc` |
| One course, everything on it (info, slides, textbook, files) | `www/teaching/it545.jemdoc` |
| Prethesis, thesis and internship projects | `www/teaching/joining.jemdoc` |
| Photo gallery | `www/research/gallery.jemdoc` + files in `www/images/` |
| A document visitors download (CV, poster, syllabus) | put it in `www/files/`, then link it — see [§2](#2-folder-structure) |
| The portrait in the profile header | replace `www/images/portrait.jpg` |
| The MathJax check page | `www/misc/mathjax-test.jemdoc` |

> **Never edit anything inside `_site/`.** It is the build's *output*, not a source. `build.py`
> rewrites every page on every run, so anything changed there is wiped the next time you
> build, commit or push — and the site reverts to whatever the `www/` sources say. If a page
> shows something you want different, find its source in the table above and change that.
>
> One of those sources is itself generated: `www/research/publications.jemdoc`. Do not edit the
> `.jemdoc` — edit `www/data/publications-extra.bib` instead, then run `make update`.

### 6.2 The first line of every page

Every page starts with a jemdoc control comment:

```
# jemdoc: menu{menu.jemdoc}{blog.html}, title{Blog}, notime
= Blog
Notes and longer write-ups
```

* `menu{menu.jemdoc}{blog.html}` — the first value is the shared menu file, the **second must
  be the page's own `.html` name**. That is what makes the menu entry highlight itself. If it
  does not match, nothing is highlighted (and the test-suite will tell you).
* `title{...}` — used for the browser tab and the page heading, unless a `= Heading` follows.
* `notime` — omits the time of day from the "last updated" footer; keep it so dates stay
  `YYYY-MM-DD`.
* `= Page title` — the big `<h1>`. The **next line** becomes the grey subtitle.

### 6.3 Adding a new page

1. Copy an existing page:

   ```bash
   cp www/blog/blog.jemdoc www/seminars.jemdoc
   ```

2. Edit it. Change the first line so the second value matches the new file name, then write the
   content:

   ```
   # jemdoc: menu{menu.jemdoc}{seminars.html}, notime
   = Seminars
   Talks hosted by the group
   ```

3. Add the page to the menu, `www/menu.jemdoc`:

   ```
    Seminars [seminars.html]
   ```

   Put it in the right section, in the order you want it to appear. But keep `www/menu.jemdoc`
   tidy — see [§8.1](#81-file-names).

4. Rebuild and verify:

   ```bash
   python build.py --serve
   ```

   Then commit both the `.jemdoc` **and** the generated `.html`.

### 6.4 The two menus

There are three menu files, and every page includes exactly one of them:

| Menu file | Used by | Sidebar shows |
| --- | --- | --- |
| `www/menu.jemdoc` | every page of the main site, the course pages included | the whole site |
| `www/menu-lab.jemdoc` | `lab.html` and the three other lab pages | the lab, and Home |
| `www/menu-blog.jemdoc` | `blog.html`, and the rest as you add them | the posts, and Home |

Two sections have a sidebar of their own: the Edge AI Lab and the blog. Click *Lab* or *Blog* on
the main site and you land inside that section, with its own sidebar and a `Home` back out.

The course pages are deliberately **not** like that: a course reads under the main site's own
sidebar, the way the Interests page does, with the courses listed under the `Teaching` heading.

**The courses are ordinary pages of the main site.** The Teaching group lists them beside
Prethesis and Thesis, exactly the same way, and each course page shows the main sidebar. There
used to be a course overview page and a shared course sidebar; both were removed, because a
course list in the sidebar and a course list in the menu were the same information twice.

`build.py` never turns a `menu*.jemdoc` file into a page of its own — it is only ever included,
and a menu no page includes is dead weight: the test-suite counts the menus that actually appear
and fails when that number does not match the number of `menu*.jemdoc` files.

```
Phuong Vo
 Home [index.html]
 Blog [blog.html]
Research
 Lab [lab.html]
 Interests [interests.html]
 Publications [publications.html]
 #Gallery [gallery.html]
Teaching
 Algorithm Optimization [it545.html]
 Thesis [joining.html]
```

* **The first line is the site name, and it is a heading, not a link** — like `Research` and
  `Teaching`, it is there to brand the sidebar. The way home is the **`Home` entry under it**,
  and a test asserts that the first *entry* of every menu links to `index.html` so no page is a
  dead end. On the lab pages there is no site name at all: their menu opens with `Home`.
* A line **without** brackets is a coloured category heading (`Research`, `Teaching`).
* A line **with** brackets is a link: ` Visible text [target-file.html]`.
* The order in the file is the order on every page of that group.
* **A label stays on one row.** jemdoc turns the spaces in a plain label into non-breaking
  spaces, so it never wraps — which means `--menu-width` in `www/css/site.css` has to be wide
  enough for the longest one. It is set for `Algorithm Optimization`. A `{{long label}}` in
  double braces is the opposite: it lets the label wrap.
* **One page name must never be the tail of another.** jemdoc marks a menu entry current with a
  suffix test (`link[-len(current):] == current` in `tools/jemdoc`), so a page called
  `news.html` would light up whenever `lab-news.html` was current — which is why the lab's news
  page is called `lab-news.html`. Call every page by a name no other page ends with.
* **Two entries must not point at the same page**, or both light up at once.
* `mathjax-test.html` is deliberately **not** a menu entry, so nothing is highlighted when you
  are on it. A test asserts exactly that.

### 6.5 Deleting a page

1. Delete the `www/*.jemdoc` file.
2. Remove its line from `www/menu.jemdoc`, and any link to it from other pages.
3. `python build.py --clean` removes the stale generated HTML.
4. `python build.py` and `python -m pytest`. The test-suite fails if any page still links to
   the deleted one, which is exactly the point.

### 6.6 The site-wide `<head>`, footer and MathJax

`www/mysite.conf` is jemdoc's *control file*. Each `[section]` in it replaces a built-in jemdoc
default. Sections are ended by a **blank line**, so never leave a blank line inside a section.
Lines starting with `#` are comments.

| Section | Controls |
| --- | --- |
| `[firstbit]` | The whole `<head>`: `<!DOCTYPE html>`, the metadata, the Literata font link, the MathJax loader. |
| `[defaultcss]` | The stylesheet link (`css/site.css`). |
| `[doctitle]` | The `<h1>` markup (currently a link back to the home page). |
| `[windowtitle]` | The browser-tab title, `Page name · Phuong Luu Vo`. |
| `[lastupdated]` | The footer line: the date, and nothing else. |

### 6.7 No visitor counter

The site used to count visits with **Busuanzi** (<https://ibruce.info>), a free public counter
that needed no account and no setting to switch on. **It was removed at the site owner's
request**, and nothing replaced it: the footer is the date and nothing else.

The totals were the whole website's rather than one page's, so any page raised the same single
number — a figure that said nothing about what was being read, at the price of a request to a
third party on every page.

Adding one back means two things in `www/mysite.conf`: a `<script>` in `[firstbit]`, and a span
beside the date in `[lastupdated]`. `test_no_page_counts_visitors` checks that neither is there,
so deleting that test is part of adding a counter.

> **Careful when editing `[firstbit]` or `[lastupdated]`.** A section ends at the first blank
> line, and one stray blank line silently drops everything after it — the footer, or the whole
> `</head>`. An HTML comment must also contain no double hyphen (`--`), which makes the page
> invalid. `test_no_page_counts_visitors` and `test_every_page_has_a_title_and_the_stylesheet`
> between them catch both: the first looks for a counter on all 14 pages, the second for the
> footer itself.

---

## 7. Math and MathJax conventions

### 7.1 Where MathJax lives

There is **exactly one** MathJax setup in this repository: the `[firstbit]` section of
`www/mysite.conf`. It contains the `window.MathJax` configuration **and** the single
`<script id="MathJax-script" ...>` tag that loads MathJax 3 from the jsDelivr CDN. Because
`[firstbit]` is emitted on every page, every page gets it automatically.

> **Never add a MathJax `<script>` tag to an individual page.** If a page needs a different
> configuration, that configuration belongs in `www/mysite.conf`. The test-suite asserts that
> every generated page loads MathJax, so a second, inconsistent include would show up as
> duplication rather than a fix.

### 7.2 Writing equations

Delimiters are configured in `www/mysite.conf` as:

| Type | Delimiters | Example |
| --- | --- | --- |
| Inline | `$...$` or `\(...\)` | `The SNR is $\gamma_k = p_k h_k / \sigma^2$.` |
| Display | `$$...$$` or `\[...\]` | see below |

**Display equations in `.jemdoc` files are written with `\(` and `\)` on their own lines**
(that is the jemdoc + MathJax convention used throughout this site):

```
\(
\gamma_k = \frac{p_k\, h_k}{\sigma^2}, \qquad k = 1, 2, \ldots, K .
\)
```

A longer example, straight from the Home page:

```
\(
\begin{array}{ll}
\mbox{maximize} & \displaystyle \sum_{k=1}^{K} \log_2\!\left(1 + \frac{p_k\,h_k}{\sigma^2}\right) \\
\mbox{subject to} & \displaystyle \sum_{k=1}^{K} p_k \le P_{\max}, \qquad p_k \ge 0 .
\end{array}
\)
```

Conventions worth keeping:

* Put the delimiters on their own lines, and keep the LaTeX indented under them.
* `\M` is jemdoc's small separator dot (`·`) — not a math command.
* Use `\,` and `\!` for spacing; use `\mbox{}` (not `\text{}`) inside `array`, to match the
  existing pages.
* Inline `$` is safe inside normal paragraphs, but a paragraph containing **two** `$` on one
  line will be typeset by MathJax. Another reason to keep `/` and `$` usage deliberate
  (see [§8.3](#83-inline-syntax-gotchas)).

### 7.3 How to test that it renders

1. `python build.py --serve`
2. Open <http://localhost:8000/mathjax-test.html> — the dedicated check page, linked from the
   Home page. It shows an inline equation, a display equation, and a matrix-style alignment.
3. If the three expressions look like typeset mathematics, MathJax works. If you see raw
   dollar signs and backslashes, MathJax did not load: check for internet access (it is a CDN
   script), then check the browser console for a failed request to the MathJax URL, then check
   that `www/mysite.conf` still contains the `MathJax-script` line.
4. Automated: `python -m pytest` asserts that every page loads MathJax and that the test page
   still contains both inline and display equations with no leftover raw `$`.

MathJax renders in the visitor's browser, never at build time, so equations are absent for a
visitor with no internet connection. That is expected and harmless.

---

## 8. Style and formatting conventions

### 8.1 File names

* **Lower case, hyphen-separated, ASCII only**: `lab-members.jemdoc`, `mathjax-test.jemdoc`,
  `lecture-01.pdf`. Never use spaces, never mix case, never use accents.
* Pages are always `.jemdoc`; the generated name is the same word with `.html`
  (`lab-members.jemdoc` → `lab-members.html`). **The two names must correspond** — links and
  the menu refer to the `.html` name, the menu's own entry must match it, and `build.py`
  derives one from the other.
* Assets follow the same rule: `portrait.jpg`, `lecture-01.pdf`.
* Prefer lower case even on Windows/macOS, where the filesystem would let you get away with
  anything: git and GitHub Pages are case-sensitive, and a case-only rename is a common source
  of "it works on my machine".
* One exception exists and should stay the only one: `.nojekyll`, which is GitHub's own
  specified name.

### 8.2 Heading levels

| You write | You get | Use for |
| --- | --- | --- |
| `= Title` (plus subtitle on the next line) | the page heading + grey subtitle | once, at the top of each page |
| `== Section` | a section heading | main sections |
| `=== Subsection` | a smaller heading | subdivisions |

Use exactly one `=` heading per page — the test-suite asserts every page has an `<h1>`.

### 8.3 Inline syntax gotchas

| You write | You get |
| --- | --- |
| `*bold*` | **bold** |
| `/italics/` | *italics* |
| `_underline_` | underline |
| `+monospace+` | `monospace` |
| `[https://example.com Label]` | a link (URL first, visible text second) |
| `[publications.html Publications]` | a link to a page of this site |
| `[name@example.edu]` | a mail link with an envelope badge |
| `- item` | a bullet (indent the next line to continue it) |
| a blank line | the end of a paragraph — **required** between paragraphs |

1. **`\n` at the end of a line forces a line break.** Without it, consecutive lines are joined
   into one flowing paragraph. This is how student entries put name / topic / email on
   separate lines.
2. **Two `/` on one line become italics.** Write `\/` for a literal slash when another `/` is
   on the same line. Journal names like `/IEEE Transactions on Wireless Communications/` are
   intentional italics.
3. **`#` starts a comment** to end of line. Put a **blank line before** a comment, or it glues
   two paragraphs together. Write `\#` for a literal hash.
4. **A line starting with `-`, `.`, `:`, `=`, `~` or `{`** is a list item, heading or block —
   never begin a normal sentence with one of those characters.
5. **`&` must be written `&amp;`** in prose. A bare `&` makes the HTML invalid and the
   test-suite will fail. (In `www/menu.jemdoc` jemdoc handles the labels, but pages are yours
   to get right.)

### 8.4 Images

* Keep images in `www/images/`, reasonably small (under roughly 300 KB) so pages stay fast.
* Reference them **relative to the site root**: `images/portrait.jpg`, not `www/images/...`.
* The full path is what the visitor's browser downloads, and `build.py` copies `www/images/` to
  `images/`.
* Always write a meaningful `alt` text.
* A plain image in a paragraph: `{}{img_left}{images/portrait.jpg}{Alt text}{175}{}{}` -- the
  seven fields are `{title}{img_left}{file}{alt}{width}{height}{link}`. Leave the width blank
  to use the image's natural size.
* Gallery photos use raw HTML inside a `<div class="gallery">` block in
  `www/research/gallery.jemdoc`; the grid rearranges itself for any number of photos. See
  [§9.6](#96-add-a-photo-to-the-gallery).
* `width` must be a bare number (`175`), never `175px` — jemdoc has a local fix for exactly
   this (see [§2](#2-folder-structure)).

### 8.5 Tables

```
~~~
{Faculty members}{table}{faculty}
*Name* | *Position* | *Research area* | *Contact* ||
Phuong Luu Vo | Associate Professor | Resource allocation | [phuong.luuvo@example.edu] ||
~~~
```

* Cells are separated by `|`; every row **ends** with `||`.
* The third `{...}` value is the table's id — keep it unique on the page.
* jemdoc always emits one empty trailing row; the stylesheet hides it.

### 8.6 No automatic link icons

The minimal theme deliberately has **no** badges in front of links. An earlier version added a
small icon for `mailto:`, `scholar.google.com`, `orcid.org`, `github.com` and `.pdf` links; if
you want them back, look at an earlier revision of the stylesheet
(`git log -p -- www/css/site.css`).

### 8.7 Keeping the prose tidy

* Wrap lines at roughly 100 characters. Long unwrapped lines are hard to review in a diff.
* One blank line between blocks; no trailing whitespace.
* Keep the commented **template** at the bottom of each list-style page up to date when you add
  a new kind of entry.
* Never edit generated files: anything under `_site/`, and
  `www/research/publications.jemdoc`. It says so at the top of the file.

---

## 9. Task recipes

Every recipe ends the same way: **`python build.py`**, then **`python -m pytest`**, then commit
the changed sources. One of those sources — `www/research/publications.jemdoc` — is itself
generated, so it is committed too. The build output in `_site/` never is.

### 9.1 Add a news item

File: `www/home/index.jemdoc` — the `== News` section. Add a line, rebuild, done. Nothing is
generated and nothing is refreshed from anywhere.

One announcement per line, newest first, in exactly this shape:

```
- 05/2025: Dr. Nguyen has been promoted to a Full Professor.
- 06/2026: “A lightweight-to-diffusion framework for semantic image communications” published in ICT Express 2026.
```

* The date comes first — `MM/YYYY`, or just `YYYY` when you do not know the month — then a
  colon, then the sentence.
* The order of the lines is the order on the page. Nothing is sorted for you, so keep the
  newest at the top.
* `--` becomes an em dash, and `*bold*` and `/italic/` work as they do anywhere else in jemdoc.
* `test_home_page_is_the_profile_the_news_and_the_awards` checks that every line starts with a
  date and a colon, so a line that does not fails the suite instead of reaching the site.

Then rebuild:

```bash
python build.py
```

**This used to be generated.** The news was built from the publication list plus a file of your
own announcements in `www/data/news-extra.txt`, on a page of its own. Both were merged into the
Home page at the site owner's request, so there is no `news.html`, no marker block to keep in
sync, and no `make update` step for news: what you write is what appears.

### 9.2 Refresh the publication list

File: `www/research/publications.jemdoc` — **generated. Do not hand-edit it**; the next refresh
overwrites it.

The list is built from the [ORCID record](https://orcid.org/0000-0003-3909-4385), with the full
author list, journal, volume, pages and **publication date** pulled from Crossref for every DOI.
To add a paper:

1. Add it to your ORCID record — that is the single source of truth — or simply wait for
   Crossref to deposit it when the publisher publishes it.
2. Refresh the page and rebuild:

   ```bash
   make update
   ```

   That is a shortcut for `python tools/update_site.py && python build.py`. The script needs no
   arguments; the ORCID iD is the `ORCID_ID` constant at the top of the file. The Publications
   page is the only thing it writes; nothing else on the site is generated.
3. Check the result and commit `www/research/publications.jemdoc` along with your other changes.

What the script does, and what it will not do:

* It writes **one section per kind of work** — `Journal articles`, then `Conference papers`,
  then `Book chapters`, and an `Other work` group if anything is left over — each newest first,
  and every entry begins with its date — `(06/2026)`, or `(2027)` when only the year is known,
  the same shape the news lines use. There are no collapsible years: one column of dates does the
  same job, and nothing has to be opened before a title can be read. After the date come the
  authors (yours in bold), the title, the venue, volume/issue/pages, and a DOI link.
* The section comes from **ORCID's own work type**, so an entry lands in the right place on its
  own and nothing is sorted by hand. A type no section names still reaches the page, in `Other
  work`, so a type ORCID adds one day cannot make a paper vanish from it. The kind of work is
  written on the entry only in that last group: under "Conference papers" a CONFERENCE label on
  every line is noise, because the heading has already said it.
* It drops an arXiv preprint when the same title is already published, so one paper is not
  listed twice.
* **The DOI decides the date, and the most precise date wins.** Crossref carries the publisher's
  own dates; ORCID often holds only a year, or the year the entry was deposited, or January when
  the real month was never recorded. Among the dates Crossref gives, one that knows the month
  beats a bare year — a Springer chapter is dated 2027 because that is the book's year, while
  its `published-online` date is July 2026, and that is the one shown. A record with no DOI, or
  one Crossref has no date for, falls back to the ORCID date.
* It invents nothing: a field Crossref does not supply is simply left out.
* `--no-crossref` skips the per-DOI requests (faster, less detail); `--dry-run` prints both
  pages without writing them; `--delay` sets the pause between requests; `--force` writes a
  list that is much shorter than the one already published.
* Google Scholar is **not** used, and cannot be: it has no public API and blocks automated
  access. ORCID is the machine-readable copy of the same list.

The generated pages are committed, so the site builds with no network. CI refreshes them before
every deploy, so the published list keeps itself up to date. If ORCID or Crossref answers only
partially — a timeout, or a truncated response — the refresh **refuses to write** a much shorter
list than the one already published, and the deployment falls back to the committed copy. A bad
API day therefore cannot empty your publication list; `--force` writes anyway when the shorter
list really is correct.

#### Adding a paper that is not in ORCID

Some things never reach ORCID: a book chapter, a workshop paper, a patent, a journal that does
not deposit DOIs. For those, edit `www/data/publications-extra.bib` and paste the BibTeX straight in:

```bibtex
@inproceedings{vo2027workshop,
  author    = {Vo, Phuong L. and Family, Given},
  title     = {Title of the paper},
  booktitle = {Workshop on Something},
  month     = {jun},
  year      = {2027},
  doi       = {10.0000/example.2027.0001}
}
```

Then run `make update`. The entry is sorted into the right year with everything else, and rendered
in exactly the same style.

* The file opens with a header explaining the rules, a template, and **four real entries** that
  are on your HCMIU page but missing from ORCID. Check those four, and delete any you do not
  want — the file works fine when it is empty.
* Lines starting with `%` are comments, so you can park an entry there until you are ready.
* An entry whose DOI **or title** already appears in ORCID is skipped, so it is safe to paste
  something today and let ORCID pick it up later.
* To take an entry off the site, delete it from the file and re-run.
* `python tools/update_site.py --offline` rebuilds the generated page from that file alone,
  with no network access at all — useful for testing one entry.

### 9.3 Add, remove or move a member

File: `www/lab/lab-members.jemdoc` — the lab's Members page, which is where the people of the group
live. There is no separate Faculty or Students page any more: staff, graduate students,
undergraduate students and alumni are four sections of this one page.

```
- *Full Name* \M PhD, since 2026.\n
  Research: topic in one sentence.\n
  Email: [name@example.edu]
```

* To add: copy an existing three-line bullet, **including the `\n`**, and edit it. Put students
  under `== Graduate students` (PhD and Master) or `== Undergraduate students`, staff in the
  table at the top, and former members under `== Alumni`.
* To remove: delete all three lines.
* Keep the two leading spaces in front of `Research:` and `Email:` — they make the file easy to
  scan.
* When a student leaves, move the bullet to `== Alumni` and rewrite it as one sentence.
* The page ships with placeholder boxes rather than invented names. Delete a box once the
  section has real entries: each box is one `~~~ ... ~~~` block.

### 9.4 Add a course

Files: one page per course. There is no course list page and no course menu.

A course is an ordinary page of the main site, listed in the Teaching group beside Prethesis and
Thesis. Each course is **one page** holding the course information, the slides, the textbook and
any other files — nothing is split up. To add a course:

1. Copy a course page and edit the two values on the first line:

   ```bash
   cp www/teaching/algorithm-optimization.jemdoc www/teaching/ee410.jemdoc
   ```

   ```
   # jemdoc: menu{menu.jemdoc}{ee410.html}, title{EE410}, notime
   = Antenna Theory (EE410)
   Graduate · 3 credits
   ```

2. Give it the sections every course has -- `== Slides`, `== Textbook` -- plus
   `== Course information`, built from the info box the other pages use:

   ```
   ~~~
   {Course information}
   - *Code*: EE410 \M *Level*: Graduate \M *Semester*: Spring 2027 \M *Credits*: 3
   - *When*: Thursday 09:00--11:00, Building B1, Room 302

   *What you will learn:* one or two sentences.
   ~~~
   ```

3. Add it to the Teaching group in `www/menu.jemdoc`, beside the other courses and Thesis:

   ```
    {{Antenna Theory}} (EE410) [ee410.html]
   ```

4. Rebuild. That is the whole job: one page and one menu line, with no list page to keep in step.

**Where the course files live.** Lecture notes, slides, assignments and exam papers go in
`www/pdf/courses/<course>/`, named `lec1.pdf`, `lec2.pdf`, … That folder is an asset folder like
`css/` and `images/`, so `build.py` copies it into the output and mirrors it — a file you delete
from `www/` is deleted from the site as well.

They are here rather than in a repository of their own for one reason: a PDF served from
`raw.githubusercontent.com` **cannot be shown inside a page**. GitHub sends
`X-Frame-Options: deny` on that host, so the browser refuses to display it in a frame, and the
course pages frame their slides.

**Name each place once.** The address of a course's PDFs is one line in the `[materials]`
section of `www/mysite.conf`:

```
[materials]
algorithm-optimization   pdf/courses/algorithm-optimization
regression-analysis      pdf/courses/regression-analysis
blog                     pdf/blogs
```

A page then writes `%%NAME%%` in place of that address, and `build.py` fills it in — so pointing
a course at a new folder, or renaming one, is **one line here** and no page changes. If a page
uses a name that is not in the list, the build stops and tells you which one; it never leaves a
link that quietly goes nowhere. A **new asset folder** also has to be named in `ASSET_DIRS` in
`build.py`, or nothing inside it is published at all.

**The slides are a list of files.** Under `== Slides` a course page is a plain list, one line per
lecture, and clicking one downloads it. It is raw HTML in a `~~~` block:

```
~~~
{}{raw}
<ul>
<li><a href="%%ALGORITHM-OPTIMIZATION%%/lec1.pdf" download>Lecture 1 &ndash; Linear Programming and ILP</a></li>
</ul>
~~~
```

**To add a lecture**, drop `lec11.pdf` in the course's folder and add one line in the same shape.

A strip of buttons over a shared frame was tried here and dropped. A framed PDF hands the reader
the browser's own viewer — its toolbar, its grey surround, and a document fitted to the window
rather than to the text — and these are wanted as files to keep. `download` on the link is what
says so; without it the browser may show the file instead.

`www/teaching/algorithm-optimization.jemdoc` is the working example to copy.

Rules that keep it working:

* A lecture needs **both** a PDF in `www/pdf/courses/<course>/` and a line in the page. A link
  with no file behind it is a 404.
* **Rebuild after adding a file**: `python build.py` copies the PDF into `_site/pdf/`. The
  output is not committed, so an unbuilt change is an unverified change.
* Keep file names lower case with no spaces — `lec1.pdf`, never `Lecture 1.pdf`.

### 9.5 Add an award or a grant

File: `www/research/awards.jemdoc` — one bullet per item:

```
- *2027* \M Description of the award or grant in one sentence.
```

### 9.6 Add a photo to the gallery

1. Put the image in `www/images/` (`gallery-5.jpg`, etc. — lower case, no spaces).
2. In `www/research/gallery.jemdoc`, copy one `<figure>` inside the `<div class="gallery">` block:

   ```
   <figure><img src="images/gallery-5.jpg" alt="Short description" /><figcaption>Caption text.</figcaption></figure>
   ```

3. Rebuild. The grid adapts to any number of photos.

### 9.7 Change the contact details

Two places, and they are the only two:

* `www/home/index.jemdoc` — the **Contact information** section of the Home page: room, email,
  telephone. This is the one visitors look for.
* `www/lab/lab-members.jemdoc` — the contact column of the staff table.

The old Biography page held a third copy; it was merged into Home and deleted, so there is one
less place to keep in step. The prethesis and thesis page (`www/teaching/joining.jemdoc`) tells people
what to send, and links to the Home page rather than repeating the address.

### 9.8 Publish a CV, or any other download

There is **no CV on the site at the moment**, and no `www/files/` folder. The placeholder PDF
that used to sit there has been deleted: nothing linked to it, so it was dead weight. Putting a
real one up takes two steps.

1. Create the folder and drop the document in it:

   ```bash
   mkdir www/files
   ```

   Then save the document as `www/files/cv.pdf`. Keep the name simple — lower case, no spaces.

2. Add the link where you want it. The profile header on `www/home/index.jemdoc` is the natural
   place; it already holds the HCMIU, Google Scholar and ORCID links:

   ```
   <li><a href="files/cv.pdf">Curriculum Vitae</a></li>
   ```

3. Rebuild, and check the link works: `python build.py --serve`.

The same recipe covers any download — a poster, a syllabus, a slide deck. `www/files/` is
copied into the output as `_site/files/`, so `files/your-file.pdf` is the path to link to. The
folder is optional: the build simply skips it while it does not exist.

> Documents that belong to a **course** are different: they live in `www/pdf/courses/`, and the
> course page **frames** them instead of linking to them — see
> [§9.4](#94-add-a-course).

### 9.9 Change the look and feel

File: `www/css/site.css`. It opens with the palette, and those are the values to change:

```css
:root {
  --bg:          #FFFFFF;   /* the page                                     */
  --text:        #000000;   /* body text                                    */
  --accent:      #527BBD;   /* headings, and the marks under them           */
  --link:        #224B8D;   /* links in the text                            */
  --border:      #DDDDDD;   /* hairlines                                    */

  --accent-ink:  #224B8D;   /* links outside body text (same blue)          */
  --muted:       #333333;   /* secondary text                               */
  --faint:       #666666;   /* captions and labels                          */
  --panel:       #F6F6F6;   /* jemdoc's grey: sidebar, code, callouts       */
  --card:        #FFFFFF;   /* card fill                                    */
  --menu-link:   #022B6D;   /* links in the sidebar, a deeper blue          */
  --rule:        #AAAAAA;   /* the rule under a section heading             */
  --rule-strong: #808080;   /* the rule under the page title and a group    */
}
```

**Those last two carry the page.** jemdoc draws a rule under the page title, under every section
heading and under every sidebar group label — the site name and "Research"/"Teaching" alike —
and that is most of what makes its pages look structured rather than plain. Remove them and the
page goes flat, which is exactly what happened once.

**These are jemdoc's own colours**, which is what Duy H. N. Nguyen's site uses: a white page,
black text, `#527BBD` for headings and `#224B8D` for links, with the sidebar, the callout boxes
and the code blocks on jemdoc's grey `#F6F6F6`. Changing the first five re-skins the site; the
rest are derived and rarely need touching.

The fonts come from **Literata**, loaded from Google Fonts in the `[firstbit]` section of
`www/mysite.conf`, with `Georgia` and then `Times New Roman` behind it as fallbacks. That is
`--font-body` and `--font-head` at the top of `www/css/site.css`.

Georgia is jemdoc's own font — and Duy H. N. Nguyen's — but **it has no Vietnamese glyphs**. A
Vietnamese word therefore came out in two typefaces on one line: the browser rendered the plain
letters in Georgia and fetched a second font, per character, for `ệ`, `ậ` and the rest of
Latin Extended Additional. Literata covers Latin and Vietnamese in one typeface and sits close
to Georgia, so the site still reads the way it did. The type sizes follow jemdoc as before: the
page title is `1.65em`, section headings `1.25em`, body text `16px`.

**To change the font**, exactly two places have to agree:

1. the family name in the `fonts.googleapis.com` stylesheet link in `[firstbit]` of
   `www/mysite.conf`;
2. `--font-body` and `--font-head` in `www/css/site.css`.

Keep the local serifs after it in both tokens. If the Google Fonts request is blocked or offline
the page silently falls back to them, and Vietnamese then comes from Times New Roman, which does
have those glyphs. `Noto Serif`, `Lora`, `Literata`, `Source Serif 4` and `Merriweather` all
carry Vietnamese; change the family in those two places and rebuild. Two details in the link are
not decoration: it asks for each weight and style separately, and the ampersand in it is written
as `&amp;`, because a bare `&` is invalid HTML and `test_no_bare_ampersands` rejects it.

> Google Fonts is a request to a third party, and the only one the site makes now that the
> visitor counter is gone ([§6.7](#67-no-visitor-counter)). To drop it, download the two or
> three `.woff2` files you need, put them in `www/css/fonts/` — the build copies `www/css/` as it
> is — replace the stylesheet link with `@font-face` rules of your own, and keep the OFL licence
> file beside them.

Three more jemdoc details are matched on purpose, because they are what the page is built on:

* a **3px rule** under the page title, a **1px `#AAAAAA` rule** under every `h2`, and a
  **1px `#808080` rule** under the site name and every sidebar group label;
* bullets are small **squares**, not round discs (`list-style-type: square`);
* the sidebar cell is a grey box with a hairline border, not a bare column, and it runs the
  **full height of the page** — on a short page as well, because `#tlayout` is made to fill the
  window and the table row stretches with it.

The geometry lives just below: `--menu-width` (245px — wide enough for the longest menu label,
"Algorithm Optimization"), and `--page-width`, which is no longer used — **the layout is full
width**, the way jemdoc and Duy H. N. Nguyen's site are: the grey sidebar sits hard against the
left edge of the window and the text runs to the right edge. To cap the line length on a very
wide screen, add a `max-width` to `td#layout-content` — around `1100px` keeps the text readable —
but that is a departure from jemdoc's own look.

The menu is a **grey sidebar** down the left. Below 760px the two columns stack: the sidebar
becomes a wrapping row above the text, and the profile header puts its portrait on top of the
text.

The site name at the top of the menu and the group labels ("Research", "Teaching") share one
rule, `.menu-category` — in jemdoc they are the same thing, and the name is simply the first of
them. That is why they look identical.

### 9.10 Collapse code blocks

Code blocks are plain, always-visible blocks. To make them collapsible, replace the
`[codeblock]` section of `www/mysite.conf`:

```
[codeblock]
<div class="codeblock">
```

with

```
[codeblock]
<details class="codeblock">
<summary class="blocktitle">BibTeX</summary>
```

and change `[codeblockend]` from `</pre></div></div>` to `</pre></div></details>`. This affects
**all** code blocks on the site. (The publication entries no longer use code blocks at all:
they are generated HTML with a DOI link.)

### 9.11 Placeholder content to replace

The profile data — name, affiliation, contact details, ORCID / Scopus / Google Scholar
identifiers, education, appointments, teaching, grants, awards, the patent, and the full
publication list — has been filled in from the
[ORCID record](https://orcid.org/0000-0003-3909-4385), the
[HCMIU faculty page](https://it.hcmiu.edu.vn/user/vtlphuong/), and the Crossref metadata of each
paper.

What is **still demo content**:

- [x] *Portrait photo* — `www/images/portrait.jpg` is a real photograph now, and
      `www/home/index.jemdoc` points at it.
- [ ] *Gallery photos and captions* — the placeholder illustrations were deleted, so
      `www/research/gallery.jemdoc` has an empty `<div class="gallery">` waiting for real photographs and
      captions. Put the files in `www/images/` and paste a `<figure>` block per photo (the
      template is at the bottom of `www/research/gallery.jemdoc`).
- [ ] *Members* — `www/lab/lab-members.jemdoc` shows one real row (yourself) and no students. The
      former demo names are kept, commented out, at the bottom of that file.
- [ ] *Lab text* — `www/lab/lab.jemdoc`, `www/lab/lab-projects.jemdoc` and `www/lab/lab-news.jemdoc` are
      skeletons. Nothing about the lab that the rest of the site does not already state has
      been filled in.
- [ ] *Research interests* — the list on `www/research/interests.jemdoc` is real, but `layout.md` asks
      for it split into current and past. The file ends with the template for that.
- [ ] *Course detail* — the textbook section on each course page, and the `[materials]` line in
      `www/mysite.conf`, which must name a real repository before the course files open.
- [ ] *News and the blog* — the `== News` list on `www/home/index.jemdoc` carries three real
      publication announcements as examples; replace them with your own, in the shape
      `- MM/YYYY: what happened.` On `www/blog/blog.jemdoc` the single post is a placeholder
      called "First post" — rename the file, the page and its menu line when you write a real
      one, and replace `www/files/blog/first-post.pdf` with the real PDF.
- [ ] *Group name* — choose one: "Network Optimization and Distributed Learning" is used on the
      Home and Research Interests pages; the deleted Faculty page said "Wireless Networks and
      Optimization Group".

Three things were **deliberately left out** because no source could confirm them, rather than
invented:

- *Office hours* — not stated on any page.
- *Teaching history and professional service* — these were sections of the deleted Biography
  page. Teaching now lives in the course sites, which say what is taught and provide the
  material, and the service list was dropped on request; only the verifiable reviewer list
  remains on `www/research/awards.jemdoc`.
- *Talks, group news and new students* — the `== News` list on `www/home/index.jemdoc` carries
  three real publication announcements and nothing else, and `www/lab/lab-news.jemdoc` is an
  empty skeleton for you to fill in.

To find anything left over:

```bash
grep -rn 'example\.edu\|Example \|20XX' www/
```

(`Select-String -Path www/* -Pattern 'example\.edu|Example '` on Windows.)

The **footer** is written by `www/mysite.conf` (`[lastupdated]`) and reads `Last updated:`
followed by the date — no name, no copyright line, and no visitor count
([§6.7](#67-no-visitor-counter)).

It is **pinned to the bottom of the page**. A short page used to stop where its text stopped, so
`Publications` ended with a rule under the date while `Interests` left it floating in the middle
of the window, and the grey sidebar was short on the same pages. `#footer` and
`td#layout-content` in `www/css/site.css` do the work, and they depend on each other: the footer
is positioned against the content cell, so that cell reserves the room for it (its
`padding-bottom`) and a page's own padding cannot be used for that.

That date is **never typed by hand**. The `|` in the section is a placeholder, and jemdoc
replaces it with the date of the build, so every `python build.py` — and every push, because CI
rebuilds the site — refreshes the footer on all 16 pages at once. Editing the date inside a
`_site/*.html` file by hand would be undone by the next build; that folder is generated output,
not a source.

To put a name or a copyright line back, edit that section:

```
[lastupdated]
<p>&copy; Assoc. Prof. Phuong Luu Vo &middot; Last updated: |</p>
```

The `|` is where jemdoc substitutes today's date.

---

### 9.12 Add a blog post

Files: a new page in `www/blog/` and a line for it under the `Blog` heading in
`www/menu-blog.jemdoc` — the blog's own sidebar. Where the PDFs live is one line in
`www/mysite.conf`.

**Blog is a site of its own**, reached from the main menu like the Lab and Teaching: clicking
*Blog* on the main site lands you in the blog, whose sidebar lists the posts and carries a `Home`
back out. Each post is a page of its own, and it is an **ordinary page**: its words are the
page's own markup, so they wrap, search and print like the rest of the site. To add one:

1. Copy an existing post, or start a new file with the right first line:

   ```bash
   cp www/blog/chap1.jemdoc www/blog/second-post.jemdoc
   ```

2. Change the first line so the file name and the title are this post's, and write the post.
   jemdoc's `= Heading`, `== Section`, `- bullet` and `*bold*` all work as they do anywhere else:

   ```
   # jemdoc: menu{menu-blog.jemdoc}{second-post.html}, title{Second post}, notime
   = Second post

   The first paragraph, and then a `== Section` of its own.
   ```

3. Add the post to the blog's own sidebar, `www/menu-blog.jemdoc`, under the `Blog` heading:

   ```
   Blog
    Chapter 1 [chap1.html]
    Second post [second-post.html]
   ```

4. `python build.py`, then look at the page.

**A post written in LaTeX.** The chapters are LaTeX, and the site already loads MathJax, so a
post is written from its own source rather than from a PDF: the prose becomes the page's markup
and every equation is left as LaTeX for MathJax. `tools/latex_to_page.py` does it:

```bash
python tools/latex_to_page.py "www/files/blog/chuong 3 - bai toan toi uu loi.tex" \
    --out www/blog/chap3.jemdoc --post "Bài toán tối ưu lồi"
```

What it handles: `\chapter` and `\section` as headings, `itemize`/`enumerate` as lists, `align`,
`equation`, matrices and cases as mathematics, `figure` with its caption (the image is copied
from `www/files/blog/` into `www/images/blog/`), `tabular` as a table, `lstlisting` as code,
`algorithmic` as pseudocode, and the bibliography with `\cite` and `\ref` turned into the numbers
they point at. It needs nothing but the standard library, and nothing in `build.py` calls it.

Two things to know:

* It is **not a LaTeX engine**: a command it does not know is dropped rather than guessed at.
  Read the page over, and when you fix a word, fix it in the `.tex` and run the tool again — or
  edit the page, and know the next run overwrites it.
* The chapters are long (three to five thousand words each). The tool is what makes them a page
  rather than a PDF; the file it writes is committed and needs no tooling to build.

The PDFs live in `www/pdf/blogs/`, and `%%BLOG%%` in the `[materials]` section of
`www/mysite.conf` says so:

```
blog      pdf/blogs
```

* **Where a PDF lives is not free.** A browser shows a PDF inside a frame only when it comes from
the same site: GitHub sends `X-Frame-Options: deny` with `raw.githubusercontent.com`, so a file
kept there appears as an empty box. That is why the lecture slides and the chapter PDFs live in
`www/pdf/` — an asset folder like `css/` and `images/`, copied into the output and mirrored. A
site served by **GitHub Pages**, e.g. `https://USER.github.io/blog`, would work too.
* `.pdf-frame` in `www/css/site.css` is what makes a framed PDF fill the screen: the width of the
text column, and as much of the height as is left after the page title and the footer. Only the
**course** pages frame a PDF now ([§9.4](#94-add-a-course)); a blog post is its own text.
* `.pdf-frame` in `www/css/site.css` is what makes a framed PDF fill the screen: the width of the
text column, and as much of the height as is left after the page title and the footer. **Nothing
frames a PDF now** -- the courses hand out files ([§9.4](#94-add-a-course)) and the blog is text
([§9.12](#912-add-a-blog-post)) -- but the framing rules are still there, and `#view=FitH` on the
address is what fits a document to the frame's width rather than to the window.
* The frames are `<iframe>`, not `<object>`. An `<object>` works while it is visible from the
  start, but one that a tab strip reveals later never initialises: the PDF of the lecture that
  was showing was not fetched at all, while a hidden one was. An iframe is built to be shown and
  hidden, which is exactly what a tab strip does.
* `pdf/` is named in `ASSET_DIRS` in `build.py`. A new asset folder has to be added there, or the
  build treats it as a folder of pages and never copies it.
* The build stops with a clear message if a page writes a `%%NAME%%` that is not in
  `[materials]`, so a typo is caught rather than shipped as a dead link.

## 10. Testing and validation checklist

Run this before every commit. It takes about a second.

```bash
conda activate vtlp          # environment with the test dependencies
make verify                  # rebuild into _site/ and run every check
```

or, without `make`:

```bash
python build.py
python -m pytest
```

### 10.1 The checklist

- [ ] **Build succeeds with no errors.** `python build.py` prints `pages written : N` with no
      `jemdoc failed` and no warning lines. Any warning names the source line it could not
      parse — almost always a missing blank line or a stray structure character.
- [ ] **Every source produced a page.** The list of `pages written` has one entry per
      `www/*.jemdoc` (except the two menus), i.e. 15 with the current content.
- [ ] **No broken links or images.** Covered automatically by
      `test_every_local_link_and_image_resolves`, which checks every relative `href`/`src`
      against the files on disk. This is what catches a moved asset or a menu entry pointing at
      a renamed page.
- [ ] **The menu is consistent.** Covered by `test_every_page_has_the_same_menu` and
      `test_the_current_menu_item_is_highlighted`. The second one fails if a page's
      `menu{menu.jemdoc}{...}` second value does not match its own file name.
- [ ] **HTML is valid.** `test_no_bare_ampersands` and
      `test_html_parses_without_serious_errors` (html5lib, obsolete `align=...` attributes
      excepted). A bare `&` is the usual failure — write `&amp;`.
- [ ] **MathJax renders.** Load `http://localhost:8000/mathjax-test.html` in the preview and
      confirm the three expressions are typeset. Automated equivalents:
      `test_mathjax_is_loaded_on_every_page` and
      `test_mathjax_test_page_has_inline_and_display_equations`.
- [ ] **Line endings are LF.** `test_generated_html_uses_lf_line_endings` — no CRLF, no BOM.
- [ ] **The publication list is valid.** `test_publications_are_grouped_by_year_newest_first`,
      `test_every_publication_links_to_its_doi` and
      `test_publication_year_summaries_agree_with_their_entries`.
- [ ] **Visual check** of the pages you touched: `python build.py --serve`, then look at the
      changed pages at both a wide and a narrow window.
- [ ] **Assets exist** in the output: `.nojekyll`, `css/site.css`,
      `images/portrait.jpg` (covered by `test_static_assets_are_copied`).
- [ ] **Nothing stale is left over.** If you deleted a file, the build says so under
      `stale removed`, and `test_a_file_deleted_from_www_disappears_from_the_output` guards it.
- [ ] **Commit sources only.** `_site/` is generated and ignored — never commit it. The
      published site is rebuilt from `www/` by GitHub Actions, so there is no second copy to
      keep in step.

Full run, for reference:

```console
$ python build.py
Build finished.
  output folder : D:\Code\phuongluuvo.github.io\_site
  pages written : 16
  ...
  assets copied : css/, images/

$ python -m pytest
.................................................                         [100%]
49 passed in 1.80s
```

(The exact number grows as checks are added; what matters is that nothing fails.)

### 10.2 What the test-suite covers

Every `.jemdoc` source produced its `.html` page · as many different menus are rendered as there
are `menu*.jemdoc` files, and pages sharing a menu render it identically · every menu starts
with the site name pointing home · each page highlights its own menu entry, and only that one ·
the lab pages show the lab sidebar and the course pages show the course sidebar, neither of them
leaking the main menu · a blog chapter is a page of text and not a PDF in a frame · no broken relative links/images · only external links open a new tab ·
no unescaped `&` · no HTML5 parse errors · every page is valid UTF-8 and non-ASCII text survives
the build · every page has a `<title>`, an `<h1>`, the stylesheet and a footer · MathJax loaded
everywhere · no page counts visitors, and the footer is the date and nothing else ·
**every SVG image is valid XML**, because a malformed one renders as nothing at all · no copied asset is empty · a file deleted from `www/`
disappears from the output on the next build · the generated
`.jemdoc` file says that it is generated · the GitHub Actions workflow is valid YAML and only
ever runs the generator in a way that cannot break the deployment · the generated page is
tracked by git · sources are normalised CRLF → LF.

Another group covers the **generated page** and the Home page: the publications are one section
per kind of work — journal articles, then conference papers, then book chapters — each
newest-first with the date leading every entry, extra paper links can be added from BibTeX, and
`tools/update_site.py` groups them by ORCID's own work type without dropping one it does not
name, runs end to end with no network access and does **not** still write a news page. The Home
page is checked as the whole front page: the profile header, its sections, and every news line
keeping its `MM/YYYY:` shape. The blog posts are checked as text rather than as pictures: real
prose, LaTeX mathematics left for MathJax, and every figure published with its caption.

The tests **build the site into a temporary folder**, so running them never disturbs your
working tree.

---

## 11. Deployment

The site is published with **GitHub Pages**, and **GitHub Actions builds and deploys it**.
Nothing generated is committed, so the published site always comes from the sources in `www/`.

### How it works

`.github/workflows/pages.yml` runs on every push to `main`, on a clean Ubuntu machine:

1. `python tools/update_site.py` — *best effort*: refresh the two generated pages from ORCID.
   If it fails, or refuses to write a suspiciously short list, the **committed copies are used**
   and the deployment carries on. This is why a bad API day cannot empty the site.
2. `python build.py --out _site` — rebuild every page from source
3. upload `_site/` as the Pages artifact
4. deploy that artifact to GitHub Pages

A second, **non-blocking** job (`Rebuild and test`) installs the test dependencies and runs
`python -m pytest`, so a broken link or a missing page shows up in the run summary without
stopping the deployment. To make a failing test block deployment, add `needs: [build, test]`
to the `deploy` job.

Watch runs under the **Actions** tab; a run can also be started by hand with **Run workflow**.

### One-time setup (required)

Repository → **Settings** → **Pages** → **Build and deployment** → **Source** →
**GitHub Actions**.

> **This is not optional.** The generated HTML is not committed, so if the Pages source is still
> set to "Deploy from a branch", GitHub looks for `index.html` in the repository root, finds only
> sources, and serves **404 for every page** — "There isn't a GitHub Pages site here" or a plain
> "does not contain the requested file", including for the home page. The repository looks
> correct and the Actions run is green, which is what makes it confusing: the build and the
> deployment both succeed, there is simply no HTML in the branch for *branch* mode to publish.
> Set the source to **GitHub Actions** once, then push.

### Deploying from a branch instead

If you would rather have GitHub serve committed files, with no CI involved, build into a folder
that Pages can publish and stop ignoring it:

```bash
python build.py --out docs
```

Then remove the `/docs/` and the anchored `/*.html`, `/css/`, `/files/`, `/images/`,
`/.nojekyll` lines from `.gitignore`, commit `docs/`, and set **Settings** → **Pages** →
**Source** → `Deploy from a branch`, branch `main`, folder `/docs`. Also delete or disable
`.github/workflows/pages.yml`, otherwise both mechanisms deploy and it becomes unclear which
version is live. Everything else in this guide still applies; only the location of the output
changes.

### The site address

The site is served at **<https://phuongluuvo.github.io>**, an address GitHub derives from the
repository name. There is **no custom domain configured and no `CNAME` file** in the
repository: `build.py` does not copy one and the test-suite does not expect one. Nothing in
`www/` controls the address.

* **To change it**, use **Settings** → **General** → **Rename** on the repository. Note that
  this repository is a *user site* (`<username>.github.io`), so renaming it produces
  `phuongluuvo.github.io/<new-name>` rather than another clean name. Leaving it alone is
  usually the right answer.
* **To add a custom domain later**, that is a GitHub setting, not a file you commit: point the
  domain's DNS at GitHub Pages — four `A` records (`185.199.108.153`, `185.199.109.153`,
  `185.199.110.153`, `185.199.111.153`) for an apex domain, or one `CNAME` record for a `www`
  subdomain pointing at `phuongluuvo.github.io` — then **Settings** → **Pages** →
  **Custom domain**, type it, **Save**, and enable **Enforce HTTPS** once the certificate is
  issued. Because this site deploys from a build artifact, the setting is what counts; you do
  not add the domain to `www/` or commit a `CNAME` file yourself.
* **To stop using a domain**, clear the field on the same settings page.

---

## 12. Troubleshooting

**"Nothing changed on the website."**
You edited a `.jemdoc` file but did not rebuild, or you built but did not commit/push. Run
`python build.py`, check with `python build.py --serve`, then `git add -A && git commit && git push`.

**"Two paragraphs merged into one."**
No blank line between them, or a comment line directly under a paragraph. Comments need a blank
line above them.

**"My text after a `#` disappeared."**
`#` starts a comment. Write `\#` for a literal hash.

**"Italics appeared out of nowhere / my slash vanished."**
Two `/` on one line make italics. Write `\/` for a literal slash when another `/` is on the
same line.

**"A line of my text vanished, or became a bullet."**
Lines starting with `-`, `.`, `:`, `=` or `~` are list items, headings or blocks. Never begin a
normal sentence with those characters.

**"The build fails with `jemdoc failed`."**
Read the line above it — jemdoc reports the source line it could not parse. Usually a missing
blank line, an unterminated `~~~` block, or a stray structure character.

**"A whole paragraph was swallowed into the previous one."**
Almost always CRLF line endings in a source file. `.gitattributes` forces LF for `*.jemdoc`,
so re-checkout the file (`git rm --cached <file>` then `git checkout <file>`) or save it again
with LF endings.

**"The site looks unstyled / the CSS is missing."**
The stylesheet is `www/css/site.css` and is copied into `_site/css/` on build. Rebuild, and
force-reload the browser (<kbd>Ctrl</kbd>+<kbd>F5</kbd>).

**"I changed a page and the change vanished / the site went back to how it was."**
You edited the output instead of the source. `_site/` is regenerated from `www/` on every build,
so an edit there lasts only until the next `python build.py`, `git push` or CI run. Make the
change in the matching `www/` file — the warning in §6.1 lists which one — and rebuild. If the
work is already gone, VS Code's Timeline (right-click the file, **Local History**) still holds
the earlier versions.

**"An image is missing — just a broken-image icon."**
Two causes, and neither one stops the build or reports an error. Either the name in the page does
not match a file in `www/images/` — check the extension, and check the path is relative to the
site root (`images/portrait.jpg`, never `www/images/...` and never a Windows-style
`images\portrait.jpg`) — or the image is an SVG with a **double hyphen inside an XML comment**,
which is illegal in XML: the note at the top of the old placeholder portrait contained one and the
portrait silently disappeared. Rewrite `--` as a single `-`, or delete the comment.
`test_every_local_link_and_image_resolves` catches the first and `test_the_images_are_valid` the
second.

**"Where do I put a PDF or a PNG?"**
On a page: `www/images/`, linked as `images/your-file.png`. For visitors to download:
`www/files/`, linked as `files/your-file.pdf` — create the folder if it is not there. For a
course: neither, because course material lives in a separate repository and is linked by URL.
There is a table with the three cases in [§2](#2-folder-structure).

**"I deleted an image or a PDF but it is still in `_site/`."**
Rebuild. `python build.py` mirrors `www/css/`, `www/images/` and `www/files/`: a file removed
from `www/` is removed from the output on the next build, and printed under `stale removed`.
Before that fix the build only ever *added* files, which is why old PNGs and PDFs used to pile
up in the output folder. If you are looking at the live site instead, the old file disappears
when CI next runs.

**"There used to be `.html` files in the repository root. Where did they go?"**
They are generated output and now live in `_site/`, which is gitignored. That keeps the
repository to sources, tooling and documentation. Build first, then look in `_site/` — see
[§2](#2-folder-structure).

**"I edited a stylesheet or `.html` file and my change disappeared."**
You edited generated output. There is exactly one stylesheet, `www/css/site.css`, and one
source per page, `www/<name>.jemdoc`. Everything under `_site/` is rebuilt from those on every
`python build.py`.

**"The menu does not highlight the current page."**
The second value in that page's `menu{menu.jemdoc}{...}` does not match its own file name.

**"I deleted a page but the menu still links to it."**
Remove its line from `www/menu.jemdoc` too. `test_every_local_link_and_image_resolves` fails
until you do.

**"Equations show up as raw LaTeX."**
MathJax comes from a public CDN, so internet access is required. Also check that
`www/mysite.conf` still contains the `MathJax-script` line, and open
`http://localhost:8000/mathjax-test.html`.

**"`python build.py` says `error: .../tools/jemdoc not found`."**
You are not in the repository root. `cd` to the folder that contains `build.py`.

**"`python -m pytest` says `No module named pytest`."**
The test dependencies are not installed in the interpreter you are using. Run
`conda activate vtlp`, or install `requirements.txt` into the environment you are using. A
fresh `python -m venv .venv` has none of them until you do.
`build.py` never needs them — only the tests do.

**"The build works but `python -m pytest` fails."**
The tests say exactly what is wrong (broken link, missing page, missing menu entry, an equation
that stopped rendering, a bare `&`). Fix the source, not the test. If a test itself is wrong,
it lives in `tests/test_site.py`.

**"A test passes on my PC but fails in CI."**
Three causes, in order of likelihood. (1) A file exists locally but is **not committed**: CI
checks out a clean copy, so anything untracked is simply absent. `git ls-files` lists every
file git knows about — if what you need is not in that list, CI does not have it. (2) **Case**:
Windows and macOS ignore it, git and Linux do not, so `Guide.md` and `guide.md` are two
different files to CI. (3) The **locale** — see the next entry.

**"Curly quotes, dashes or accents come out as `â€œ`, `Ã—` or `?`."**
jemdoc writes its HTML with the platform default encoding, which is cp1252 on Windows, so
non-ASCII characters become single bytes that are not valid UTF-8. Linux (and therefore CI) is
unaffected, so this is a bug you only see locally. `build.py` prevents it by running jemdoc
with `PYTHONUTF8=1` in its environment — do not remove that line from `run_jemdoc`. If a
character is still wrong, check that the *source* file is saved as UTF-8, without a BOM.

**"`tools/update_site.py` printed `error: only N entries this time` and wrote nothing."**
That is the guard working, not a crash: ORCID or Crossref answered with far fewer papers than
are already published, so the script refused to overwrite the page. Nothing changed and the
site keeps the committed list. Try again later, or re-run with `--force` if the shorter list
really is correct.

**"CI printed `Could not refresh the generated pages; using the committed copies.`"**
Expected and harmless. That step is deliberately best effort, so a network blip or a partial
API response cannot block a deployment — the build then uses the committed
`www/research/publications.jemdoc`. Run `make update` locally when you want it
refreshed, and commit the result.

**"The news on the Home page is out of date."**
Nothing refreshes it but you: it is a hand-written list in the `== News` section of
`www/home/index.jemdoc`. Edit the lines there and run `python build.py`. It used to be generated
from the publication list and a `www/data/news-extra.txt` file; both are gone.

**"How do I read a failed CI run?"**
**Actions** → the run → the job → the failed step. The last lines name the test and the problem.
Reproduce it locally with `python build.py && python -m pytest` (or `make verify`), fix the
source, and push again. A red **Rebuild and test** job does not stop the deployment, because it
is the second, non-blocking job — but it always means something is genuinely wrong.

**"I broke `www/research/publications.jemdoc`."**
It is committed, so git can restore it: `git checkout -- www/research/publications.jemdoc`, or
simply re-run `python tools/update_site.py`. There is no way to break it permanently, which is
exactly why the generated file is committed rather than ignored.

**"Everything looks fine locally but the deployed site is old."**
Check the **Actions** tab — the workflow may have failed. Also confirm that **Settings** →
**Pages** → **Source** is set to **GitHub Actions**: the generated HTML is no longer committed,
so a branch-based source would serve stale files. GitHub Pages also caches for a few minutes.

---

## 13. Notes for AI coding agents

Read this before making any change.

### 13.1 Hard rules

1. **Never hand-edit generated files.** `build.py` writes the whole site into `_site/`, which
   is gitignored and rebuilt from scratch every time:
   * `_site/*.html` (one per page), `_site/css/site.css`, `_site/images/*`, `_site/.nojekyll`.

   Their sources are, respectively: `www/*.jemdoc`, `www/css/site.css` and
   `www/images/`. `www/` is the only place to edit — with one exception:
   `www/research/publications.jemdoc` is generated by `tools/update_site.py`. Never edit it by
   hand. To change what it contains, edit your ORCID record or paste BibTeX into
   `www/data/publications-extra.bib`, and run `make update`. The news is **not** generated: it
   is a hand-written list on the Home page.
2. **Always rebuild after a source change:** `python build.py`. The deployed site is built from
   `www/` by CI, so an unpushed change is simply not live; but a change you never build is a
   change you never verified.
3. **Commit sources only.** `_site/` is generated and ignored — never add generated output to
   git. There is deliberately no second copy of the site to keep in step by hand.
4. **Never add or remove a page without updating `www/menu.jemdoc`.** A menu entry pointing at
   a non-existent page fails `test_every_local_link_and_image_resolves`.
5. **The page's `menu{menu.jemdoc}{X.html}` second argument must equal that page's own `.html`
   file name**, otherwise `test_the_current_menu_item_is_highlighted` fails. Note the matching
   rule in jemdoc: it marks a menu entry current with a **suffix test**
   (`link[-len(current):] == current`), so one page name must never be the tail of another.
   That is why the lab's news page is `lab-news.html` rather than `news.html`: a page called
   `news.html` would light up whenever you were on `lab-news.html`. Call every page by a name no
   other page ends with.
6. **MathJax is configured in exactly one place:** the `[firstbit]` section of
   `www/mysite.conf`. Never add a MathJax `<script>` tag to a page, and never add a second
   configuration block. A duplicated include is a bug, not a feature.
7. **Keep `build.py` dependency-free.** It must run on a stock Python 3.9+ using only the
   standard library. Extra packages belong in the test requirements only.
8. **Do not rename files to a different case.** Windows and macOS would accept it, git and
   GitHub Pages would not. New files: lower case, hyphen-separated, ASCII.
9. **Do not touch `tools/jemdoc` casually.** It is vendored upstream jemdoc + MathJax 0.7.3
   with **five** local fixes marked by a `LOCAL FIX` comment, listed in
   [§2](#2-folder-structure). If you modify it, keep every `LOCAL FIX` intact and say so
   explicitly.
10. **Keep generated output out of the repository.** `_site/` and `/docs/` are ignored on
    purpose, as are the anchored root patterns (`/*.html`, `/css/`, `/files/`, `/images/`,
    `/.nojekyll`) that block the old layout. Do not commit generated pages and do not remove
    those rules.

### 13.2 Where things live (quick map)

| Need to change… | Edit |
| --- | --- |
| a page's content | `www/<name>.jemdoc` |
| the sidebar of the main site | `www/menu.jemdoc` |
| the sidebar inside the Edge AI Lab | `www/menu-lab.jemdoc` |
| the sidebar inside the blog | `www/menu-blog.jemdoc` |
| `<head>`, MathJax config, `<title>` suffix, footer, favicon | `www/mysite.conf` (`[firstbit]`, `[windowtitle]`, `[lastupdated]`) |
| colours / fonts / layout | `www/css/site.css` (the palette is the first block) |
| the publication list | `tools/update_site.py` (the ORCID iD is at the top) |
| which pages exist | `build.py` (it treats any `menu*.jemdoc` as a menu, not a page) |
| the checks | `tests/test_site.py` |
| CI / deployment | `.github/workflows/pages.yml` |
| line-ending policy | `.gitattributes` |
| ignored files | `.gitignore` |

### 13.3 How to verify a change did not break other pages

The generated pages share the menu, the `<head>` and the stylesheet, so a change to
`www/menu.jemdoc`, `www/menu-lab.jemdoc`, `www/menu-blog.jemdoc`, `www/mysite.conf` or
`www/css/site.css` affects
**every page at once**.
`python build.py` alone does not prove anything; always run both steps:

```bash
python build.py --out _site
python -m pytest              # needs the vtlp env / test dependencies
```

Then read the result against what you changed:

| Test | Fails when |
| --- | --- |
| `test_build_produces_every_page` | a `.jemdoc` was not generated (bad name/location) |
| `test_every_page_has_the_same_menu` | the menu markup diverged between pages |
| `test_the_current_menu_item_is_highlighted` | a page's `menu{...}{X.html}` no longer matches its name, or a non-menu page highlights something |
| `test_every_local_link_and_image_resolves` | a link, image, stylesheet or asset points at something that does not exist |
| `test_no_bare_ampersands` | prose contains a raw `&` |
| `test_html_parses_without_serious_errors` | malformed HTML, e.g. a broken `<div>` in `mysite.conf` |
| `test_every_page_has_a_title_and_the_stylesheet` | `[windowtitle]`, `[defaultcss]` or the `<h1>` markup broke |
| `test_mathjax_is_loaded_on_every_page` | the MathJax include was dropped or moved out of `[firstbit]` |
| `test_publications_are_grouped_by_year_newest_first`, `test_every_publication_links_to_its_doi`, `test_publication_year_summaries_agree_with_their_entries` | the generated publication list is malformed, or `www/research/publications.jemdoc` has been hand-edited |
| `test_generated_html_uses_lf_line_endings`, `test_build_normalizes_crlf_line_endings`, `test_every_source_page_is_staged_with_lf` | CRLF line endings or a BOM crept in |
| `test_github_actions_workflow_is_valid_yaml` | `.github/workflows/*.yml` is no longer valid YAML |

`git diff` will **not** show the effect of your change on the generated pages, because the
output is not committed. If you cannot run pytest (no dependencies available), build and then
search the output instead:

```bash
python build.py
grep -l 'Your new menu label' _site/*.html      # expect all 15 pages
```

On Windows, `Select-String -Path _site/*.html -Pattern 'Your new menu label'` does the same.

### 13.4 Explicit don'ts

* Do not "tidy" the tree by moving `www/` to `src/`, or by moving `menu.jemdoc` or
  `mysite.conf` out of `www/`. jemdoc is run inside a single staging directory and resolves
  every relative path from the site root; the current layout is what makes that work, and
  `build.py`, `tests/test_site.py`, `.gitattributes`, `.gitignore`, the workflow and this guide
  all encode the current paths.
* Do not reformat the CRLF → LF normalisation in `build.py`; it exists because jemdoc is
  line-ending sensitive.
* Do not switch `.jemdoc` files to CRLF.
* Do not hand-write HTML into a page where jemdoc syntax exists. Raw HTML is reserved for the
  gallery `<figure>` blocks, the `<details class="materials">` dropdowns on the Courses page,
  and the `<head>` in `mysite.conf`.
* Do not mass-rewrite pages to "improve" style. Content changes belong to the site owner.

---

## 14. Where to learn more

* jemdoc syntax reference: <http://jemdoc.jaboc.net/using.html>
* jemdoc example page (a live cheat sheet): <http://jemdoc.jaboc.net/example.html>
* MathJax supported LaTeX commands:
  <https://docs.mathjax.org/en/latest/input/tex/macros/index.html>
* GitHub Pages documentation: <https://docs.github.com/en/pages>
* jemdoc+MathJax upstream (the source of `tools/jemdoc`):
  <https://github.com/wsshin/jemdoc_mathjax>

### Licence and credits

* The **website content** is © Assoc. Prof. Phuong Luu Vo. All rights reserved.
* `tools/jemdoc` is **jemdoc + MathJax** by Jacob Mattingley and Wonseok Shin, distributed
  under the **GNU GPL v3**; its original README is kept at `tools/README-jemdoc.md`. The five
  patches applied to it are listed in [§2](#2-folder-structure).
* **MathJax** is loaded from the jsDelivr CDN and is licensed under Apache-2.0.
* Everything else was written for this site: the pages in `www/`, `www/css/site.css`,
  `build.py`, `tools/update_site.py` and `tests/test_site.py`.

### Where documentation belongs

There are exactly two documents, and each has one job, so that nothing has to be kept in step
by hand:

| File | Audience | Contains |
| --- | --- | --- |
| `guide.md` | the site owner, contributors, agents | **all** operational material: build, edit, publish, troubleshoot, conventions, the vendored patches, licence |
| `AGENTS.md` | AI coding agents | the hard rules only — it is auto-loaded by the editor, so it stays short |

When you add something, put it in the file whose job it is and **link** to it from the other
rather than copying it.
