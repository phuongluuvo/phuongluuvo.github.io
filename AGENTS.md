# AGENTS.md — instructions for AI coding agents

This repository is the personal website of Assoc. Prof. Phuong Luu Vo: static
[jemdoc](http://jemdoc.jaboc.net/) sources compiled to HTML by `build.py`, with MathJax 3 for
equations, published with GitHub Pages.

**Read [`guide.md`](guide.md) before changing anything.** It is the full manual for both humans
and agents; §13 is the agent-specific part. It is the only manual — nothing is duplicated
elsewhere.

## The five rules that matter most

1. **Edit sources in `www/` only.** `www/*.jemdoc` (pages), the two sidebars
   (`www/menu.jemdoc`, `www/menu-lab.jemdoc`),
   `www/mysite.conf` (control file: `<head>`, MathJax config, `<title>`, footer, favicon),
   `www/css/site.css`, `www/images/` (pictures shown on a page) and `www/files/` (documents
   visitors download — optional, and it does not exist until there is one).
2. **Never hand-edit generated files.** `build.py` writes the entire site into `_site/` —
   `_site/*.html`, `_site/css/`, `_site/images/`, `_site/files/` and `.nojekyll`. That folder is
   gitignored and rebuilt from scratch every time, and every generated page carries a
   `GENERATED FILE. DO NOT EDIT` comment in its `<head>`. The asset folders are **mirrored**,
   so a file deleted from `www/` is deleted from the output on the next build.
   **Two source files are also generated:** `www/publications.jemdoc` and `www/news.jemdoc`
   both come from `tools/update_site.py`. To change the publication list, edit the ORCID record
   and run `make update`; for a paper ORCID does not have, paste BibTeX into
   `www/publications-extra.bib`; for an announcement that is not a paper, write it in
   `www/news-extra.txt`. Never edit a generated `.jemdoc` by hand.
3. **After any source change run `python build.py`.** The published site is rebuilt from `www/`
   by CI, so an unbuilt change is an unverified change. Commit **sources only** — `_site/` is
   generated and ignored; never commit it.
4. **Do not add or remove a page without updating its menu,** and keep each page's own header in
   sync: the second argument of `menu{menu.jemdoc}{X.html}` must equal that page's `.html` file
   name. There are two menus — `menu.jemdoc` (the main site, including the course pages) and
   `menu-lab.jemdoc` (the Edge AI Lab) — and `build.py` never builds one into a page.
5. **MathJax is configured in exactly one place** — the `[firstbit]` section of
   `www/mysite.conf`. Never add a MathJax `<script>` to an individual page.

## Commands

```bash
python build.py                  # rebuild the whole site into _site/ (gitignored)
python build.py --out docs       # build into a different folder
python build.py --serve          # build + preview at http://localhost:8000
python build.py --clean          # delete the generated *.html
make verify                      # build to _site/ + run the full test-suite
make update                      # refresh the generated pages from ORCID, then build
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
grep -l 'Your new menu label' _site/*.html    # expect all 16 pages
```

The suite (`tests/test_site.py`) catches broken links, a menu entry pointing at a
renamed page, a page that fails to highlight itself, a bare `&`, malformed HTML, invalid UTF-8
(or a code-page lookalike character), a missing stylesheet or `<h1>`, missing MathJax, a
malformed publication list, a publication that never reaches the News page, a Home-page news
block that drifts from the News page, CRLF line endings, and an invalid CI workflow.

## Do not

* Rename or move `www/`, any `menu*.jemdoc` or `mysite.conf`. jemdoc runs inside one staging
  directory and resolves every relative path from the site root; that layout is load-bearing.
* Commit generated output, or remove the `_site/`, `/docs/` or anchored `/*.html`, `/css/`,
  `/files/`, `/images/`, `/.nojekyll` rules from `.gitignore`. This repository holds sources,
  tooling and documentation only.
* Hand-edit `www/publications.jemdoc`, or add a page whose file name is the tail of another
  page's name (see rule 4).
* Rename files to a different case, or introduce spaces/uppercase. Windows and macOS would
  accept it; git and GitHub Pages would not.
* Reformat the CRLF → LF normalisation in `build.py`, or save `.jemdoc` files as CRLF. jemdoc
  treats a CRLF blank line as non-blank and silently swallows paragraphs.
* Modify `tools/jemdoc` casually. It is vendored upstream jemdoc + MathJax 0.7.3 with **five**
  local fixes marked `LOCAL FIX` (`guide.md` §2). Keep them all intact.
* Mass-rewrite page content to "improve" style; content belongs to the site owner.
