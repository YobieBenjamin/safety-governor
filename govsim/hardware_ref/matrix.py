# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The compliance matrix: docs/interfaces/compliance_matrix.csv -> docs/interfaces/COMPLIANCE-MATRIX.md.

    python -m govsim.hardware_ref.matrix            # check the CSV and write the Markdown
    python -m govsim.hardware_ref.matrix --check    # exit 1 if the CSV is bad or the Markdown is stale

Rules: every row has a source that resolves to docs/interfaces/sources.csv (or a repo path), or
says "no public source"; status is designed / tested / NDA / members-only / open; an NDA row cites
an NDA source and a members-only row a members-only source or none; every evidence file exists,
and an evidence "file::name" names a function or text that is in that file; a tested row's
evidence is a test or a generated result.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter

from . import REPO
from .dcscm import _read

CSV = REPO / "docs/interfaces/compliance_matrix.csv"
SOURCES = REPO / "docs/interfaces/sources.csv"
OUT = REPO / "docs/interfaces/COMPLIANCE-MATRIX.md"
STATUSES = ("tested", "designed", "open", "members-only", "NDA")


def check(rows: list[dict] | None = None, sources: list[dict] | None = None) -> list[str]:
    rows = _read(CSV) if rows is None else rows
    sources = _read(SOURCES) if sources is None else sources
    by_id = {s["id"]: s for s in sources}
    errs, seen = [], set()
    for r in rows:
        rid = r["id"]
        if rid in seen:
            errs.append(f"{rid}: duplicate id")
        seen.add(rid)
        if r["status"] not in STATUSES:
            errs.append(f"{rid}: status {r['status']!r}")
        src = r["source"].strip()
        cited = []
        if not src:
            errs.append(f"{rid}: no source and no 'no public source'")
        elif src != "no public source":
            for item in (x.strip() for x in src.split(";")):
                head = item.split()[0] if item else ""
                if head in by_id:
                    cited.append(by_id[head])
                    if by_id[head]["access"] in ("public", "public secondary") and not by_id[head]["url"]:
                        errs.append(f"{rid}: source {head} has no URL")
                elif not (REPO / head).exists():
                    errs.append(f"{rid}: source {item!r} is neither a source id nor a repo path")
        if r["status"] == "NDA" and not any(c["access"] == "NDA" for c in cited):
            errs.append(f"{rid}: NDA row without an NDA source")
        if r["status"] == "members-only" and src != "no public source" and not any(c["access"] == "members-only" for c in cited):
            errs.append(f"{rid}: members-only row without a members-only source")
        ev = r["evidence"].strip()
        if not ev:
            errs.append(f"{rid}: no evidence file")
            continue
        path, _, name = ev.partition("::")
        f = REPO / path
        if not f.exists():
            errs.append(f"{rid}: evidence {path} does not exist")
            continue
        if name and f"def {name}(" not in f.read_text(encoding="utf-8") and name not in f.read_text(encoding="utf-8"):
            errs.append(f"{rid}: {name} not found in {path}")
        if r["status"] == "tested" and not (path.startswith("tests/") or path.startswith("docs/interfaces/results/")):
            errs.append(f"{rid}: tested, but the evidence is not a test or a generated result")
    return errs


def render(rows: list[dict] | None = None, sources: list[dict] | None = None) -> str:
    rows = _read(CSV) if rows is None else rows
    sources = _read(SOURCES) if sources is None else sources
    by_id = {s["id"]: s for s in sources}
    n = Counter(r["status"] for r in rows)

    def src_cell(s: str) -> str:
        if s.strip() == "no public source":
            return "no public source"
        out = []
        for item in (x.strip() for x in s.split(";")):
            head, _, rest = item.partition(" ")
            if head in by_id and by_id[head]["url"] and by_id[head]["url"].startswith("http"):
                out.append(f"[{head}]({by_id[head]['url']}){(' ' + rest) if rest else ''}")
            elif head in by_id:
                out.append(f"{head}{(' ' + rest) if rest else ''} ({by_id[head]['access']})")
            else:
                out.append(f"`{item}`")
        return "; ".join(out)

    lines = [
        "# Compliance matrix: the governor against the public NVIDIA server environment",
        "",
        "Generated from `docs/interfaces/compliance_matrix.csv` by `python -m govsim.hardware_ref.matrix` "
        "(do not edit by hand). The one command that re-checks every row is `python -m govsim.hardware_ref`.",
        "",
        "Read this first if you build servers or work with NVIDIA's partner programme. Every row says where the "
        "requirement comes from, how far we got, and the file that proves it. **tested** means a test or a "
        "generated result in this repo fails by assertion if the row is broken. **designed** means it is in the "
        "design files but nothing runs against it. **open** means we know it is not done and say why. "
        "**members-only** and **NDA** mean the deciding document is not public: we have not read it and claim "
        "no compliance with it. Where a number came from a public secondary source instead of the members-only "
        "original, the source column says which.",
        "",
        f"Rows: {len(rows)}. " + ", ".join(f"{k} {n.get(k, 0)}" for k in STATUSES) + ".",
        "",
        "| ID | Area | Requirement | Source | Status | Evidence | Notes |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['id']} | {r['area']} | {r['requirement']} | {src_cell(r['source'])} | **{r['status']}** | `{r['evidence']}` | {r['notes']} |")
    lines += ["", "## Sources", "", "| ID | Document | Access | How we read it |", "|---|---|---|---|"]
    for s in sources:
        doc = f"[{s['title']}]({s['url']})" if s["url"].startswith("http") else (f"{s['title']} (`{s['url']}`)" if s["url"] else s["title"])
        lines.append(f"| {s['id']} | {doc} | {s['access']} | {s['how_read']} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    errs = check()
    for e in errs:
        print("  FAIL", e)
    text = render()
    if "--check" in argv:
        stale = not OUT.exists() or OUT.read_text(encoding="utf-8") != text
        if stale:
            print("  FAIL COMPLIANCE-MATRIX.md is stale: run python -m govsim.hardware_ref.matrix")
        print("compliance matrix:", "PASS" if not errs and not stale else "FAIL")
        return 1 if errs or stale else 0
    OUT.write_text(text, encoding="utf-8")
    rows = _read(CSV)
    print(f"compliance matrix: {len(rows)} rows, {dict(Counter(r['status'] for r in rows))}:", "PASS" if not errs else "FAIL")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
