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
| **`tools/update_site.py`** | Regenerates the two generated pages. `www/publications.jemdoc` comes from the ORCID record, with the full author list, volume, pages and DOI from Crossref; `www/news.jemdoc` and the "Latest news" block on the Home page come from that same list plus `www/news-extra.txt`. Anything ORCID does not have yet goes into `www/publications-extra.bib`. Run `make update` when you publish something. |
| **`tests/test_site.py`** | The automated checks on the *generated* site: no broken links, identical menu on every page, valid HTML and UTF-8, MathJax present, a well-formed publication list, and a news page that covers every publication. |

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
│   ├── menu.jemdoc              the navigation menu, shared by every page
│   ├── index.jemdoc             Home                   ─┐
│   ├── biography.jemdoc         Biography               │
│   ├── news.jemdoc              News (GENERATED)        │
│   ├── faculty.jemdoc           Faculty                 │
│   ├── students.jemdoc          PhD / Master students   ├─ one file = one page
│   ├── joining.jemdoc           For Students            │
│   ├── gallery.jemdoc           Gallery                 │
│   ├── publications.jemdoc      Publications (GENERATED)│
│   ├── awards.jemdoc            Awards & Grants         │
│   ├── courses.jemdoc           Courses                 │
│   └── mathjax-test.jemdoc      MathJax check page      ─┘
│   ├── publications-extra.bib   BibTeX you add by hand (see §9.2)
│   ├── news-extra.txt           your own announcements (see §9.1)
│   ├── css/site.css             the stylesheet source
│   ├── files/                   files visitors download ┐ copied into the output
│   └── images/                  portrait, gallery photos ┘ on every build
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
│   ├── update_site.py           regenerates www/publications.jemdoc and www/news.jemdoc
│   ├── make_placeholder_pdfs.py regenerates the dummy CV in www/files/
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
| `www/` | All hand-edited sources: pages, menu, control file, stylesheet, and assets. |
| `www/files/` | Files visitors download (currently the CV). Copied into the output on build. |
| `www/images/` | Images (`portrait.svg`, `gallery-*.svg`). Copied into the output on build. |
| `tools/` | Vendored third-party tools. Only touched when updating jemdoc itself. |
| `tests/` | Automated checks. Run them before every commit. |
| `.github/workflows/` | GitHub Actions: build, deploy, test. |
| `_site/` | **Generated.** The entire website — HTML, CSS, images, `.nojekyll`. Ignored by git; it exists only after a build. |

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
  pages written : 11
                  awards.html
                  biography.html
                  ...
  assets copied : css/, files/, images/
