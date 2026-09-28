#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
latex_to_page.py -- write a blog post from a LaTeX chapter.

WHY
    The two chapters arrived as PDFs, and a PDF inside a page is not a page: the
    reader gets the browser's viewer, the type cannot be selected, and equations
    had to be pictures. The sources are LaTeX, and the site already loads
    MathJax, so the chapter becomes text with real mathematics in it.

WHAT IT DOES
    Reads one .tex file and writes a .jemdoc source holding a single raw HTML
    block:

      * \\chapter and \\section as headings, \\subsection as a smaller one;
      * paragraphs, italics, bold, links, and the Vietnamese text as it stands;
      * every equation left as LaTeX, for MathJax -- align becomes aligned, and
        equation numbers are kept with \\tag. Matrices, cases and bmatrix are
        handed to MathJax untouched;
      * itemize as a bullet list, enumerate as a numbered one;
      * figures: the referenced image is copied into www/images/blog/ and shown
        with the caption underneath;
      * tables as tables, listings as code, and algorithmic blocks as pseudocode;
      * the bibliography as a numbered list, with \\cite and \\ref turned into
        the numbers they point at.

WHAT IT DOES NOT DO
    It is not a LaTeX engine. A command it does not know is dropped rather than
    guessed at, so read the page over before publishing it.

USAGE
    python tools/latex_to_page.py "www/files/blog/chuong 1 - quy hoach tuyen tinh.tex" \
        --out www/blog/chap1.jemdoc

    Standard library only, like build.py.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMAGES = os.path.join(ROOT, "www", "images", "blog")

#: Environments whose contents are mathematics, and what to wrap them in.
MATH_ENVIRONMENTS = {
    "equation": ("$$", "$$", ""),
    "equation*": ("$$", "$$", ""),
    "displaymath": ("$$", "$$", ""),
    "align": ("$$", "$$", "aligned"),
    "align*": ("$$", "$$", "aligned"),
    "gather": ("$$", "$$", "gathered"),
    "gather*": ("$$", "$$", "gathered"),
    "multline": ("$$", "$$", "gathered"),
    "eqnarray": ("$$", "$$", "aligned"),
}

#: Commands that only decorate their argument.
INLINE = {
    "textbf": ("<b>", "</b>"), "bf": ("<b>", "</b>"),
    "textit": ("<i>", "</i>"), "emph": ("<i>", "</i>"), "textsl": ("<i>", "</i>"),
    "texttt": ("<code>", "</code>"), "textsc": ("", ""),
    "textrm": ("", ""), "textsf": ("", ""), "textnormal": ("", ""), "mbox": ("", ""),
    "mathrm": ("", ""), "text": ("", ""),
}

#: Commands whose whole argument is thrown away.
DROPPED = (
    "label", "index", "nonumber", "notag", "protect", "centering",
    "hfill", "noindent", "maketitle", "tableofcontents", "clearpage", "newpage",
    "vspace", "hspace", "smallskip", "medskip", "bigskip", "par",
    "pagestyle", "fancyfoot", "thispagestyle", "printbibliography",
)

PSEUDO_KEYWORDS = {
    "IF": "if", "ELSIF": "else if", "ELSE": "else", "FOR": "for",
    "FORALL": "for all", "WHILE": "while", "UNTIL": "until", "REPEAT": "repeat",
    "RETURN": "return", "REQUIRE": "require", "ENSURE": "ensure",
    "PRINT": "print", "LOOP": "loop", "DO": "do",
}
PSEUDO_END = {"ENDIF": "IF", "ENDFOR": "FOR", "ENDFORALL": "FORALL",
              "ENDWHILE": "WHILE", "ENDLOOP": "LOOP"}

PAGE = """# jemdoc: menu{menu-blog.jemdoc}{%(name)s.html}, title{%(title)s}, notime
# Written by tools/latex_to_page.py from %(source)s -- edit it, or fix the .tex
# and run the tool again, which overwrites this file.

= %(title)s

~~~
{}{raw}
<div class="post">
<p class="post-meta">%(meta)s</p>
%(body)s</div>
~~~
"""


