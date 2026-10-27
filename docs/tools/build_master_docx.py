#!/usr/bin/env python3
"""Build the master design document: every design document, the audit, the hardware
references and the current sweep report in one .docx, with the figures embedded.

Usage: python3 docs/tools/build_master_docx.py [out.docx]   (default: docs/safety-governor-design.docx)

Self-validating: the script opens the result, checks that every chapter heading made it in,
that every figure is embedded, and that no em dash slipped into the text. Needs pandoc and
python-docx (pip install python-docx).
"""
from __future__ import annotations

import datetime as dt
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "safety-governor-design.docx")

# (path, chapter title override or None, heading shift)
CHAPTERS = [
    ("README.md", "Overview", 0),
    ("docs/10-plain-english-walkthrough.md", None, 0),
    ("docs/00-objectives.md", None, 0),
    ("docs/01-architecture.md", None, 0),
    ("docs/02-safety-fabric.md", None, 0),
    ("docs/03-interfaces.md", None, 0),
    ("docs/04-specification.md", None, 0),
    ("docs/05-threat-model.md", None, 0),
    ("docs/06-assumptions-register.md", None, 0),
    ("docs/07-verification-plan.md", None, 0),
    ("docs/08-silicon-plan.md", None, 0),
    ("docs/09-analogies.md", None, 0),
    ("docs/11-loop-timing.md", None, 0),
    ("docs/17-use-cases.md", None, 0),
    ("docs/18-viability-and-open-questions.md", None, 0),
    ("docs/19-how-solid-is-the-theory.md", None, 0),
    ("docs/20-experiment-program.md", None, 0),
    ("docs/21-agent-run-plan.md", None, 0),
    ("docs/22-roadmap-to-tapeout.md", None, 0),
    ("docs/23-there-is-no-kill-switch.md", None, 0),
    ("docs/24-the-ladder.md", None, 0),
    ("docs/25-the-rulebook-and-the-board.md", None, 0),
    ("hw/README.md", "hw · From Verilog to GDS, and into the rack", 0),
    ("hw/pcb/rack-integration.md", "hw · Rack integration reference", 0),
    ("docs/AUDIT-2026-10.md", None, 0),
    ("docs/REVIEW-2026-10-22-fact-check.md", None, 0),
    ("results/report.md", "Sweep report (results/report.md)", 0),
]
FIGURES = sorted(f for f in os.listdir(os.path.join(ROOT, "docs", "figures")) if f.endswith(".png"))
PAGE_BREAK = '\n\n```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n\n'


def proportional_tables(text: str) -> str:
    """Rewrite each pipe table's separator row so pandoc gives wide columns the width their
    content needs (pandoc reads relative widths from the dash counts)."""
    out, table = [], []

    def flush():
        if len(table) >= 2 and re.match(r"^\|?\s*:?-{3,}", table[1]):
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table]
            ncol = max(len(r) for r in rows)
            widths = [max((len(r[i]) if i < len(r) else 0) for j, r in enumerate(rows) if j != 1) for i in range(ncol)]
            # a wide column wraps, so its share is its character count capped at 90; a narrow column must still
            # hold its longest word (the header, usually) on one line, and a word in a column that does not wrap
            # takes about four of these units, so the floor is the longest word plus two, times four
            longest = [max((max((len(w) for w in (r[i] if i < len(r) else "").split()), default=0)) for j, r in enumerate(rows) if j != 1) for i in range(ncol)]
            widths = [min(max(w, (lw + 2) * 4), 90) for w, lw in zip(widths, longest)]
            total = sum(widths)
            dashes = [max(3, round(100 * w / total)) for w in widths]
            table[1] = "|" + "|".join("-" * d for d in dashes) + "|"
        out.extend(table)
        table.clear()

    for line in text.split("\n"):
        if line.lstrip().startswith("|"):
            table.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out)


def load(path: str, title: str | None) -> str:
    text = open(os.path.join(ROOT, path), encoding="utf-8").read()
    # the first H1 becomes the chapter title
    lines = text.split("\n")
    if lines and lines[0].startswith("# "):
        if title:
            lines[0] = "# " + title
    elif title:
        lines.insert(0, "# " + title)
    text = "\n".join(lines)
    # figures: make the image paths absolute so pandoc finds them from the temp file
    text = re.sub(r"\]\((?:docs/)?figures/(fig-[a-z-]+\.png)\)",
                  lambda m: "](" + os.path.join(ROOT, "docs", "figures", m.group(1)) + ")", text)
    # links into the repository: keep the text, point at GitHub so they work from the document
    text = re.sub(r"\]\(((?:docs|govsim|tests|rtl|hw|results)/[^)]+)\)",
                  r"](https://github.com/YobieBenjamin/safety-governor/blob/main/\1)", text)
    text = re.sub(r"\]\(((?:0\d|10)-[a-z-]+\.md)\)", r"](https://github.com/YobieBenjamin/safety-governor/blob/main/docs/\1)", text)
    return proportional_tables(text)