```

If `pages written` does not match the number of `.jemdoc` files in `www/` (11 at the time of
writing), or a page is missing from the list, a source file was not picked up — check that it
is directly inside `www/` and ends in `.jemdoc`.

### What the build actually does

1. Collects every `www/*.jemdoc` except `menu.jemdoc`.
2. Copies the sources **and** `www/mysite.conf` into a temporary staging folder, converting
   CRLF to LF on the way. This matters: jemdoc decides where a paragraph ends by looking for a
   blank line, and a Windows CRLF blank line is not blank to jemdoc, so content silently
   merges. Keeping the sources at LF (`www/` is safe via `.gitattributes`) plus this
   normalisation makes the build identical on Windows, macOS, Linux and CI.
3. Runs `tools/jemdoc -c mysite.conf <pages>` inside the staging folder. Relative paths inside
   a page (`css/site.css`, `images/portrait.svg`) therefore resolve from the **site root**.
4. Copies the generated `*.html` into the output folder (`_site/` unless `--out` says
   otherwise).
5. Copies `www/css/`, `www/files/`, `www/images/`, and writes the `.nojekyll` marker.
6. Deletes pages from the output folder that an earlier build wrote but that no longer have a
   source, so that removing a page cannot leave a stale one behind.

Nothing else is touched.

### Command reference

| What you want | Command |
| --- | --- |
| Rebuild the whole site into `_site/` (normal case) | `python build.py` |
| Build and preview in a browser | `python build.py --serve` |
| Build into a different folder | `python build.py --out docs` |
| Delete the generated `*.html` files | `python build.py --clean` |
| Rebuild **and** run every check | `make verify` |
| Run only the checks | `python -m pytest` |
| Refresh the generated pages (Publications and News) from ORCID | `make update` |
| Regenerate the placeholder CV in `www/files/` | `python tools/make_placeholder_pdfs.py` |

`make` wrappers: `make` = `python build.py`, `make site` = the same (an alias),
`make serve` = `--serve`, `make clean` = `--clean`, `make test` = `pytest`,
`make verify` = build to `_site/` + `pytest`, `make update` = refresh the generated pages from
ORCID + build. `make publications` and `make news` are both aliases of `make update`, because
one run produces both pages.

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
| The navigation menu (on every page) | `www/menu.jemdoc` |
| Colours, fonts, spacing, page width, badges | `www/css/site.css` |
| The MathJax setup, the `<head>`, the page-title suffix, the footer | `www/mysite.conf` |
| Home page (welcome text, contact, quick links; the marked news block is generated) | `www/index.jemdoc` |
| Biography: contact, profiles, interests, education, positions, service | `www/biography.jemdoc` |
| News and announcements | `www/news-extra.txt`, then `make update` — `www/news.jemdoc` is **generated**, see [§9.1](#91-add-a-news-item) |
| Faculty in the group | `www/faculty.jemdoc` |
| PhD / Master students | `www/students.jemdoc` |
| For Students (prethesis, thesis, internship) | `www/joining.jemdoc` |
| Photo gallery | `www/gallery.jemdoc` + files in `www/images/` |
| Publications | `www/publications.jemdoc` — **generated**, see [§9.2](#92-refresh-the-publication-list) |
| A paper that ORCID does not have yet | paste BibTeX into `www/publications-extra.bib`, then `make update` |
| Awards and grants | `www/awards.jemdoc` |
| Courses and their material links | `www/courses.jemdoc` |
| The CV that visitors download | replace `www/files/cv.pdf` |
| The portrait photo on the Home page | replace `www/images/portrait.svg` |
| The MathJax check page | `www/mathjax-test.jemdoc` |

### 6.2 The first line of every page

Every page starts with a jemdoc control comment:

```
# jemdoc: menu{menu.jemdoc}{news.html}, title{News}, notime
= News
News and announcements
```

* `menu{menu.jemdoc}{news.html}` — the first value is the shared menu file, the **second must
  be the page's own `.html` name**. That is what makes the menu entry highlight itself. If it
  does not match, nothing is highlighted (and the test-suite will tell you).
* `title{...}` — used for the browser tab and the page heading, unless a `= Heading` follows.
* `notime` — omits the time of day from the "last updated" footer; keep it so dates stay
  `YYYY-MM-DD`.
* `= Page title` — the big `<h1>`. The **next line** becomes the grey subtitle.

### 6.3 Adding a new page

1. Copy an existing page:

   ```bash
   cp www/news.jemdoc www/seminars.jemdoc
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

### 6.4 The shared menu

`www/menu.jemdoc` is the menu for **every** page — there is exactly one copy of it.

```
Home
 Biography [biography.html]
 News [news.html]
Research Group
 Faculty [faculty.html]
 {{PhD / Master students}} [students.html]
 {{For Students}} [joining.html]
 ...
```

* A line **without** brackets is a grey category heading (`Research Group`).
* A line **with** brackets is a link: ` Visible text [target-file.html]`.
* The order in this file is the order on every page.
* Wrap a long label in `{{double braces}}` to stop jemdoc forcing it onto one line.
* **One page name must never be the tail of another.** jemdoc marks a menu entry current with
  a suffix test (`link[-len(current):] == current` in `tools/jemdoc`), so `for-students.html`
  would light up on `students.html` too. That is why the For Students page is
  `www/joining.jemdoc`.
* `index.html` and `mathjax-test.html` are deliberately **not** menu entries. The `Home`
  category has no page of its own: the page heading at the top of every page is the link back
  to the Home page.

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
| `[firstbit]` | Everything from `<!DOCTYPE html>` to the MathJax `<script>` — the whole `<head>`. |
| `[defaultcss]` | The stylesheet link (`css/site.css`). |
| `[doctitle]` | The `<h1>` markup (currently a link back to the home page). |
| `[windowtitle]` | The browser-tab title, `Page name · Phuong Luu Vo`. |
| `[lastupdated]` | The footer line. |

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

* **Lower case, hyphen-separated, ASCII only**: `students.jemdoc`, `mathjax-test.jemdoc`,
  `lecture-01.pdf`. Never use spaces, never mix case, never use accents.
* Pages are always `.jemdoc`; the generated name is the same word with `.html`
  (`students.jemdoc` → `students.html`). **The two names must correspond** — links and
  the menu refer to the `.html` name, the menu's own entry must match it, and `build.py`
  derives one from the other.
* Assets follow the same rule: `gallery-1.svg`, `lecture-01.pdf`, `portrait.svg`.
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
| `[biography.html Biography]` | a link to a page of this site |
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
* Reference them **relative to the site root**: `images/portrait.svg`, not `www/images/...`.
* The full path is what the visitor's browser downloads, and `build.py` copies `www/images/` to
  `images/`.
* Always write a meaningful `alt` text.
* A plain image in a paragraph: `{}{img_left}{images/portrait.svg}{Alt text}{175}{}{}` — the
  seven fields are `{title}{img_left}{file}{alt}{width}{height}{link}`. Leave the width blank
  to use the image's natural size.
* Gallery photos use raw HTML inside a `<div class="gallery">` block in
  `www/gallery.jemdoc`; the grid rearranges itself for any number of photos. See
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
* Never edit generated files: anything under `_site/`, `www/publications.jemdoc` and
  `www/news.jemdoc`. Both say so at the top of the file.

---

## 9. Task recipes

Every recipe ends the same way: **`python build.py`**, then **`python -m pytest`**, then commit
the changed sources. Two of those sources — `www/publications.jemdoc` and `www/news.jemdoc` —
are themselves generated, so they are committed too. The build output in `_site/` never is.

### 9.1 Add a news item

File: `www/news-extra.txt` — then run `make update`.

The News page is **generated** from two sources:

1. **Your publications.** Every entry on the Publications page becomes an announcement on its
   own, so a paper that arrives through ORCID, or that you paste into
   `www/publications-extra.bib`, appears in the news with nothing for you to write.
2. **`www/news-extra.txt`**, for everything that is not a paper: grants, talks, awards, new
   students. One announcement per line:

   ```
   2026-10-01 | Three new papers accepted at [IEEE ICC 2026](https://icc2026.ieee-icc.org/).
   2026-06-15 | Invited talk at the Vietnam School of Information Theory.
   2025 | An announcement where you only know the year.
   ```

   * The date comes first — `YYYY-MM-DD`, `YYYY-MM`, or just `YYYY` — then a vertical bar, then
     the text. Lines are sorted automatically, so the order of the lines does not matter.
   * `[a label](https://link)` becomes a link. Everything else is plain text.
   * Lines starting with `#` are comments. The file ships with only commented-out examples,
     and `test_news_extra_ships_with_every_line_commented_out` keeps it that way.
   * This file is never published; it stays on your computer.

Then rebuild:

```bash
make update
```

That is a shortcut for `python tools/update_site.py && python build.py`. It rewrites
`www/news.jemdoc`, the "Latest news" block on the Home page, and the Publications page. It is
safe to run as often as you like: a page whose content has not changed is not rewritten at all.

How the page is laid out:

* Announcements are grouped by year, newest first.
* The **two most recent years are shown open**. Every older year is collapsed behind a
  click-to-open row that says how many announcements it holds.
* Each announcement shows its date (`2026-06`, or `2026-06-01` when the day is known), a short
  sentence, and a `doi` link where there is one.
* The Home page repeats the **four newest** announcements, in a block that lives in
  `www/index.jemdoc` between two `GENERATED latest-news` comment markers. Delete both markers
  if you would rather write that block by hand, and the generator will leave it alone.

### 9.2 Refresh the publication list

File: `www/publications.jemdoc` — **generated. Do not hand-edit it**; the next refresh
overwrites it.

The list is built from the [ORCID record](https://orcid.org/0000-0003-3909-4385), with the full
author list, journal, volume, pages and month pulled from Crossref for every DOI. To add a
paper:

1. Add it to your ORCID record — that is the single source of truth — or simply wait for
   Crossref to deposit it when the publisher publishes it.
2. Refresh the page and rebuild:

   ```bash
   make update
   ```

   That is a shortcut for `python tools/update_site.py && python build.py`. The script needs no
   arguments; the ORCID iD is the `ORCID_ID` constant at the top of the file. It writes the
   Publications page *and* the News page, which is why one command covers both.
3. Check the result and commit `www/publications.jemdoc` along with your other changes.

What the script does, and what it will not do:

* It groups entries by year, newest first, as one collapsible `<details>` per year with the
  newest year open. Each entry shows the authors (yours in bold), the title, the type, the
  venue, volume/issue/pages, the month, and a DOI link.
* It drops an arXiv preprint when the same title is already published, so one paper is not
  listed twice.
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
not deposit DOIs. For those, edit `www/publications-extra.bib` and paste the BibTeX straight in:

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

Then run `make update`. The entry is sorted into the right year with everything else, rendered
in exactly the same style, and announced on the News page too.

* The file opens with a header explaining the rules, a template, and **four real entries** that
  are on your HCMIU page but missing from ORCID. Check those four, and delete any you do not
  want — the file works fine when it is empty.
* Lines starting with `%` are comments, so you can park an entry there until you are ready.
* An entry whose DOI **or title** already appears in ORCID is skipped, so it is safe to paste
  something today and let ORCID pick it up later.
* To take an entry off the site, delete it from the file and re-run.
* `python tools/update_site.py --offline` rebuilds both generated pages from that file alone,
  with no network access at all — useful for testing one entry.

### 9.3 Add or remove a student

File: `www/students.jemdoc`

```
- *Full Name* \M PhD, since 2026.\n
  Research: topic in one sentence.\n
  Email: [name@example.edu]
```

* To add: copy an existing three-line bullet, **including the `\n`**, and edit it.
* To remove: delete all three lines.
* Keep the two leading spaces in front of `Research:` and `Email:` — they make the file easy to
  scan.
* When a student leaves, move the bullet to the alumni list and rewrite it as one sentence.

### 9.4 Add a course, or a dropdown of materials

File: `www/courses.jemdoc`

A course is a heading plus the same information box the other pages use:

```
== Wireless Communications (EE301)

~~~
{Course information}
- *Code*: EE301 \M *Level*: Undergraduate \M *Semester*: Spring 2026 \M *Credits*: 3
- *When*: Monday 09:00--11:00, Building B1, Room 201

*What you will learn:* one or two sentences.
~~~
```

The material files are **not** stored in this repository. They live in a separate GitHub
repository and are linked from here, so the site stays small. Each group of files is a
collapsible **dropdown**: a `<details>` element with a `<summary>` title. Because that is raw
HTML, it goes inside a `~~~` block whose language is `raw`:

```
~~~
{}{raw}
<details class="materials">
<summary>Lecture slides</summary>
<ul>
<li><a href="https://raw.githubusercontent.com/USER/REPO/main/ee301/lecture-01.pdf" target="blank">Lecture 1 &ndash; Introduction (PDF)</a></li>
<li><a href="https://raw.githubusercontent.com/USER/REPO/main/ee301/lecture-02.pdf" target="blank">Lecture 2 &ndash; Fading (PDF)</a></li>
</ul>
</details>
~~~
```

Rules that keep it working:

* `target="blank"` is **required** on every external link. The test-suite checks it, and it
  makes the file open in a new tab instead of replacing your site.
* Use `&ndash;` for a dash and `&amp;` for a literal `&` inside these HTML blocks. A bare `&`
  makes the HTML invalid and fails `test_no_bare_ampersands`.
* Repeat the whole `<details>…</details>` block for each group — slides, assignments, reading
  list, past papers. The styling is automatic: `class="materials"` is defined in
  `www/css/site.css`.
* Two ways to link a file in another repository: the raw URL
  (`https://raw.githubusercontent.com/USER/REPO/main/FOLDER/file.pdf`) opens or downloads it
  directly, while the GitHub page for it
  (`https://github.com/USER/REPO/blob/main/FOLDER/file.pdf`) shows a preview first.
* There is a fully commented template at the bottom of `www/courses.jemdoc`.

### 9.5 Add an award or a grant

File: `www/awards.jemdoc` — one bullet per item:

```
- *2027* \M Description of the award or grant in one sentence.
```

### 9.6 Add a photo to the gallery

1. Put the image in `www/images/` (`gallery-5.jpg`, etc. — lower case, no spaces).
2. In `www/gallery.jemdoc`, copy one `<figure>` inside the `<div class="gallery">` block:

   ```
   <figure><img src="images/gallery-5.jpg" alt="Short description" /><figcaption>Caption text.</figcaption></figure>
   ```

3. Rebuild. The grid adapts to any number of photos.

### 9.7 Change the contact details

One place now: the **Contact** box near the top of `www/biography.jemdoc`. The Home page links
to it rather than repeating it. Inside a box, use `-` bullets so each item gets its own line.

### 9.8 The CV

The CV link was **removed** from the site, because `www/files/cv.pdf` is only a placeholder. The
file and the generator are still in place, so publishing a real CV takes two steps:

1. Replace `www/files/cv.pdf` with your real CV, keeping the name `cv.pdf`.
2. Add the link where you want it, for example in "Quick links" on `www/index.jemdoc`:

   ```
   [files/cv.pdf Curriculum Vitae (PDF)]
   ```

### 9.9 Change the look and feel

File: `www/css/site.css`. All colours are variables at the top:

```css
:root {
  --navy:        #16181d;   /* headings and body text        */
  --text:        #16181d;   /* normal body text              */
  --accent:      #17457a;   /* links, current menu entry     */
  --accent-soft: #eef3f9;   /* barely-there highlight        */
  --muted:       #4a5160;   /* secondary text                */
  --faint:       #8b93a1;   /* captions, labels, dates       */
  --panel:       #f7f8fa;   /* very light fill for code      */
  --border:      #e6e8ec;   /* hairlines                     */
  --page-width:  980px;     /* width of the whole layout     */
  --menu-width:  190px;     /* width of the sidebar column   */
}
```

Below that are the fonts (`--font-body`, `--font-head`, `--font-mono`). The design rules are
written at the top of the file: one narrow column of text, one accent colour, no boxes or
shadows, and one shared look for every list. The menu is a **sidebar** down the left of the
page; below 760px it turns into a wrapping row above the text.

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

- [ ] *Portrait photo* — `www/images/portrait.svg` is still the placeholder illustration.
- [ ] *Gallery photos and captions* — `www/images/gallery-1..4.svg` and the `<figure>` blocks in
      `www/gallery.jemdoc`.
- [ ] *CV* — `www/files/cv.pdf` is a placeholder and is no longer linked from anywhere. See
      [§9.8](#98-the-cv) if you want to publish a real one.
- [ ] *Faculty colleagues* — the 2nd, 3rd and 4th table rows in `www/faculty.jemdoc`, plus the
      visiting professor and the alumnus below the table.
- [ ] *Students* — every entry in `www/students.jemdoc` (five `student.*@example.edu` people).
- [ ] *Course material links* — `YOUR-GITHUB-USER/YOUR-COURSE-REPO` in `www/courses.jemdoc`.

Three things were **deliberately left out** because no source could confirm them, rather than
invented:

- *Office hours* — absent from `www/index.jemdoc` and `www/biography.jemdoc`.
- *Editorial roles and invited talks* — removed from `www/biography.jemdoc` and
  `www/awards.jemdoc`; only the verifiable reviewer list remains.
- *Talks, group news, new students* — `www/news.jemdoc` now lists real publication records only.

To find anything left over:

```bash
grep -rn 'example\.edu\|Example \|20XX' www/
```

(`Select-String -Path www/* -Pattern 'example\.edu|Example '` on Windows.)

The copyright name in the footer lives in `www/mysite.conf` (`[lastupdated]`).

---

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
      `www/*.jemdoc` (except `menu.jemdoc`), i.e. 11 with the current content.
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
      `images/portrait.svg`, `files/cv.pdf` (covered by `test_static_assets_are_copied`).
- [ ] **Commit sources only.** `_site/` is generated and ignored — never commit it. The
      published site is rebuilt from `www/` by GitHub Actions, so there is no second copy to
      keep in step.

Full run, for reference:

```console
$ python build.py
Build finished.
  output folder : D:\Code\phuongluuvo.github.io\_site
  pages written : 11
  ...
  assets copied : css/, files/, images/

$ python -m pytest
...........................................                              [100%]
43 passed in 1.52s
```

(The exact number grows as checks are added; what matters is that nothing fails.)

### 10.2 What the test-suite covers

Every `.jemdoc` source produced its `.html` page · identical menu on all pages · each page
highlights its own menu entry · no broken relative links/images · only external links open a
new tab · no unescaped `&` · no HTML5 parse errors · every page is valid UTF-8 and non-ASCII
text survives the build · every page has a `<title>`, an `<h1>`, the stylesheet and a footer ·
MathJax loaded everywhere · publication years newest-first, every entry links to its DOI, and
each year summary agrees with the entries listed · placeholder PDFs really are PDFs · the
generated `.jemdoc` files say that they are generated · the GitHub Actions workflow is valid
YAML and only ever runs the generator in a way that cannot break the deployment · the two
generated pages are tracked by git · sources are normalised CRLF → LF.

Another group covers the **generated pages**: the news is grouped by year newest-first, the two
most recent years are open and the rest are collapsed, every year summary agrees with its
entries, every announcement has a well-formed date, **every publication appears in the news**,
the Home-page headlines are the newest announcements, the note at the top of each generated page
came through jemdoc intact, and `tools/update_site.py` runs end to end with no network access.

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

> **This is not optional.** The generated HTML is no longer committed, so if the Pages source
> is still set to "Deploy from a branch" the live site will stop updating. Set the source to
> **GitHub Actions** once, then push.

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
`www/publications.jemdoc` and `www/news.jemdoc`. Run `make update` locally when you want them
refreshed, and commit the result.

**"The Home page still shows the old news items."**
That block is rewritten from the News page. It sits between two `GENERATED latest-news` comment
markers in `www/index.jemdoc`, and if either marker is missing it is left alone on purpose. Run
`make update` to refresh it.

**"How do I read a failed CI run?"**
**Actions** → the run → the job → the failed step. The last lines name the test and the problem.
Reproduce it locally with `python build.py && python -m pytest` (or `make verify`), fix the
source, and push again. A red **Rebuild and test** job does not stop the deployment, because it
is the second, non-blocking job — but it always means something is genuinely wrong.

**"I broke `www/publications.jemdoc` or `www/news.jemdoc`."**
Both are committed, so git can restore them: `git checkout -- www/news.jemdoc`, or simply
re-run `python tools/update_site.py`. There is no way to break them permanently, which is
exactly why the generated files are committed rather than ignored.

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
   * `_site/*.html` (11 pages), `_site/css/site.css`, `_site/files/*`, `_site/images/*`,
   * `_site/.nojekyll`.

   Their sources are, respectively: `www/*.jemdoc`, `www/css/site.css`, `www/files/` and
   `www/images/`. `www/` is the only place to edit — with two exceptions:
   `www/publications.jemdoc` and `www/news.jemdoc` are both generated by
   `tools/update_site.py`. Never edit those two by hand. To change what they contain, edit your
   ORCID record, or paste BibTeX into `www/publications-extra.bib`, or write an announcement in
   `www/news-extra.txt`, and run `make update`.
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
   `for-students.html` also lights up on `students.html` — which is why the For Students page
   is `www/joining.jemdoc`. Call the page by a name no other page ends with.
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
| the menu on every page | `www/menu.jemdoc` |
| `<head>`, MathJax config, `<title>` suffix, footer | `www/mysite.conf` (`[firstbit]`, `[windowtitle]`, `[lastupdated]`) |
| colours / fonts / layout | `www/css/site.css` |
| the publication list and the news | `tools/update_site.py` (the ORCID iD is at the top) |
| the build pipeline | `build.py` |
| the checks | `tests/test_site.py` |
| CI / deployment | `.github/workflows/pages.yml` |
| line-ending policy | `.gitattributes` |
| ignored files | `.gitignore` |

### 13.3 How to verify a change did not break other pages

The generated pages share the menu, the `<head>` and the stylesheet, so a change to
`www/menu.jemdoc`, `www/mysite.conf` or `www/css/site.css` affects **all 11 pages at once**.
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
| `test_publications_are_grouped_by_year_newest_first`, `test_every_publication_links_to_its_doi`, `test_publication_year_summaries_agree_with_their_entries` | the generated publication list is malformed, or `www/publications.jemdoc` has been hand-edited |
| `test_generated_html_uses_lf_line_endings`, `test_build_normalizes_crlf_line_endings`, `test_every_source_page_is_staged_with_lf` | CRLF line endings or a BOM crept in |
| `test_github_actions_workflow_is_valid_yaml` | `.github/workflows/*.yml` is no longer valid YAML |

`git diff` will **not** show the effect of your change on the generated pages, because the
output is not committed. If you cannot run pytest (no dependencies available), build and then
search the output instead:

```bash
python build.py
grep -l 'Your new menu label' _site/*.html      # expect all 11 pages
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
  `build.py`, `tools/update_site.py`, `tools/make_placeholder_pdfs.py` and `tests/test_site.py`.

### Where documentation belongs

There are exactly two documents, and each has one job, so that nothing has to be kept in step
by hand:

| File | Audience | Contains |
| --- | --- | --- |
| `guide.md` | the site owner, contributors, agents | **all** operational material: build, edit, publish, troubleshoot, conventions, the vendored patches, licence |
| `AGENTS.md` | AI coding agents | the hard rules only — it is auto-loaded by the editor, so it stays short |

When you add something, put it in the file whose job it is and **link** to it from the other
rather than copying it.