# --------------------------------------------------------------------------- #
# small LaTeX helpers
# --------------------------------------------------------------------------- #

def take_group(text, start):
    """The {...} group that begins at *start*, and the position after it.

    Braces are matched, so \\textbf{a \\emph{b}} gives the whole argument.
    """
    while start < len(text) and text[start] in " \n\t":
        start += 1
    if start >= len(text) or text[start] != "{":
        return "", start
    depth, index = 0, start
    while index < len(text):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:index], index + 1
        index += 1
    return text[start + 1:], len(text)


def take_optional(text, start):
    """The [...] argument at *start* if there is one, and the position after it."""
    while start < len(text) and text[start] in " \n\t":
        start += 1
    if start < len(text) and text[start] == "[":
        end = text.find("]", start)
        if end != -1:
            return text[start + 1:end], end + 1
    return "", start


def strip_comments(text):
    """Drop % comments, keeping \\% escapes."""
    return re.sub(r"(?<!\\)%.*", "", text)


def escape_text(text):
    """Escape for HTML, leaving the LaTeX that survives for MathJax alone."""
    return html.escape(text, quote=False)


# --------------------------------------------------------------------------- #
# mathematics
# --------------------------------------------------------------------------- #

def clean_math(body, alignment=""):
    """One piece of LaTeX maths, ready for MathJax.

    & and the angle brackets are escaped for HTML: an align block is full of &
    and a lt b appears in half the inequalities, and a bare & makes the page
    invalid. MathJax reads the text back after parsing, so it still sees the LaTeX
    it expects.
    """
    body = re.sub(r"\\(label|nonumber|notag|index)\{[^}]*\}", "", body)
    body = re.sub(r"\\(label|nonumber|notag)\b", "", body)
    body = body.replace("\\rm{", "\\mathrm{").replace("\\rm ", "\\mathrm ")
    body = re.sub(r"\s*\\\\\s*$", "", body.strip())
    if alignment:
        body = "\\begin{%s}%s\\end{%s}" % (alignment, body, alignment)
    body = body.strip()
    return (body.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def math_to_html(body, alignment=""):
    """Display maths, centred, with its number out to the right."""
    tag = re.search(r"\\tag\{([^}]*)\}", body)
    number = tag.group(1) if tag else ""
    body = re.sub(r"\\tag\{[^}]*\}", "", body)
    markup = "$$%s$$" % clean_math(body, alignment)
    if not number:
        return '<p class="equation">%s</p>' % markup
    return ('<p class="equation">%s<span class="eq-number">(%s)</span></p>'
            % (markup, escape_text(number)))


# --------------------------------------------------------------------------- #
# the conversion
# --------------------------------------------------------------------------- #

class Chapter:
    """One chapter being converted: its text, its images and its numbering."""

    def __init__(self, source, prefix, images_prefix):
        with open(source, "r", encoding="utf-8") as handle:
            text = handle.read()
        self.source = source
        self.prefix = prefix
        self.images_prefix = images_prefix
        self.stored = []            # placeholders, in the order they were cut out
        self.blocky = set()         # the ones that are a block, not inline text
        self.chapter_seen = False   # the first \chapter is the post's title
        self.labels = {}            # \label -> the number it points at
        self.cites = {}             # \bibitem key -> [n]
        self.counters = {"figure": 0, "equation": 0, "table": 0, "algorithm": 0}
        body = text.split("\\begin{document}", 1)
        self.body = strip_comments(body[1] if len(body) > 1 else body[0])
        self.body = self.body.split("\\end{document}", 1)[0]
        # The book's own title page is not a post: \maketitle draws it.
        self.body = re.sub(r"\\(title|author|date)\{.*?\}\s*", "", self.body,
                           flags=re.S)
        self.body = re.sub(r"\\maketitle", "", self.body)
        # The byline under \chapter is the post's meta line; it does not need to
        # appear again at the top of the text. It is kept, because that line is
        # what the meta line is made from.
        self.byline = ""
        chapter = re.search(r"\\chapter\{.*?\}", self.body, re.S)
        if chapter:
            byline = re.compile(r"\\textit\{(.*?)\}", re.S).search(
                self.body, chapter.end())
            if byline and byline.start() - chapter.end() < 120:
                self.byline = byline.group(1)
                self.body = self.body[:byline.start()] + self.body[byline.end():]

    # -- placeholders ------------------------------------------------------- #

    def keep(self, markup):
        self.stored.append(markup)
        return "\x00%d\x00" % (len(self.stored) - 1)

    def keep_block(self, markup):
        """Hold a block -- an equation, a figure, a table -- out of the prose."""
        self.blocky.add(len(self.stored))
        return self.keep(markup)

    def restore(self, text):
        def swap(match):
            return self.stored[int(match.group(1))]
        previous = None
        while previous != text:         # a placeholder may hold another
            previous = text
            text = re.sub("\x00(\\d+)\x00", swap, text)
        return text

    def number(self, kind, label=None):
        self.counters[kind] += 1
        if label:
            self.labels[label] = self.counters[kind]
        return self.counters[kind]

    # -- maths -------------------------------------------------------------- #

    def keep_math(self):
        """Cut every equation out of the way, as LaTeX for MathJax."""
        def environment(match):
            name = match.group(1)
            open_tag, close_tag, alignment = MATH_ENVIRONMENTS[name]
            body = match.group(2)
            label = re.search(r"\\label\{([^}]*)\}", body)
            # \nonumber (and \notag) mean LaTeX prints no number for it, so the
            # count must not move either -- otherwise everything after it is one
            # out, which is how (3) went missing the first time.
            numbered = "\\nonumber" not in body and "\\notag" not in body
            if numbered:
                number = self.number("equation", label.group(1) if label else None)
                if not re.search(r"\\tag\{", body):
                    body += "\\tag{%d}" % number
            return self.keep_block(math_to_html(body, alignment))

        pattern = (r"\\begin\{(%s)\}(.*?)\\end\{\1\}" % "|".join(
            re.escape(name) for name in sorted(MATH_ENVIRONMENTS, key=len, reverse=True)))
        self.body = re.sub(pattern, environment, self.body, flags=re.S)

        def display(match):
            return self.keep_block(math_to_html(match.group(1)))

        self.body = re.sub(r"\\\[(.*?)\\\]", display, self.body, flags=re.S)

        def inline(match):
            return self.keep("$%s$" % clean_math(match.group(1)))

        self.body = re.sub(r"(?<!\\)\$(.+?)(?<!\\)\$", inline, self.body, flags=re.S)
        # A literal dollar in the prose is not a maths delimiter: as one, it would
        # swallow the rest of the sentence into a formula.
        self.body = self.body.replace("\\$", "&#36;")

    # -- the things that are not prose -------------------------------------- #

    def keep_verbatim(self):
        self.body = re.sub(
            r"\\begin\{(lstlisting|verbatim)\}(\[[^\]]*\])?(.*?)\\end\{\1\}",
            lambda m: self.keep_block("<pre>%s</pre>" % escape_text(m.group(3).strip("\n"))),
            self.body, flags=re.S)
        self.body = re.sub(r"\\verb\|([^|]*)\|",
                           lambda m: self.keep("<code>%s</code>"
                                               % escape_text(m.group(1))),
                           self.body)

    def keep_bibliography(self):
        def section(match):
            entries = re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]*)\}(.*?)(?=\\bibitem|$)",
                                 match.group(1), flags=re.S)
            items = []
            for index, (key, entry) in enumerate(entries, start=1):
                self.cites[key] = index
                items.append('<li id="cite-%s">%s</li>'
                             % (escape_text(key), self.inline(entry.strip())))
            return self.keep_block('<h2>Tài liệu tham khảo</h2><ol class="refs">%s</ol>'
                                   % "".join(items))
        self.body = re.sub(r"\\begin\{thebibliography\}\{[^}]*\}(.*?)\\end\{thebibliography\}",
                           section, self.body, flags=re.S)

    def keep_figures(self):
        def figure(match):
            content = match.group(3) or ""
            image = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}", content)
            caption = re.search(r"\\caption\{(.*?)\}\s*(?=\\label|\\end|$)", content, re.S)
            label = re.search(r"\\label\{([^}]*)\}", content)
            number = self.number("figure", label.group(1) if label else None)
            if not image:
                return self.keep_block("")
            name = self.copy_image(image.group(1))
            if not name:
                return self.keep_block(
                    '<p class="missing-figure">Hình %d: %s (thiếu tệp ảnh %s)</p>'
                    % (number,
                       self.inline(caption.group(1)) if caption else "",
                       escape_text(image.group(1))))
            caption_html = self.inline(caption.group(1)) if caption else ""
            width = re.search(r"width=([0-9.]+)cm", content)
            style = ""
            if width:
                # A width in centimetres at 96dpi, capped to the column.
                style = ' style="max-width:%dpx"' % round(float(width.group(1)) / 2.54 * 96)
            return self.keep_block(
                '<figure id="fig-%d"><img src="images/blog/%s" alt="Hình %d"%s />'
                '<figcaption>Hình %d: %s</figcaption></figure>'
                % (number, escape_text(name), number, style, number, caption_html))
        self.body = re.sub(r"\\begin\{(figure\*?)\}(\[[^\]]*\])?(.*?)\\end\{\1\}",
                           figure, self.body, flags=re.S)

    def copy_image(self, path):
        """Copy a figure next to the site's images, and return its new name."""
        source = os.path.join(ROOT, "www", "files", "blog",
                              path.replace("/", os.sep))
        if not os.path.isfile(source):
            return None
        name = "%s-%s" % (self.images_prefix,
                          os.path.basename(path).replace(" ", "-"))
        if not name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
            name += ".png"
        os.makedirs(IMAGES, exist_ok=True)
        shutil.copyfile(source, os.path.join(IMAGES, name))
        return name

    def keep_tables(self):
        def rows_of(body):
            rows = []
            for row in re.split(r"\\\\", body or ""):
                row = re.sub(r"\\(hline|toprule|midrule|bottomrule|cline\{[^}]*\})", "",
                             row).strip()
                if not row:
                    continue
                cells = [self.inline(cell.strip()) for cell in row.split("&")]
                rows.append("<tr>%s</tr>" % "".join(
                    "<td>%s</td>" % cell for cell in cells))
            return "".join(rows)

        def table(match):
            content = match.group(3) or ""
            caption = re.search(r"\\caption\{(.*?)\}\s*(?=\\label|\\end|$)", content, re.S)
            label = re.search(r"\\label\{([^}]*)\}", content)
            number = self.number("table", label.group(1) if label else None)
            body = re.search(r"\\begin\{(tabular\*?|tabularx)\}"
                             r"(?:\{[^}]*\})?(?:\{[^}]*\})?(.*?)\\end\{\1\}",
                             content, re.S)
            caption_html = self.inline(caption.group(1)) if caption else ""
            return self.keep_block(
                '<table class="data" id="tab-%d">%s'
                '<caption>Bảng %d: %s</caption></table>'
                % (number, rows_of(body.group(2) if body else ""), number,
                   caption_html))
        self.body = re.sub(r"\\begin\{(table\*?)\}(\[[^\]]*\])?(.*?)\\end\{\1\}",
                           table, self.body, flags=re.S)

        # A tabular that is not wrapped in a table: still a table, and left as
        # text it becomes a paragraph full of ampersands.
        def loose(match):
            if not match.group(2).strip():
                return self.keep_block("")
            return self.keep_block('<table class="data">%s</table>'
                                   % rows_of(match.group(2)))
        self.body = re.sub(r"\\begin\{(tabular\*?|tabularx)\}"
                           r"(?:\{[^}]*\})?(?:\{[^}]*\})?(.*?)\\end\{\1\}",
                           loose, self.body, flags=re.S)

    def keep_algorithms(self):
        """An algorithmic block as pseudocode: one line each, indented by depth."""
        def algorithm(match):
            content = match.group(3) or ""
            caption = re.search(r"\\caption\{(.*?)\}\s*(?=\\label|\\end|$)", content, re.S)
            # An algorithm float whose body is NOT pseudocode commands -- a list,
            # or plain prose -- is not a pseudocode block at all: its contents are
            # handed back to the ordinary conversion, which renders a list as a
            # list and a paragraph as a paragraph. Read as pseudocode it came out
            # as an empty frame.
            if not re.search(r"\\(STATE|IF|ELSIF|FOR|FORALL|WHILE|LOOP|REPEAT|UNTIL|"
                             r"RETURN|REQUIRE|ENSURE)\b", content):
                head = ""
                if caption:
                    head = self.keep_block('<p class="alg-title">%s</p>'
                                           % self.inline(caption.group(1)))
                    content = content[:caption.start()] + content[caption.end():]
                return head + re.sub(r"\\label\{[^}]*\}", "", content)
            number = self.number("algorithm")
            blocks, depth = [], 0
            # A line break in LaTeX is two backslashes; splitting on one would cut
            # every command away from its own argument.
            for line in content.split(r"\\"):
                line = line.strip()
                if not line:
                    continue
                command = re.match(r"\\([A-Za-z]+)\s*(.*)", line)
                if not command:
                    continue
                name, argument = command.group(1).upper(), command.group(2).strip()
                argument = argument.strip("{}")
                if name == "STATE":
                    body = self.inline(argument)
                    blocks.append('<p class="alg" style="margin-left:%dem">%s</p>'
                                  % (1.5 * depth, body))
                elif name in ("IF", "FOR", "FORALL", "WHILE", "LOOP", "REPEAT", "UNTIL"):
                    blocks.append('<p class="alg" style="margin-left:%dem">'
                                  '<b>%s</b> %s</p>'
                                  % (1.5 * depth, escape_text(PSEUDO_KEYWORDS[name]),
                                     self.inline(argument)))
                    if name not in ("UNTIL", "REPEAT"):
                        depth += 1
                elif name in ("ELSE", "ELSIF"):
                    depth = max(0, depth - 1)
                    label = "else" if name == "ELSE" else "else if"
                    blocks.append('<p class="alg" style="margin-left:%dem">'
                                  '<b>%s</b> %s</p>'
                                  % (1.5 * depth, label, self.inline(argument)))
                    depth += 1
                elif name in ("ENDIF", "ENDFOR", "ENDFORALL", "ENDWHILE", "ENDLOOP"):
                    depth = max(0, depth - 1)
                    blocks.append('<p class="alg" style="margin-left:%dem">'
                                  '<b>%s</b></p>'
                                  % (1.5 * depth,
                                     escape_text(PSEUDO_KEYWORDS.get(
                                         PSEUDO_END.get(name, ""), "end"))))
                elif name == "COMMENT":
                    blocks.append('<p class="alg alg-comment" style="margin-left:%dem">'
                                  '%s</p>' % (1.5 * depth, self.inline(argument)))
                elif name == "RETURN":
                    blocks.append('<p class="alg" style="margin-left:%dem">'
                                  '<b>return</b> %s</p>'
                                  % (1.5 * depth, self.inline(argument)))
            title = self.inline(caption.group(1)) if caption else ""
            return self.keep_block('<div class="algorithm">'
                                   '<p class="alg-title">Thuật toán %d: %s</p>%s</div>'
                                   % (number, title, "".join(blocks)))
        self.body = re.sub(r"\\begin\{(algorithm\*?)\}(\[[^\]]*\])?(.*?)\\end\{\1\}",
                           algorithm, self.body, flags=re.S)

    # -- inline markup ------------------------------------------------------ #

    def inline(self, text):
        """The inline commands of one run of text.

        The text is escaped FIRST, so the tags written here survive, and so a bare
        & in the prose becomes &amp;. Braces are untouched by escaping, which is
        what lets the command arguments still be found.
        """
        text = escape_text(text)
        text = text.replace("\\\\", " ")
        text = re.sub(r"\\[,;:!]", "", text)
        text = re.sub(r"\\(?:cite|citep|citet)(?:\[[^\]]*\])?\{([^}]*)\}",
                      lambda m: "[%s]" % ", ".join(
                          str(self.cites.get(key.strip(), "?"))
                          for key in m.group(1).split(",")),
                      text)
        text = re.sub(r"\\(?:eqref|ref)\{([^}]*)\}",
                      lambda m: str(self.labels.get(m.group(1), "?")), text)
        text = re.sub(r"\\(?:hyperref|autoref|nameref|pageref)\[[^\]]*\]\{([^}]*)\}",
                      r"\1", text)
        text = re.sub(r"\\href\{([^}]*)\}\{([^}]*)\}",
                      lambda m: '<a href="%s" target="blank">%s</a>'
                      % (m.group(1).replace("&amp;", "&amp;amp;"), self.inline(m.group(2))),
                      text)
        text = re.sub(r"\\url\{([^}]*)\}",
                      lambda m: '<a href="%s" target="blank">%s</a>'
                      % (m.group(1), m.group(1)), text)
        text = re.sub(r"\\footnote\{([^}]*)\}",
                      lambda m: " (%s)" % self.inline(m.group(1)), text)

        # \textbf{...} and friends, innermost first
        pattern = re.compile(r"\\(%s)\{" % "|".join(INLINE))
        while True:
            match = None
            for candidate in pattern.finditer(text):
                body, end = take_group(text, candidate.end() - 1)
                if "\\" in body and pattern.search(body[-400:]):
                    continue
                match = (candidate, body, end)
            if not match:
                break
            candidate, body, end = match
            opening, closing = INLINE[candidate.group(1)]
            text = text[:candidate.start()] + opening + body + closing + text[end:]

        for name in DROPPED:
            text = re.sub(r"\\%s\b(\[[^\]]*\])?(\{[^}]*\})?" % name, "", text)
        text = re.sub(r"\\(vspace|hspace)\*?\{[^}]*\}", "", text)
        text = re.sub(r"\\begin\{(center|flushleft|flushright|quote|quotation)\}", "", text)
        text = re.sub(r"\\end\{(center|flushleft|flushright|quote|quotation)\}", "", text)
        text = re.sub(r"\\begin\{minipage\}(\[[^\]]*\])?(\{[^}]*\})?", "", text)
        text = re.sub(r"\\end\{minipage\}", "", text)
        text = re.sub(r"\\item\b(\[[^\]]*\])?", "", text)
        text = text.replace("~", " ").replace("\\,", " ").replace("\\ ", " ")
        text = text.replace("---", "\u2014").replace("--", "\u2013")
        text = re.sub(r"\\([%&_#{}])", r"\1", text)
        text = re.sub(r"\\[a-zA-Z]+\*?", "", text)     # anything left over
        return re.sub(r"[ \t]+", " ", text).strip()

    # -- blocks ------------------------------------------------------------- #

    def blocks(self):
        """The body as HTML: headings, lists, paragraphs."""
        out = []
        lines = self.body.split("\n")
        index = 0
        list_stack = []                 # ("ul"/"ol", open at this line)
        paragraph = []

        def flush():
            if not paragraph:
                return
            text = " ".join(paragraph).strip()
            paragraph.clear()
            if not text:
                return
            # An equation, a figure or a table is a block of its own: the run of
            # text is split around it. Inline mathematics is NOT a block -- it
            # stays in the sentence it belongs to.
            buffer = []
            for piece in re.split(r"(\x00\d+\x00)", text):
                if not piece:
                    continue
                index = re.fullmatch(r"\x00(\d+)\x00", piece)
                if index and int(index.group(1)) in self.blocky:
                    if buffer:
                        out.append("<p>%s</p>" % self.inline("".join(buffer).strip()))
                        buffer = []
                    out.append(self.stored[int(index.group(1))])
                else:
                    buffer.append(piece)
            if buffer:
                out.append("<p>%s</p>" % self.inline("".join(buffer).strip()))

        def close_lists(to=0):
            to = max(0, min(to, len(list_stack)))
            while len(list_stack) > to:
                out.append("</%s>" % list_stack.pop()[0])

        while index < len(lines):
            line = lines[index].strip()
            index += 1

            if not line:
                flush()
                continue

            heading = re.match(r"\\chapter\{(.*)\}", line)
            if heading:
                flush()
                close_lists()
                # The first \chapter is the post's own title, which is already the
                # page's heading; a second one would be a real heading.
                if self.chapter_seen:
                    out.append("<h2>%s</h2>" % self.inline(heading.group(1)))
                self.chapter_seen = True
                continue
            heading = re.match(r"\\(sub)*section\*?\{(.*)\}", line)
            if heading:
                flush()
                close_lists()
                # \subsection and \subsubsection are used as the same level here:
                # the chapters number both as 1.1.
                level = 2 if not heading.group(1) else 3
                out.append("<h%d>%s</h%d>"
                           % (level, self.inline(heading.group(2)), level))
                continue

            opening = re.match(r"\\begin\{(itemize|enumerate)\}", line)
            if opening:
                flush()
                tag = "ul" if opening.group(1) == "itemize" else "ol"
                out.append("<%s>" % tag)
                list_stack.append((tag, index))
                continue
            if re.match(r"\\end\{(itemize|enumerate)\}", line):
                flush()
                close_lists(len(list_stack) - 1)
                continue
            item = re.match(r"\\item\s*(.*)", line)
            if item and list_stack:
                flush()
                out.append("<li>%s" % self.inline(item.group(1)))
                # the rest of the item runs until the next \item or \end
                while index < len(lines):
                    following = lines[index].strip()
                    if (not following or following.startswith("\\item")
                            or re.match(r"\\end\{(itemize|enumerate)\}", following)):
                        break
                    out.append(" %s" % self.inline(following))
                    index += 1
                out.append("</li>")
                continue

            other = re.match(r"\\begin\{([^}]*)\}", line)
            if other:
                flush()
                continue
            if re.match(r"\\end\{[^}]*\}", line):
                flush()
                continue

            paragraph.append(line)

        flush()
        close_lists()
        return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Write a blog post from a LaTeX chapter.")
    parser.add_argument("source", help="the .tex file, e.g. 'www/files/blog/chuong 1 ....tex'")
    parser.add_argument("--out", required=True, help="the .jemdoc source to write")
    parser.add_argument("--post", help="the post title; defaults to the chapter title")
    parser.add_argument("--meta", help="the line under the title; defaults to the chapter number and the byline in the source")
    arguments = parser.parse_args()

    name = os.path.splitext(os.path.basename(arguments.out))[0]
    chapter = Chapter(arguments.source, name, name)

    # The order matters. Mathematics is cut out first, so that a formula inside a
    # reference entry or a caption is converted as well: the bibliography used to
    # run before it, and the "$/\sim$" in one of the references came out as two
    # stray dollar signs. Figures and tables then take their captions with the
    # mathematics already held aside, and the bibliography collects the keys that
    # \cite points at.
    chapter.keep_verbatim()
    chapter.keep_math()
    chapter.keep_bibliography()
    chapter.keep_figures()
    chapter.keep_tables()
    chapter.keep_algorithms()

    body = chapter.restore(chapter.blocks())

    title_match = re.search(r"\\chapter\{(.*)\}", chapter.body)
    title = arguments.post or (chapter.inline(title_match.group(1))
                              if title_match else name)
    title = re.sub(r"<[^>]+>", "", title).strip()

    # The meta line: the chapter number from the file's own name, and whatever
    # byline the source carries under its \chapter.
    meta = arguments.meta
    if meta is None:
        number = re.search(r"chuong\s*(\d+)", os.path.basename(arguments.source))
        parts = []
        if number:
            parts.append("Chương %s" % number.group(1))
        if chapter.byline:
            parts.append(chapter.inline(chapter.byline.replace("\\\\", " \u00b7 ")))
        meta = " \u00b7 ".join(parts)

    page = PAGE % {"name": name, "title": title, "meta": meta,
                   "source": os.path.relpath(arguments.source, ROOT).replace(os.sep, "/"),
                   "body": body}
    with open(arguments.out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(page)
    print("wrote %s (title: %s, %d words)"
          % (arguments.out, title, len(re.sub(r"<[^>]+>", " ", body).split())))


if __name__ == "__main__":
    main()
