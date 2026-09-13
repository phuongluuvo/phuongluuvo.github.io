#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_placeholder_pdfs.py -- create the dummy PDF files that ship with this site.

The website links to a CV and to course materials. So that the demo has no broken
links, this script writes tiny, valid, single-page PDFs that simply say "placeholder".
Replace them with the real documents (same file names) and you are done.

Usage:
    python tools/make_placeholder_pdfs.py

Only the standard library is used, so this works in any Python 3 environment.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = os.path.join(os.path.dirname(HERE), "www", "files")


def escape(text: str) -> str:
    """Escape the characters that are special inside a PDF string literal."""
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def make_pdf(path: str, title: str, body: list[str]) -> None:
    """Write a minimal but valid single-page PDF."""
    content = "BT /F1 18 Tf 72 760 Td (%s) Tj ET\n" % escape(title)
    y = 726
    for line in body:
        content += "BT /F1 12 Tf 72 %d Td (%s) Tj ET\n" % (y, escape(line))
        y -= 20

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "<< /Length %d >>\nstream\n%sendstream" % (len(content), content),
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body_text in enumerate(objects, start=1):
        offsets.append(len(out))
        out += ("%d 0 obj\n%s\nendobj\n" % (index, body_text)).encode("latin-1")

    xref_position = len(out)
    out += ("xref\n0 %d\n" % (len(objects) + 1)).encode("latin-1")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += ("%010d 00000 n \n" % offset).encode("latin-1")
    out += (
        "trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, xref_position)
    ).encode("latin-1")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(bytes(out))
    print("wrote %s" % os.path.relpath(path, os.path.dirname(HERE)))


PLACEHOLDERS = {
    "cv.pdf": (
        "Curriculum Vitae - PLACEHOLDER",
        [
            "This is a placeholder file.",
            "Replace it with your real CV, keeping the file name cv.pdf.",
            "The website links to it from the Home and About me pages.",
        ],
    ),
    "syllabus.pdf": (
        "Syllabus - PLACEHOLDER",
        [
            "This is a placeholder file.",
            "Replace it with the real syllabus of your course.",
            "Every course on the Courses page links to this file.",
        ],
    ),
    "lecture-01.pdf": (
        "Lecture 1 - PLACEHOLDER",
        [
            "This is a placeholder file.",
            "Replace it with the real slide deck, keeping the file name.",
        ],
    ),
    "lecture-02.pdf": (
        "Lecture 2 - PLACEHOLDER",
        [
            "This is a placeholder file.",
            "Replace it with the real slide deck, keeping the file name.",
        ],
    ),
    "lecture-03.pdf": (
        "Lecture 3 - PLACEHOLDER",
        [
            "This is a placeholder file.",
            "Replace it with the real slide deck, keeping the file name.",
        ],
    ),
}


def main() -> None:
    for name, (title, body) in PLACEHOLDERS.items():
        make_pdf(os.path.join(FILES, name), title, body)
    print("\nDone. %d placeholder PDF(s) in www/files/." % len(PLACEHOLDERS))


if __name__ == "__main__":
    main()