def header_ids(md: str) -> list[tuple[int, str, str]]:
    """(level, text, pandoc id) for every heading, using pandoc's own identifier rules."""
    import json
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(md)
        src = fh.name
    out = subprocess.run(["pandoc", src, "--from", "markdown+pipe_tables+raw_attribute+yaml_metadata_block+autolink_bare_uris+gfm_auto_identifiers-smart", "--to", "json"],
                         check=True, capture_output=True, text=True).stdout
    os.unlink(src)
    doc = json.loads(out)

    def plain(inlines) -> str:
        bits = []
        for x in inlines:
            t = x["t"]
            if t == "Str":
                bits.append(x["c"])
            elif t == "Space":
                bits.append(" ")
            elif t in ("Emph", "Strong", "Link", "Code"):
                bits.append(plain(x["c"][-1]) if t != "Code" else x["c"][1])
        return "".join(bits)

    heads = []
    for blk in doc["blocks"]:
        if blk["t"] == "Header" and blk["c"][0] <= 2:
            level, (ident, _, _), inl = blk["c"]
            heads.append((level, plain(inl), ident))
    return heads


def reference_docx() -> str:
    """pandoc's default reference document with a smaller code font, so the ASCII diagrams fit."""
    import docx
    from docx.shared import Pt
    path = os.path.join(tempfile.gettempdir(), "sg-reference.docx")
    with open(path, "wb") as fh:
        fh.write(subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"], check=True, capture_output=True).stdout)
    d = docx.Document(path)
    from docx.shared import Inches
    for name, size in (("Source Code", 7), ("Verbatim Char", 7), ("Compact", 8.5), ("Body Text", 10.5), ("First Paragraph", 10.5)):
        try:
            d.styles[name].font.size = Pt(size)
        except KeyError:
            pass
    for sec in d.sections:          # pandoc keeps the reference document's page setup
        sec.page_width, sec.page_height = Inches(8.5), Inches(11)   # US Letter; pandoc's reference leaves the size unset
        sec.left_margin = sec.right_margin = Inches(0.75)
        sec.top_margin = sec.bottom_margin = Inches(0.8)
    d.save(path)
    return path


# pandoc's markdown reader rather than gfm: only it turns a pipe table's separator row into column
# widths and lets a table span the text width; the gfm reader gave every column the same width and
# left the tables narrow and tall. The same reader computes the heading identifiers for the contents.
def build() -> str:
    today = dt.date.today().isoformat()
    parts = [
        "---",
        'title: "Safety Governor: the design"',
        'subtitle: "A chip that says no. One per NVIDIA GPU, added through the rack\'s own boards."',
        'author: "Yobie Benjamin · yobie AT ieee DOT org · linkedin.com/in/yobie"',
        f'date: "{today} · github.com/YobieBenjamin/safety-governor"',
        "---",
        "",
        "This document is the repository's `README.md`, the plain-English walkthrough, the ten",
        "design documents, the hardware references, the October 2026 audit and the current sweep",
        "report, in one file, with the figures. It is generated by `docs/tools/build_master_docx.py`;",
        "the Markdown sources on GitHub are the originals.",
        "",
    ]
    body = []
    for path, title, _ in CHAPTERS:
        body.append(load(path, title))
    chapters_md = PAGE_BREAK.join(body)
    # a static, clickable table of contents (a Word field would show empty until the reader updates it)
    toc = ["# Contents", ""]
    for level, text, ident in header_ids(chapters_md):
        toc.append(("- " if level == 1 else "    - ") + f"[{text}](#{ident})")
    md = "\n".join(parts) + "\n".join(toc) + PAGE_BREAK + chapters_md
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(md)
        src = fh.name
    cmd = ["pandoc", src, "--from", "markdown+pipe_tables+raw_attribute+yaml_metadata_block+autolink_bare_uris+gfm_auto_identifiers-smart", "--to", "docx",
           "--reference-doc", reference_docx(), "--resource-path", os.path.join(ROOT, "docs"), "-o", OUT]
    subprocess.run(cmd, check=True)
    os.unlink(src)
    return OUT


def fit_pictures(path: str) -> None:
    """pandoc scales a picture to the text width but not to the page height, so a tall figure
    runs off the page; this scales any such picture down to fit, keeping its proportions."""
    import docx
    d = docx.Document(path)
    sec = d.sections[0]
    max_w = sec.page_width - sec.left_margin - sec.right_margin
    max_h = sec.page_height - sec.top_margin - sec.bottom_margin - int(0.6 * 914400)   # room for the caption
    for shape in d.inline_shapes:
        w, h = shape.width, shape.height
        scale = min(max_w / w, max_h / h, 1.0)
        if scale < 1.0:
            shape.width, shape.height = int(w * scale), int(h * scale)
    d.save(path)


def validate(path: str) -> None:
    import docx  # python-docx
    d = docx.Document(path)
    text = "\n".join(p.text for p in d.paragraphs)
    heads = [p.text for p in d.paragraphs if p.style.name.startswith("Heading 1")]
    missing = []
    for chapter, title, _ in CHAPTERS:
        first = open(os.path.join(ROOT, chapter), encoding="utf-8").readline().strip()
        want = (title or first.lstrip("# ")).strip()
        if not any(want[:30] in h for h in heads):
            missing.append(want)
    if missing:
        raise SystemExit(f"chapters missing from the document: {missing}")
    n_img = sum(1 for rel in d.part.rels.values() if "image" in rel.reltype)
    if n_img < len(FIGURES):
        raise SystemExit(f"expected at least {len(FIGURES)} embedded figures, found {n_img}")
    if "\u2014" in text:
        raise SystemExit("an em dash made it into the document")
    n_tables = len(d.tables)
    size_kb = os.path.getsize(path) // 1024
    print(f"wrote {path}: {len(heads)} chapters, {n_tables} tables, {n_img} images, {len(text.split()):,} words, {size_kb} KB")


if __name__ == "__main__":
    out = build()
    fit_pictures(out)
    validate(out)
