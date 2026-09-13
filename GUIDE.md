# GUIDE — how to run and edit your website

This is the friendly guide. It assumes **no** knowledge of HTML, CSS or programming.
Everything you need to change is in one folder: **`www/`**.

`README.md` is the technical companion to this file (for whoever sets up the machine or
changes the tooling).

---

## 1. The 60-second version

Every time you change something, you do exactly three things:

```bash
python build.py            # 1. turn the text files into HTML
git add -A                 # 2. collect your changes
git commit -m "update"      # 3. save them
git push                   # 4. publish (GitHub builds the site for you)
```

To see the result before publishing:

```bash
python build.py --serve     # opens http://localhost:8000 in your browser
```

That is all. The sections below explain **which** text file to edit.

> If you are using the included conda environment, run `conda activate vtlp` once per terminal
> session before any of these commands.

---

## 2. Which file controls what

| What you want to change | Edit this file |
| --- | --- |
| The navigation menu (on every page) | `www/menu.jemdoc` |
| Colours, fonts, spacing, page width, icons | `www/css/site.css` |
| MathJax / the site title suffix / the footer | `www/mysite.conf` |
| Home page (welcome text, contact, quick links, latest news) | `www/index.jemdoc` |
| Biography (education, positions, service) | `www/biography.jemdoc` |
| News and announcements | `www/news.jemdoc` |
| About me (contact details, links, credits) | `www/about.jemdoc` |
| Faculty in the group | `www/faculty.jemdoc` |
| PhD / Master students | `www/students.jemdoc` |
| Honors (undergraduate thesis) students | `www/honors.jemdoc` |
| Interns | `www/interns.jemdoc` |
| **Prospective Students** (process, requirements, open topics) | `www/prospective.jemdoc` |
| Photo gallery | `www/gallery.jemdoc` + files in `www/images/` |
| Publications + BibTeX | `www/publications.jemdoc` |
| Awards and grants | `www/awards.jemdoc` |
| Courses, slides and materials | `www/courses.jemdoc` + files in `www/files/` |
| The CV that visitors download | replace `www/files/cv.pdf` |
| The portrait photo on the Home page | replace `www/images/portrait.svg` |
| The MathJax check page | `www/mathjax-test.jemdoc` |

Rule of thumb: **one `.jemdoc` file = one page**. To add a page you add one `.jemdoc` file,
add one line to `www/menu.jemdoc`, and rebuild.

---

## 3. The only 12 things you need to know about the text format

The format is called *jemdoc*. It is just plain text with a few conventions.

| You write | You get |
| --- | --- |
| `= Title` then the next line = subtitle | the big page heading and the grey line under it |
| `== Section` | a section heading |
| `=== Subsection` | a smaller heading |
| `*bold*` | **bold** |
| `/italics/` | *italics* |
| `_underline_` | underline |
| `+monospace+` | `monospace` |
| `[https://example.com Click here]` | a link (URL first, label second) |
| `[biography.html Biography]` | a link to another page of your site |
| `[phuong.luuvo@example.edu]` | an email link |
| `- item` at the start of a line | a bullet point (indent the next line to continue it) |
| a **blank line** | the end of a paragraph — this is required between paragraphs |

Four extra rules that will save you time:

1. **`\n` at the end of a line forces a line break.** Without it, consecutive lines are joined
   into one flowing paragraph. This is how the student entries put the name, the topic and the
   email on separate lines.
2. **Two `/` characters on the same line turn into italics.** If you literally want a slash and
   there is another one on the same line, write `\/`. Journal names like
   `/IEEE Transactions on Wireless Communications/` are intentional italics.
3. **`#` starts a comment.** Everything from `#` to the end of the line is ignored. Put a
   **blank line before** a comment, otherwise it will glue two paragraphs together.
4. **A line starting with `-`, `.`, `:` or `=`** means "list item" / "heading". Do not start a
   normal sentence with those characters.

### Comments are your template library

Every page where you add entries has a commented-out template at the bottom, so you never have
to remember the syntax. For example, at the bottom of `www/publications.jemdoc` you will find:

```
# ---------------------------------------------------------------------------
# TEMPLATE -- to ADD a publication:
#
# +J5+ *P. L. Vo*, N. X. Author, "Title of the paper," /Journal Name/,
# vol. 1, no. 2, pp. 3--14, 2027.
#
# ~~~
# {BibTeX}{bibtex}
# @article{vo2027shortkey,
#   ...
# }
# ~~~
```

Copy those commented lines into the right place, delete the leading `#`, and fill them in.

---

## 4. How to… (task by task)

### 4.1 …add a news item

File: **`www/news.jemdoc`**

Each item is one bullet at the top of the newest year section:

```
== 2026

- *2026-10-01* \M One-sentence announcement goes here.
- *2026-09-05* \M Existing older item...
```

* `\M` prints a small separator dot (`·`). It is not required.
* Put the newest item **first**.
* If you start a new year, add a new `== 2027` block at the **top** of the list of years.
* The Home page only shows the newest four items, hand-picked in `www/index.jemdoc`.
  Update that list too if the news is important.

### 4.2 …add a publication (and keep the year order correct)

File: **`www/publications.jemdoc`**

jemdoc does **not** sort anything — the order on the page is exactly the order in the file.

1. Find (or create) the section for the year, e.g. `== 2027`.
2. Inside it, journal papers go under `=== Journal papers`, conference papers under
   `=== Conference papers`.
3. Paste the template (see §3) at the **end** of the matching list and edit it:

```
+J5+ *P. L. Vo*, N. X. Author, "Title of the paper," /Journal Name/,
vol. 1, no. 2, pp. 3--14, 2027.

~~~
{BibTeX}{bibtex}
@article{vo2027shortkey,
  author  = {Vo, P. L. and Author, N. X.},
  title   = {Title of the paper},
  journal = {Journal Name},
  volume  = {1},
  number  = {2},
  pages   = {3--14},
  year    = {2027}
}
~~~
```

Rules that keep the page tidy:

* **`+J5+` / `+C6+`** is just the little grey chip at the start. Use `J` for journal papers,
  `C` for conference papers, and keep the numbers increasing.
* Leave **one blank line** between the citation and the `~~~` line, and one blank line after
  the closing `~~~`.
* `--` prints an en dash (–), used in page ranges (`3--14`).
* Years must stay in **descending** order (`2027`, `2026`, `2025`, …). To add a new year, copy
  the whole `== 2026` block, paste it above, and change the year.
* **You do not need to touch `files/publications.bib`.** Every time you build, the download
  file is regenerated from the BibTeX blocks on this page. (The test-suite checks that the two
  stay in sync.)

### 4.3 …add or remove a student

File: **`www/students.jemdoc`** (also `www/honors.jemdoc` and `www/interns.jemdoc`, same idea)

Each student is one bullet of three lines:

```
- *Full Name* \M PhD, since 2026.\n
  Research: topic in one sentence.\n
  Email: [name@example.edu]
```

* **To add:** copy an existing bullet (all three lines, including the `\n`) and edit it.
* **To remove:** delete all three lines.
* The two spaces in front of `Research:` and `Email:` are just for readability — but keep
  them, they make the file much easier to scan.
* The `\n` at the end of a line is what puts the next part on a new line. Do not delete them.
* If a student leaves, move the bullet to the "Completed ... theses" / "Group alumni" list and
  rewrite it as one normal sentence (see the existing examples).

### 4.4 …add a course

File: **`www/courses.jemdoc`**

A course is a heading, an information box, and a list of material links:

```
== Example Course 1 -- Wireless Communications

~~~
{Course information}
- *Code*: EE301 \M *Level*: Undergraduate \M *Semester*: Spring 2026 \M *Credits*: 3
- *When*: Monday 09:00--11:00, Building B1, Room 201
- *Office hours*: Tuesday 14:00--16:00, or by appointment

*What you will learn:* one or two sentences.
~~~

*Materials*

- [files/syllabus.pdf Syllabus and reading list (PDF)]
- [files/lecture-01.pdf Lecture 1 -- Introduction (PDF)]
```

