# AGENTS.md — instructions for AI coding agents

This repository is the personal website of Assoc. Prof. Phuong Luu Vo: static
[jemdoc](http://jemdoc.jaboc.net/) sources compiled to HTML by `build.py`, with MathJax 3 for
equations, published with GitHub Pages.

**Read this file before changing anything.** It is the only documentation the repository has:
the rules below, and the commands in the next section, are all there is, so keep them accurate
when you change something.

## The five rules that matter most

1. **Edit sources in `www/` only.** Pages live in one folder per menu group —
   `www/home/`, `www/profile/` (what the menu lists under the site name), `www/research/`,
   `www/teaching/`, `www/blog/`, `www/misc/` (pages the menu does not link) — alongside the two
   sidebars (`www/menu.jemdoc`, `www/menu-blog.jemdoc`),
   `www/mysite.conf` (control file:
   `<head>`, MathJax config, `<title>`, footer, favicon, the `[materials]` list),
   `www/css/site.css`, `www/images/` (pictures shown on a page), `www/files/` (documents
   visitors download), `www/pdf/` (the PDFs the site displays — course handouts and lecture
   slides) and `www/data/` (the file you edit by hand: the publication list, in BibTeX).

   **The folder and the file name follow the menu.** The page's file name is its address, so
   `www/research/projects.jemdoc` is served as `projects.html`; the menu label is free to be
   longer or in another language. The subfolders are **organisation only**: every page is built
   to the top of `_site/`, so moving a page between folders costs nothing — no link, no menu
   entry. Two pages may therefore not share a file name; the build refuses and says which two
   collide. *Renaming* a page does change its address, so the menu, the page's own
   `menu{…}{page.html}` line and every link to it must change with it.
2. **Never hand-edit generated files.** `build.py` writes the entire site into `_site/` —
   `_site/*.html`, `_site/css/`, `_site/images/`, `_site/files/`, `_site/pdf/` and `.nojekyll`.
   That folder is
   gitignored and rebuilt from scratch every time, and every generated page carries a
   `GENERATED FILE. DO NOT EDIT` comment in its `<head>`. The asset folders are **mirrored**,
   so a file deleted from `www/` is deleted from the output on the next build.
   **One source file is also generated:** `www/profile/publications.jemdoc` comes from
   `tools/build_publications.py`. To change the publication list, edit
   `www/data/publications.bib` and run `make publications`; the tool is offline and
   nothing is fetched from anywhere. Never edit a generated `.jemdoc` by hand. The news is   **not** generated: it is a hand-written list in the `== News` section of
   `www/home/index.jemdoc`, one `- MM/YYYY: text` line per announcement.
3. **After any source change run `python build.py`.** The published site is rebuilt from `www/`
   by CI, so an unbuilt change is an unverified change. Commit **sources only** — `_site/` is
   generated and ignored; never commit it.
4. **Do not add or remove a page without updating its menu,** and keep each page's own header in
   sync: the second argument of `menu{menu.jemdoc}{X.html}` must equal that page's `.html` file
   name. There are two menus — `menu.jemdoc` (the main site, including the course pages) and
   `menu-blog.jemdoc` (the blog) — and `build.py` never
   builds one into a page. A label
   stays on one row, so `--menu-width` in `www/css/site.css` has to be wide enough for the
   longest of them; two entries must never point at the same page.
5. **MathJax is configured in exactly one place** — the `[firstbit]` section of
   `www/mysite.conf`. Never add a MathJax `<script>` to an individual page.

## Commands

```bash
python build.py                  # rebuild the whole site into _site/ (gitignored)
python build.py --out docs       # build into a different folder
python build.py --serve          # build + preview at http://localhost:8000
python build.py --clean          # delete the generated *.html
make verify                      # build to _site/ + run the full test-suite
make publications                # rebuild the Publications page from its BibTeX file, then build
python -m pytest                 # run only the tests (needs the "vtlp" env)
```

`build.py` uses the **standard library only** and must stay that way. The test-suite needs the
packages listed in `requirements.txt` (pip) or `environment.yml` (conda env `vtlp`).

## Verifying a change

The three menus, `www/mysite.conf` and `www/css/site.css` affect **every page at once**, so
`python build.py` succeeding proves nothing by itself:

```bash
python build.py && python -m pytest
```

Because the output is not committed, `git diff` cannot show the effect on the generated pages.
If pytest is unavailable, build and search the output instead:

```bash
python build.py
grep -l 'Your new menu label' _site/*.html    # expect every page
```

The suite (`tests/test_site.py`) catches broken links, a menu entry pointing at a
renamed page, a page that fails to highlight itself, a bare `&`, malformed HTML, invalid UTF-8
(or a code-page lookalike character), a missing stylesheet or `<h1>`, missing MathJax, a
malformed publication list, a news line on the Home page that loses its `MM/YYYY:` shape, CRLF
line endings, and an invalid CI workflow.

## Do not

* Rename or move `www/` itself, a sidebar, `mysite.conf`, or the asset folders (`css/`,
  `images/`, `files/`, `pdf/`). jemdoc runs inside one staging directory and resolves every
  relative
  path from the site root, so that layout is load-bearing. Moving a *page* between the
  subfolders, or into one, is fine and costs nothing.
* Commit generated output, or remove the `_site/`, `/docs/` or anchored `/*.html`, `/css/`,
  `/files/`, `/images/`, `/.nojekyll` rules from `.gitignore`. This repository holds sources,
  tooling and documentation only.
* Hand-edit `www/profile/publications.jemdoc`, or add a page whose file name is the tail of another
  page's name (see rule 4).
* Rename files to a different case, or introduce spaces/uppercase. Windows and macOS would
  accept it; git and GitHub Pages would not.
* Reformat the CRLF → LF normalisation in `build.py`, or save `.jemdoc` files as CRLF. jemdoc
  treats a CRLF blank line as non-blank and silently swallows paragraphs.
* Modify `tools/jemdoc` casually. It is vendored upstream jemdoc + MathJax 0.7.3 with **five**
  local fixes marked `LOCAL FIX`. Keep them all intact.
* Mass-rewrite page content to "improve" style; content belongs to the site owner.
