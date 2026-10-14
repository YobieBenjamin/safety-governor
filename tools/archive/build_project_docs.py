#!/usr/bin/env python3
"""Build the consolidated copies of the design documents for the claude.ai Project.

    python3 tools/archive/build_project_docs.py --out build/project \
        --governor . --stack ../hardware-and-silicon --archive-url https://claude.ai/artifact/...

The Project holds text, searchable from every chat in it, so this script joins the Markdown
sources into a small number of documents (one per subject), each opening with a header that
says which repository and commit it came from and where the code, figures and history live.
Image links are rewritten to the archive artifact when --archive-url is given, so the figures
still show. The output names are the Project paths; nothing is uploaded from here.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys

GOVERNOR = [
    ("design/safety-governor-0-repository-guide.md",
     "Safety Governor: repository guide, document index, pass and gap matrix, console",
     ["README.md", "docs/README.md", "results/report.md", "tools/console/README.md"]),
    ("design/safety-governor-1-objectives-architecture-fabric-interfaces.md",
     "Safety Governor design, part 1: objectives, architecture, the safety fabric, interfaces",
     ["docs/00-objectives.md", "docs/01-architecture.md", "docs/02-safety-fabric.md", "docs/03-interfaces.md"]),
    ("design/safety-governor-2-spec-threat-model-register-verification-silicon-analogies.md",
     "Safety Governor design, part 2: specification, threat model, assumptions register, verification plan, silicon plan, analogies",
     ["docs/04-specification.md", "docs/05-threat-model.md", "docs/06-assumptions-register.md",
      "docs/07-verification-plan.md", "docs/08-silicon-plan.md", "docs/09-analogies.md"]),
    ("design/safety-governor-3-plain-english-walkthrough.md",
     "Safety Governor design, part 3: the plain-English walkthrough",
     ["docs/10-plain-english-walkthrough.md"]),
    ("design/safety-governor-4-viability-reach-adoption.md",
     "Safety Governor design, part 4: viability, reach and adoption",
     ["docs/18-viability-and-open-questions.md"]),
    ("design/safety-governor-5-use-cases.md",
     "Safety Governor design, part 5: use cases, catching a bad action before it starts",
     ["docs/17-use-cases.md"]),
    ("design/safety-governor-6-loop-timing-and-evidence-registers.md",
     "Safety Governor design, part 6: the halt loop as a circuit, and the two evidence registers",
     ["docs/11-loop-timing.md", "docs/research/board-lever-register.md", "docs/research/nvswitch-management.md"]),
    ("design/safety-governor-7-hardware-references.md",
     "Safety Governor design, part 7: from Verilog to GDS, rack integration, the loop simulation results, the pinout",
     ["hw/README.md", "hw/pcb/rack-integration.md", "hw/loop/results.md", "hw/pinout/governor_module.csv"]),
    ("design/review-2026-10-audit-findings.md",
     "Audit of the Safety Governor design, October 2026",
     ["docs/AUDIT-2026-10.md"]),
]
STACK = [
    ("blog/a-multi-layer-approach-to-ai-safety.md", None, ["blog/01-a-multi-layer-approach-to-ai-safety.md"]),
    ("blog/the-chip-that-says-no-part-1-plain.md", None, ["blog/02-the-chip-that-says-no-1-plain-english.md"]),
    ("blog/the-chip-that-says-no-part-2-technical.md", None, ["blog/03-the-chip-that-says-no-2-with-the-technical-detail.md"]),
    ("blog/the-chip-that-says-no-part-3-architecture.md", None, ["blog/04-the-chip-that-says-no-3-the-silicon-design.md"]),
    ("blog/the-chip-that-says-no-part-4-governor-in-the-rack.md", None, ["blog/05-the-chip-that-says-no-4-the-governor-in-the-rack.md"]),
    ("design/chip-design-spec.md", None, ["docs/CHIP_DESIGN.md"]),
    ("design/prototyping-plan.md", None, ["docs/PROTOTYPING.md"]),
    ("design/review-2026-10-response.md", None, ["docs/REVIEW-2026-10.md"]),
    ("design/reference-stack-architecture-lanes-nvidia-silicon-threat-model-usage.md",
     "The reference stack: architecture, lanes, NVIDIA, silicon, threat model, usage",
     ["README.md", "docs/ARCHITECTURE.md", "docs/LANES.md", "docs/NVIDIA.md", "docs/SILICON.md",
      "docs/THREAT_MODEL.md", "docs/USAGE.md", "blog/README.md"]),
]


def sh(args: list[str], cwd: str) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def load(repo: str, rel: str) -> str:
    text = open(os.path.join(repo, rel), encoding="utf-8").read().strip("\n")
    if rel.endswith(".csv"):
        rows = [r.split(",") for r in text.splitlines()]
        head = "| " + " | ".join(c.strip() for c in rows[0]) + " |\n|" + "---|" * len(rows[0])
        body = "\n".join("| " + " | ".join(c.strip() for c in r) + " |" for r in rows[1:])
        text = f"# {os.path.basename(rel)}\n\n{head}\n{body}"
    return text


def rewrite_images(text: str, repo_name: str, src_rel: str, archive_url: str | None) -> str:
    """Point relative image links at the archive's copy of the file (the Project holds text only)."""
    if not archive_url:
        return text
    base = os.path.dirname(src_rel)

    def fix(m):
        target = m.group(2)
        if target.startswith(("http://", "https://", "data:")):
            return m.group(0)
        path = os.path.normpath(os.path.join(base, target)).replace(os.sep, "/")
        return f"{m.group(1)}({archive_url.rstrip('/')}/{repo_name}/{path})"

    return re.sub(r"(!\[[^\]]*\])\(([^)\s]+)\)", fix, text)