* The box is created by `~~~`, then a title in `{...}`, the content, then `~~~` again.
* **Slides:** put your PDF files in `www/files/` and link them as
  `[files/your-file.pdf The label you want]`.
* Links ending in `.pdf` automatically get a small red PDF badge (see §5.6).
* There is a full commented template at the bottom of the file — copy it, remove the `#`.

### 4.5 …change the menu

File: **`www/menu.jemdoc`** — one file, used by every page.

```
Home
 Biography [biography.html]
 News [news.html]
 About me [about.html]
Research Group
 Faculty [faculty.html]
 ...
```

* A line **without** brackets is a grey category heading (`Research Group`).
* A line **with** brackets is a link: the visible text, then the target file in `[ ]`.
* The order in this file is the order in the menu.
* Wrap a long label in `{{double braces}}` if you do not want it forced onto a single line,
  e.g. `{{PhD / Master students}} [students.html]`.

**Adding a new page** takes three steps:

1. Copy an existing page, e.g. `cp www/news.jemdoc www/seminars.jemdoc`.
2. Edit it: change the first line to `# jemdoc: menu{menu.jemdoc}{seminars.html}, notime`,
   then the `= Title` and the content.
3. Add ` Seminars [seminars.html]` to `www/menu.jemdoc`, then rebuild.

The second value in `menu{menu.jemdoc}{seminars.html}` **must** match the file name — that is
what makes the menu entry highlight itself when the page is open.

The `Home` category deliberately has no page of its own: the page heading at the top of every
page is a link back to the Home page. (If you would rather have a plain, unlinked heading,
delete the `<a href="index.html">` and `</a>` in the `[doctitle]` section of
`www/mysite.conf`.)

### 4.6 …change the contact details and office hours

Two places:

* `www/index.jemdoc` — the box under **Contact and office hours** (this is the one visitors
  see first).
* `www/about.jemdoc` — the same information in more detail.

Inside a box, use `-` bullets so that each item gets its own line.

### 4.7 …change the CV and the profile links

* **CV:** replace the file `www/files/cv.pdf`, keeping the name `cv.pdf`. Every "Download my
  CV" link keeps working. (The one that ships with the demo is a placeholder created by
  `python tools/make_placeholder_pdfs.py`.)
* **Google Scholar / ORCID / ResearchGate / GitHub / LinkedIn:** edit the "Quick links" line on
  `www/index.jemdoc` and the list on `www/about.jemdoc`. Each link is
  `[full-url Label]`. Replace the placeholder URLs — the Scholar id `XXXXXXXX` and the ORCID
  `0000-0000-0000-0000` are dummies.
* The little badge icons appear **automatically** based on the URL — see §5.6.

### 4.8 …add a photo to the gallery

1. Put the image in `www/images/` (a `.jpg`, `.png` or `.svg`; keep it reasonably small, under
   ~300 KB, so the page stays fast).
2. In `www/gallery.jemdoc`, copy a `<figure>` line inside the `<div class="gallery">` block and
   change the file name and the caption:

```
<figure><img src="images/my-photo.jpg" alt="Short description" /><figcaption>Caption text.</figcaption></figure>
```

3. Rebuild. The grid rearranges itself automatically for any number of photos.

The same `{}{img_left}` trick used for the Home page portrait is explained in §5.5 if you want
a photo beside a block of text on another page.

### 4.9 …add an award or a grant

File: **`www/awards.jemdoc`** — one bullet per item:

```
- *2027* \M Description of the award or grant in one sentence.
```

### 4.10 …add or close a prospective-student topic

File: **`www/prospective.jemdoc`**, section 3.

```
=== T5. Short topic title (open)
*Question:* the one question the project answers.\n
*Scope:* what the student will actually do, step by step.\n
*Prerequisites:* tools and background needed.\n
*Good outcome:* what a successful result looks like.
```

* `(open)` in the heading is just text — keep the convention so it is obvious at a glance.
* To close a topic, either delete the block or change `(open)` to `(taken)`.
* The `\n` at the end of each line is what puts each field on its own line.
* Update the sentence "The list below is updated every semester" whenever you change it.

### 4.11 …change the look and feel

File: **`www/css/site.css`**