def demote(text: str) -> str:
    """Push every heading down one level, leaving fenced code alone."""
    out, fenced = [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and re.match(r"^#{1,5} ", line):
            line = "#" + line
        out.append(line)
    return "\n".join(out)


def build(repo: str, repo_name: str, github: str, specs: list, out: str, archive_url: str | None) -> list[str]:
    sha = sh(["git", "rev-parse", "--short", "HEAD"], repo)
    date = sh(["git", "log", "-1", "--format=%cs"], repo)
    written = []
    for path, title, sources in specs:
        bodies = []
        for rel in sources:
            body = rewrite_images(load(repo, rel), repo_name, rel, archive_url)
            if title and len(sources) > 1:
                body = demote(body)                                 # chapters under one title
            bodies.append(body)
        head = (f"# {title}\n\n" if title else "")
        head += (f"> Archived copy of `{repo_name}` at commit `{sha}` ({date}), from "
                 + ", ".join(f"`{s}`" for s in sources) + ". "
                 + (f"Code, tests, figures, the Word files and the full git history are in the archive artifact: {archive_url}. " if archive_url else "")
                 + f"The originals are on GitHub: {github}. Figures, where present, are served from the archive.\n\n")
        text = head + "\n\n---\n\n".join(bodies) + "\n"
        dashes = text.count("—") + text.count("–")
        if dashes:
            print(f"  note: {path} carries {dashes} dash(es) from its sources (older reference-stack text)", file=sys.stderr)
        full = os.path.join(out, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)
        written.append(path)
        print(f"{path}: {len(text.split()):,} words from {len(sources)} file(s)")
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--governor", required=True, help="path of the safety-governor repository")
    ap.add_argument("--stack", required=True, help="path of the hardware-and-silicon repository")
    ap.add_argument("--archive-url", default=None)
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    written = build(args.governor, "safety-governor", "https://github.com/YobieBenjamin/safety-governor", GOVERNOR, out, args.archive_url)
    written += build(args.stack, "hardware-and-silicon", "https://github.com/YobieBenjamin/hardware-and-silicon", STACK, out, args.archive_url)
    for path in written:                                      # self-check: every source file was used, nothing empty
        assert os.path.getsize(os.path.join(out, path)) > 500, path
    print(f"{len(written)} project documents in {out}, built {dt.date.today().isoformat()}")


if __name__ == "__main__":
    main()