All the colours are variables at the very top of the file. Change one line, rebuild, done:

```css
:root {
  --navy:        #1b3a63;   /* headings, menu section titles  */
  --accent:      #2b6cb0;   /* links, active menu item        */
  --accent-soft: #e8f0fa;   /* highlight background           */
  --text:        #1f2733;   /* normal body text               */
  --muted:       #61708a;   /* dates, captions, footer        */
  --panel:       #f5f7fa;   /* info boxes, code boxes         */
  --border:      #e0e6ef;   /* thin lines                     */
  --page-width:  1100px;    /* overall width of the site      */
  --menu-width:  210px;     /* width of the left menu column  */
}
```

Below that, the fonts:

```css
--font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, ... ;
--font-head: Georgia, "Iowan Old Style", "Times New Roman", serif;
--font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, ... ;
```

The site is responsive: on a screen narrower than 780px the menu moves to the top and the
content becomes a single column.

---

## 5. Details, defaults and where the extras live

Everything in this section is something I chose for you. All of it can be changed.

### 5.1 Defaults I picked

| Default | Where to change it |
| --- | --- |
| Navigation menu exactly as you specified, plus **Prospective Students** and **Gallery** under *Research Group*, and **Awards & Grants** under *Research* | `www/menu.jemdoc` |
| The page heading is a link back to the Home page (the `Home` menu entry is a category, not a page) | `[doctitle]` in `www/mysite.conf` |
| Menu is a left sidebar; on screens narrower than 780px it moves to the top | `www/css/site.css` |
| Page title in the browser tab is `Page name · Phuong Luu Vo` | `[windowtitle]` in `www/mysite.conf` |
| Footer shows `© Assoc. Prof. Phuong Luu Vo · Last updated: YYYY-MM-DD · Built with jemdoc + MathJax` | `[lastupdated]` in `www/mysite.conf` |
| Dates are shown as `YYYY-MM-DD` (no time, no time zone) | the `notime` flag in each page's first line |
| Internal links open in the same tab; external links, email links and the footer credit open in a new tab | `tools/jemdoc` (see README §5) |
| BibTeX blocks are always visible (collapsible toggles were the alternative) | see §5.4 |
| Serif headings (Georgia), sans-serif body text | `www/css/site.css` |
| Section headings are suffixed `(open)` / `(taken)` for topics, `J1`/`C1` for publications | the `.jemdoc` files |

### 5.2 MathJax (equations)

Equations are rendered by **MathJax 3**, loaded from the jsDelivr CDN, configured in
`www/mysite.conf`. Visitors without internet access will see the raw LaTeX source — that is
expected.

* **Inline equation:** `$\gamma_k = p_k h_k / \sigma^2$`
* **Display equation:** put `\(` on its own line, the LaTeX, then `\)` on its own line:

```
\(
\gamma_k = \frac{p_k\, h_k}{\sigma^2}, \qquad k = 1, 2, \ldots, K .
\)
```

`www/mathjax-test.html` (linked from the Home page) shows both and tells you how to diagnose a
problem. The test-suite checks that the equations are still there after every change.

### 5.3 The downloadable `.bib` file

`files/publications.bib` is **generated** by the build from the `{BibTeX}{bibtex}` blocks on
`www/publications.jemdoc`. Do not edit it by hand — edit the page. The number of blocks on the
page and the number of entries in the file are checked by the test-suite.

### 5.4 BibTeX blocks are plain, always-visible blocks

The publications page shows each BibTeX entry in a bordered, monospace block with a `BIBTEX`
title bar. If you prefer them collapsed behind a "show/hide" toggle, replace this part of
`www/mysite.conf`:

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

and change the `[codeblockend]` line from `</pre></div></div>` to
`</pre></div></details>`. Note that this affects **all** code blocks in the site.

### 5.5 Photo beside a block of text

The Home page uses jemdoc's "image left" block:

```
~~~
{}{img_left}{images/portrait.svg}{Portrait of Phuong Luu Vo}{175}{}{}
Welcome! I am an Associate Professor...
~~~
```

The seven `{...}` fields are `{title}{img_left}{image file}{alt text}{width}{height}{link}`.
Leave the width blank to use the image's natural size.

### 5.6 The automatic link badges

Small square icons are added by CSS to links that point at well-known sites, purely based on
the URL — you do not write any markup for them:

| Badge | Appears for links to |
| --- | --- |
| envelope | `mailto:` links (i.e. bare `[name@example.edu]`) |
| **G** | `scholar.google.com` |
| **iD** | `orcid.org` |
| **RG** | `researchgate.net` |
| **aX** | `arxiv.org` |
| **GH** | `github.com` |
| **in** | `linkedin.com` |
| **PDF** | any link ending in `.pdf` |
| **BIB** | any link ending in `.bib` |

To change, remove or add badges, edit the block marked *"profile icons"* in
`www/css/site.css`. Each one is a self-contained `background-image: url("data:image/svg+xml,...")`
rule, so copying a rule and changing the colour and letters is enough.

### 5.7 Tables

`www/faculty.jemdoc` shows how to make a data table (used for the faculty list). Two things to
know:

* Cells are separated by a single `|`, and each row **ends** with `||`.
* jemdoc always leaves one empty row at the very bottom; the stylesheet hides it, so you do not
  have to do anything about it.

```
~~~
{Faculty members}{table}{faculty}
*Name* | *Position* | *Research area* | *Contact* ||
Phuong Luu Vo | Associate Professor | Resource allocation | [phuong.luuvo@example.edu] ||
~~~
```

The third `{faculty}` value is the table's id; keep it unique on the page (the stylesheet uses
it to recognise data tables).

---

## 6. Rebuilding and publishing

### 6.1 Build locally

```bash
conda activate vtlp        # if you use the provided environment
python build.py            # writes all *.html into the repository root
python build.py --serve    # or: build and preview at http://localhost:8000
python -m pytest           # optional but recommended: 23 checks, takes ~1 second
```

If `python build.py` prints `error: ... not found`, you are not in the repository root — `cd`
to the folder that contains `build.py`.

### 6.2 Publish

```bash
git add -A
git commit -m "Update website"
git push
```

### 6.3 Deployment — one-time GitHub setup

**Method A (recommended): GitHub Actions builds and deploys for you.**

1. Push the repository to GitHub.
2. Repository → **Settings** → **Pages**.
3. **Build and deployment** → **Source** → choose **GitHub Actions**.
4. Done. Every future `git push` to `main` rebuilds the site from the `.jemdoc` sources and
   publishes it. You can watch it under the **Actions** tab.

**Method B: GitHub serves the HTML that you committed.**

1. Build locally (`python build.py`), then commit and push the generated `.html` files.
2. **Settings** → **Pages** → **Source** → `Deploy from a branch`.
3. Branch `main`, folder `/ (root)`, then **Save**.
4. If you use Method B, disable the workflow so that the two mechanisms do not fight over the
   site: delete `.github/workflows/pages.yml` (or disable it from the **Actions** tab).

**Method C: publish only the `docs/` folder** (keeps the repository root tidy).

1. `python build.py --out docs`
2. `git add -A && git commit -m "Publish site" && git push`
3. **Settings** → **Pages** → **Source** → `Deploy from a branch`, branch `main`, folder
   `/docs`, then **Save**.

Use **one** of the three methods only. `CNAME` and `.nojekyll` are written into whichever
output folder you choose, so the custom domain keeps working.

**Custom domain.** `CNAME` contains `phuongluuvo.me` and is copied into the built site
automatically. To use it: **Settings** → **Pages** → **Custom domain** → enter
`phuongluuvo.me` → **Save**, then enable **Enforce HTTPS** (this can take a few minutes). Your
DNS provider must point the domain at GitHub Pages. To stop using the custom domain, delete the
`CNAME` file and clear the custom-domain field.

---

## 7. Checklist of placeholder content to replace

Search for the word `Example` and for `example.edu` — that finds almost all of it.

- [ ] `Example University`, `Department of Communications Engineering` — `www/index.jemdoc`,
      `www/about.jemdoc`, `www/faculty.jemdoc`
- [ ] Email address `phuong.luuvo@example.edu` — `www/index.jemdoc`, `www/about.jemdoc`
- [ ] Google Scholar id `XXXXXXXX` — `www/index.jemdoc`, `www/about.jemdoc`
- [ ] ORCID `0000-0000-0000-0000` — `www/index.jemdoc`, `www/about.jemdoc`
- [ ] Portrait photo — `www/images/portrait.svg`
- [ ] Gallery photos — `www/images/gallery-1..4.svg`
- [ ] CV — `www/files/cv.pdf`
- [ ] Course materials — `www/files/syllabus.pdf`, `www/files/lecture-01..03.pdf`
- [ ] Office, office hours, postal address — `www/index.jemdoc`, `www/about.jemdoc`
- [ ] Biography: education, appointments, editorial roles — `www/biography.jemdoc`
- [ ] Faculty list — `www/faculty.jemdoc`
- [ ] Students, honors students, interns — `www/students.jemdoc`, `www/honors.jemdoc`,
      `www/interns.jemdoc`
- [ ] Open topics — `www/prospective.jemdoc`
- [ ] Publications and their BibTeX — `www/publications.jemdoc`
- [ ] Grants, awards, invited talks — `www/awards.jemdoc`
- [ ] Courses and materials — `www/courses.jemdoc`
- [ ] News items — `www/news.jemdoc` and the "Latest news" list in `www/index.jemdoc`
- [ ] Journal and conference names (`Example Transactions on ...`) — `www/publications.jemdoc`,
      `www/biography.jemdoc`, `www/news.jemdoc`

The tiny copyright name in the footer also lives in `www/mysite.conf` (`[lastupdated]`).

---

## 8. Troubleshooting

**"Nothing changed on the website."**
You edited a `.jemdoc` file but did not rebuild, or you built but did not commit/push. Run
`python build.py`, check the change locally with `python build.py --serve`, then
`git add -A && git commit && git push`.

**"Two paragraphs merged into one."**
There was no blank line between them, or you put a comment line directly under a paragraph.
Comments need a blank line above them.

**"My text after a `#` disappeared."**
`#` starts a comment. Write `\#` if you need a literal hash character.

**"Something I wrote in italics/slashes looks wrong."**
Two `/` on one line make italics. Write `\/` for a literal slash when another `/` is on the
same line.

**"A line of my text vanished / became a bullet."**
Lines that start with `-`, `.`, `:`, `=` or `~` are treated as lists, headings or blocks.
Do not begin a normal sentence with those characters.

**"The site looks unstyled / the CSS is missing."**
The stylesheet is `www/css/site.css` and is copied to `css/site.css` on build. Rebuild and make
sure the browser is not serving a cached copy (Ctrl+F5).

**"Equations show up as raw LaTeX."**
MathJax comes from a public CDN, so you need internet access. Also check that
`www/mysite.conf` still contains the `MathJax-script` line. Open
`http://localhost:8000/mathjax-test.html` to check.

**"`python build.py` fails with `jemdoc failed`".**
Read the error above it — jemdoc reports the source line it could not parse, which is almost
always a missing blank line or a stray structure character.

**"The build works but `python -m pytest` fails."**
The tests tell you exactly what is wrong (a broken link, a missing page, a missing menu entry,
an equation that stopped rendering…). Fix that and re-run. If a test looks wrong rather than the
site, the test file is `tests/test_site.py`.

**"I deleted a page but the menu still links to it."**
Remove its line from `www/menu.jemdoc` too. The test-suite catches this automatically
(`test_every_local_link_and_image_resolves`).

**"Everything looks fine locally but the deployed site is old."**
Check the **Actions** tab: the workflow may have failed. GitHub Pages also caches for a few
minutes.

---

## 9. Where to learn more

* jemdoc syntax reference: <http://jemdoc.jaboc.net/using.html>
* jemdoc example page (a live cheat sheet): <http://jemdoc.jaboc.net/example.html>
* MathJax supported LaTeX commands: <https://docs.mathjax.org/en/latest/input/tex/macros/index.html>
* GitHub Pages documentation: <https://docs.github.com/en/pages>
* Technical details of this repository, including the local fixes to jemdoc: `README.md`
