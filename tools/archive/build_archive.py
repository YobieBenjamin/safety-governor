#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Stage a complete, browsable archive of the program's repositories for publishing on claude.ai.

One command, self-checking:

    python3 tools/archive/build_archive.py --out build/archive \
        --repo ../safety-governor --repo ../hardware-and-silicon

For every repository it copies each tracked file into <out>/<repo>/<path>, writes a full
git bundle of all refs (split into parts under the artifact's per-file limit when the history
is large), zips the tracked working tree, and then renders <out>/index.html: a static page
listing every file with a link, the commit each repository is at, the bundles, and the
restore procedure. <out>/manifest.json records all of it and <out>/publish-files.json is the
file list to hand to the publisher (published path and media type for every file).

The page is static on purpose: no store, no script beyond a filter box, nothing that can
go stale on its own. The archive is the point; the page is its table of contents.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import shutil
import subprocess
import sys
import zipfile

BINARY_LIMIT = 15 * 1024 * 1024          # the publisher's limit for one binary file
BUNDLE_TARGET = 13 * 1024 * 1024         # aim under the limit; bundles compress differently from packs
TEXT = "text/plain"
# the publisher serves these extensions; a document or archive (.docx, .zip, a git bundle) is not
# served, so bundles go up as base64 text and Word files travel inside the bundles
SERVED = {".html", ".css", ".js", ".mjs", ".wasm", ".json", ".map", ".geojson", ".webmanifest", ".txt", ".md",
          ".csv", ".xml", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico", ".woff", ".woff2",
          ".ttf", ".otf", ".mp3", ".wav", ".ogg", ".mp4", ".webm", ".pdf"}
TYPES = {
    ".md": TEXT, ".py": TEXT, ".v": TEXT, ".sv": TEXT, ".csv": TEXT, ".toml": TEXT, ".sh": TEXT,
    ".yml": TEXT, ".yaml": TEXT, ".txt": TEXT, ".cff": TEXT, ".html": TEXT, ".js": TEXT, ".cfg": TEXT,
    ".ini": TEXT, ".lock": TEXT, ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".bundle": "application/octet-stream", ".zip": "application/zip",
}
DESCRIPTIONS = {
    "safety-governor": "The Safety Governor chip: design documents, the functional model and its hypothesis tests, the RTL blocks, the silicon flow, the halt-loop circuit, the use cases, the audit and the master document.",
    "hardware-and-silicon": "The reference stack the governor enforces in hardware, and the blog series The Chip That Says No, parts 1 to 4, with their figures and the Word files.",
}


def sh(args: list[str], cwd: str | None = None) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def media_type(path: str) -> str:
    base = os.path.basename(path)
    ext = os.path.splitext(base)[1].lower()
    if ext in TYPES:
        return TYPES[ext]
    return TEXT                       # Makefile, LICENSE, NOTICE, .gitignore and the like


def served(path: str) -> bool:
    ext = os.path.splitext(os.path.basename(path))[1].lower()
    return ext in SERVED or ext == "" or media_type(path) == TEXT


def human(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / 1024 / 1024:.1f} MB"


def repo_info(repo: str) -> dict:
    name = os.path.basename(os.path.abspath(repo))
    dirty = sh(["git", "status", "--porcelain"], repo)
    sha = sh(["git", "rev-parse", "HEAD"], repo)
    date = sh(["git", "log", "-1", "--format=%ci"], repo)
    subject = sh(["git", "log", "-1", "--format=%s"], repo)
    branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
    count = int(sh(["git", "rev-list", "--count", "--all"], repo))
    refs = sh(["git", "for-each-ref", "--format=%(refname:short) %(objectname:short)", "refs/heads", "refs/tags"], repo)
    files = sh(["git", "ls-files", "-z"], repo).split("\0")
    files = [f for f in files if f]
    return {"name": name, "path": os.path.abspath(repo), "sha": sha, "short": sha[:7], "date": date, "subject": subject,
            "branch": branch, "commits": count, "refs": refs.splitlines(), "files": files, "dirty": bool(dirty),
            "github": f"https://github.com/YobieBenjamin/{name}"}


def copy_tree(info: dict, out: str) -> list[dict]:
    rows = []
    for rel in info["files"]:
        src = os.path.join(info["path"], rel)
        dst = os.path.join(out, info["name"], rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        rows.append({"path": f"{info['name']}/{rel}", "bytes": os.path.getsize(src), "type": media_type(rel), "served": served(rel)})
    return rows


def bundle_segments(repo: str) -> list[tuple[str | None, str]]:
    """Cut the first-parent history of HEAD into segments whose object size stays under the
    target, so each bundle lands under the per-file limit. Returns (start, end) pairs; start
    None means from the root."""
    commits = sh(["git", "rev-list", "--reverse", "--first-parent", "HEAD"], repo).splitlines()
    segments, start, prev = [], None, None
    for c in commits:
        rng = c if start is None else f"{start}..{c}"
        size = int(sh(["git", "rev-list", "--objects", "--disk-usage", rng], repo))
        if size > BUNDLE_TARGET and prev is not None and prev != start:
            segments.append((start, prev))
            start = prev
        prev = c
    segments.append((start, commits[-1]))
    return segments


def as_text(bundle_path: str) -> tuple[str, int]:
    """The publisher serves text, not archives: write the bundle as base64 lines beside it."""
    import base64
    txt = bundle_path + ".txt"
    with open(bundle_path, "rb") as src, open(txt, "w", encoding="ascii") as dst:
        data = base64.b64encode(src.read()).decode("ascii")
        dst.write("\n".join(data[i:i + 76] for i in range(0, len(data), 76)) + "\n")
    return txt, os.path.getsize(txt)


def make_bundles(info: dict, out: str) -> list[dict]:
    repo, name = info["path"], info["name"]
    bdir = os.path.join(out, "bundles")
    os.makedirs(bdir, exist_ok=True)
    rows = []
    whole = os.path.join(bdir, f"{name}-all.bundle")
    subprocess.run(["git", "bundle", "create", whole, "--all", "HEAD"], cwd=repo, check=True, capture_output=True)
    if os.path.getsize(whole) <= BINARY_LIMIT:
        subprocess.run(["git", "bundle", "verify", whole], cwd=repo, check=True, capture_output=True)
        txt, tbytes = as_text(whole)
        rows.append({"path": f"bundles/{name}-all.bundle", "bytes": os.path.getsize(whole), "type": TYPES[".bundle"],
                     "text": f"bundles/{name}-all.bundle.txt", "text_bytes": tbytes,
                     "refs": "all branches and tags, with HEAD", "requires": None,
                     "restore": f"git clone {name}-all.bundle {name}"})
        return rows
    os.unlink(whole)
    segments = bundle_segments(repo)
    for i, (start, end) in enumerate(segments, 1):
        part = os.path.join(bdir, f"{name}-part{i}.bundle")
        ref = f"refs/archive/part{i}"
        subprocess.run(["git", "update-ref", ref, end], cwd=repo, check=True)
        try:
            args = ["git", "bundle", "create", part, ref] + ([f"^{start}"] if start else [])
            subprocess.run(args, cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "bundle", "verify", part], cwd=repo, check=True, capture_output=True)
        finally:
            subprocess.run(["git", "update-ref", "-d", ref], cwd=repo, check=True)
        size = os.path.getsize(part)
        if size > BINARY_LIMIT:
            sys.exit(f"{part} is {human(size)}, over the per-file limit; lower BUNDLE_TARGET")
        last = i == len(segments)
        txt, tbytes = as_text(part)
        rows.append({"path": f"bundles/{name}-part{i}.bundle", "bytes": size, "type": TYPES[".bundle"],
                     "text": f"bundles/{name}-part{i}.bundle.txt", "text_bytes": tbytes,
                     "refs": f"{(start or 'root')[:7]}..{end[:7]} of {info['branch']}, as {ref}",
                     "requires": f"part {i - 1}" if start else None,
                     "restore": (f"git init {name} && git -C {name} fetch ../{name}-part1.bundle {ref}:refs/heads/{info['branch']}" if i == 1
                                 else f"git -C {name} fetch ../{name}-part{i}.bundle +{ref}:refs/heads/{info['branch']}")
                                + (f" && git -C {name} checkout {info['branch']}" if last else "")})
    return rows


def make_zip(info: dict, out: str) -> dict:
    zdir = os.path.join(out, "zips")
    os.makedirs(zdir, exist_ok=True)
    name = f"{info['name']}-{info['short']}.zip"
    dst = os.path.join(zdir, name)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in info["files"]:
            z.write(os.path.join(info["path"], rel), f"{info['name']}/{rel}")
    return {"path": f"zips/{name}", "bytes": os.path.getsize(dst), "type": TYPES[".zip"]}


def group(rows: list[dict], name: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        rel = r["path"][len(name) + 1:]
        top = rel.split("/")[0] if "/" in rel else "(top level)"
        if rel.count("/") >= 2:
            top = "/".join(rel.split("/")[:2])
        groups.setdefault(top, []).append(dict(r, rel=rel))
    return dict(sorted(groups.items(), key=lambda kv: (kv[0] == "(top level)", kv[0])))


def render(out: str, repos: list[dict], console_url: str, built: str) -> str:
    e = html.escape
    parts = []
    for info in repos:
        files = info["rows"]
        total = sum(r["bytes"] for r in files)
        bundles = "".join(
            f'<li><a href="{e(b["text"])}">{e(os.path.basename(b["text"]))}</a> <span class="n">{human(b["text_bytes"])} as text, {human(b["bytes"])} decoded</span>'
            f'<span class="d">git bundle, {e(b["refs"])}{"; needs " + e(b["requires"]) if b["requires"] else ""}; base64 text because the page cannot serve an archive</span></li>'
            for b in info["bundles"])
        z = info["zip"]
        groups = group(files, info["name"])
        tree = "".join(
            f'<details open><summary><span class="dir">{e(top)}</span><span class="n">{len(rows)} files</span></summary><ul class="files">'
            + "".join((f'<li data-f="{e(r["rel"].lower())}"><a href="{e(r["path"])}">{e(r["rel"])}</a><span class="n">{human(r["bytes"])}</span></li>' if r["served"]
                       else f'<li data-f="{e(r["rel"].lower())}"><span class="unlinked">{e(r["rel"])}</span><span class="n">{human(r["bytes"])} · inside the bundle</span></li>') for r in rows)
            + "</ul></details>"
            for top, rows in groups.items())
        parts.append(f"""
  <section class="repo" id="{e(info['name'])}">
    <div class="repo-head">
      <h2>{e(info['name'])}</h2>
      <p class="lede">{e(DESCRIPTIONS.get(info['name'], ''))}</p>
      <dl class="facts">
        <div><dt>Commit</dt><dd><code>{e(info['short'])}</code> on <code>{e(info['branch'])}</code>, {e(info['date'][:10])}</dd></div>
        <div><dt>Last change</dt><dd>{e(info['subject'])}</dd></div>
        <div><dt>History</dt><dd>{info['commits']} commits, {len(files)} tracked files, {human(total)}</dd></div>
        <div><dt>Origin</dt><dd><a href="{e(info['github'])}">{e(info['github'].replace('https://', ''))}</a></dd></div>
      </dl>
      <h3>Whole repository</h3>
      <ul class="plain">
        {bundles}
        <li><span class="unlinked">{e(os.path.basename(z['path']))}</span> <span class="n">{human(z['bytes'])}</span><span class="d">the tracked files at this commit as a zip; sent to the conversation and kept on the Mac, not servable from this page</span></li>
      </ul>
    </div>
    <h3>Every file</h3>
    <div class="tree">{tree}</div>
  </section>""")
    bundle_names = [os.path.basename(b["path"]) for info in repos for b in info["bundles"]]
    restore = "\n".join(
        f"base64 -d {n}.txt > {n}" for n in bundle_names) + "\n" + "\n".join(
        b["restore"] for info in repos for b in info["bundles"]) + "\n" + "\n".join(
        f"git -C {info['name']} bundle verify ../{os.path.basename(b['path'])}   # verify needs a repository to run in"
        for info in repos for b in info["bundles"]) + "\ncd safety-governor && python3 -m pytest -q tests rtl/tests   # 200 + 20 tests"
    return f"""<title>Governor Program Archive</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
  /* Layout: a manifest. Two repository sections, each a facts list, the whole-repository files, then a file tree with sizes. */
  :root {{
    --bg: #f5f6f4; --panel: #ffffff; --fg: #1d2420; --muted: #5c655f; --line: #d6dbd6; --accent: #1f5f8b; --accent-bg: #e6eff5;
    --font-body: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
    --font-mono: "IBM Plex Mono", "SFMono-Regular", Menlo, Consolas, monospace;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{ --bg: #121614; --panel: #1a201d; --fg: #e6ebe7; --muted: #9aa49d; --line: #2e3733; --accent: #7fb4dc; --accent-bg: #1c2a35; color-scheme: dark; }}
  }}
  :root[data-theme="dark"] {{ --bg: #121614; --panel: #1a201d; --fg: #e6ebe7; --muted: #9aa49d; --line: #2e3733; --accent: #7fb4dc; --accent-bg: #1c2a35; color-scheme: dark; }}
  body {{ background: var(--bg); color: var(--fg); font-family: var(--font-body); font-size: 15px; line-height: 1.45; }}
  .wrap {{ max-width: 880px; margin: 0 auto; padding-block: 20px 48px; padding-inline: 16px; display: grid; gap: 28px; }}
  h1 {{ font-size: 21px; font-weight: 600; margin: 0 0 6px; text-wrap: balance; }}
  h2 {{ font-size: 18px; font-weight: 600; margin: 0; font-family: var(--font-mono); }}
  h3 {{ font-size: 12.5px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); margin: 18px 0 8px; }}
  p {{ margin: 0; max-width: 68ch; }}
  .lede {{ color: var(--muted); }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover, a:focus-visible {{ text-decoration: underline; outline: none; }}
  code {{ font-family: var(--font-mono); font-size: 0.92em; }}
  .head {{ border-bottom: 1px solid var(--line); padding-bottom: 16px; display: grid; gap: 8px; }}
  .meta {{ font-family: var(--font-mono); font-size: 12.5px; color: var(--muted); font-variant-numeric: tabular-nums; }}
  .repo {{ background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px; min-width: 0; }}
  .facts {{ display: grid; gap: 4px 0; margin: 12px 0 0; }}
  .facts div {{ display: grid; grid-template-columns: 96px 1fr; gap: 10px; min-width: 0; }}
  .facts dt {{ color: var(--muted); font-size: 13px; }}
  .facts dd {{ margin: 0; min-width: 0; overflow-wrap: anywhere; }}
  ul.plain {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }}
  ul.plain li {{ display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; min-width: 0; }}
  .n {{ font-family: var(--font-mono); font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .d {{ color: var(--muted); font-size: 13px; flex-basis: 100%; }}
  .filter {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
  .filter input {{ font: inherit; padding: 6px 10px; border: 1px solid var(--line); border-radius: 4px; background: var(--panel); color: var(--fg); min-width: 0; width: min(100%, 320px); }}
  .filter input:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 1px; }}
  .tree details {{ border-top: 1px solid var(--line); padding: 6px 0; }}
  .tree details:first-child {{ border-top: 0; }}
  .tree summary {{ cursor: pointer; display: flex; justify-content: space-between; gap: 10px; align-items: baseline; list-style: none; }}
  .tree summary::-webkit-details-marker {{ display: none; }}
  .tree summary::before {{ content: "+"; font-family: var(--font-mono); color: var(--muted); margin-right: 8px; }}
  .tree details[open] summary::before {{ content: "-"; }}
  .dir {{ font-family: var(--font-mono); font-weight: 500; flex: 1; min-width: 0; }}
  ul.files {{ list-style: none; margin: 4px 0 2px; padding: 0 0 0 20px; display: grid; gap: 2px; }}
  ul.files li {{ display: flex; justify-content: space-between; gap: 10px; min-width: 0; }}
  ul.files li a, .unlinked {{ font-family: var(--font-mono); font-size: 13px; min-width: 0; overflow-wrap: anywhere; }}
  .unlinked {{ color: var(--muted); }}
  ul.files li.hide, .tree details.hide {{ display: none; }}
  pre {{ background: var(--accent-bg); border-radius: 6px; padding: 12px 14px; overflow-x: auto; font-family: var(--font-mono); font-size: 12.5px; line-height: 1.6; margin: 0; }}
  .note {{ display: grid; gap: 10px; }}
  .note p {{ max-width: 72ch; }}
  .foot {{ color: var(--muted); font-size: 12.5px; }}
</style>
<div class="wrap">
  <div class="head">
    <div>
      <h1>Governor Program Archive</h1>
      <p class="lede">Every file of the two repositories, the full history of each as git bundles, the tracked trees as zip files, and the master documents. Kept on claude.ai so the work does not depend on any one place.</p>
    </div>
    <div class="meta">built {e(built)} · plan of record: rack tier, the governor on the OEM's management-module card · <a href="{e(console_url)}">program console</a></div>
    <div class="filter"><label for="q" class="meta">filter files</label><input id="q" type="search" placeholder="e.g. governor.py, loop, docs/17" autocomplete="off"></div>
  </div>
{''.join(parts)}
  <section class="note">
    <h3>Restoring a repository from this page</h3>
    <p>A bundle is a complete copy of a repository's history in one file. This page serves it as base64 text, because it cannot serve an archive directly. Save the text to a computer with git, decode it, clone it, then verify it from inside the clone. A repository that needed more than one part is cloned from part 1 and the later parts are fetched into it in order.</p>
    <pre>{e(restore)}</pre>
    <p>A future Claude session can read any file here, bundles included, straight from this archive, so the repositories can be rebuilt from here even when GitHub is not reachable.</p>
    <h3>Where the rest lives</h3>
    <p>The Project "Hardware and Silicon" on claude.ai holds the design documents, the use cases, the viability write-up, the audit, the blog series and the reference-stack documents as searchable text. The live program console is linked above. GitHub holds the originals under the account YobieBenjamin.</p>
  </section>
  <div class="foot">Yobie Benjamin · yobie AT ieee DOT org · linkedin.com/in/yobie</div>
</div>
<script>
(function () {{
  var q = document.getElementById("q");
  if (!q) return;
  q.addEventListener("input", function () {{
    var s = q.value.trim().toLowerCase();
    document.querySelectorAll(".tree details").forEach(function (d) {{
      var any = false;
      d.querySelectorAll("li[data-f]").forEach(function (li) {{
        var show = !s || li.getAttribute("data-f").indexOf(s) >= 0;
        li.classList.toggle("hide", !show);
        any = any || show;
      }});
      d.classList.toggle("hide", !any);
      if (s && any) d.open = true;
    }});
  }});
}})();
</script>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", action="append", required=True, help="repository path; repeat for each")
    ap.add_argument("--console-url", default="https://claude.ai/artifact/K1qH4rHMPmWJ7neSW8pitb")
    ap.add_argument("--allow-dirty", action="store_true")
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    repos = []
    for repo in args.repo:
        info = repo_info(repo)
        if info["dirty"] and not args.allow_dirty:
            sys.exit(f"{info['name']} has uncommitted changes; commit first or pass --allow-dirty")
        info["rows"] = copy_tree(info, out)
        info["bundles"] = make_bundles(info, out)
        info["zip"] = make_zip(info, out)
        repos.append(info)
        print(f"{info['name']}: {len(info['rows'])} files at {info['short']}, "
              f"{', '.join(os.path.basename(b['path']) + ' ' + human(b['bytes']) for b in info['bundles'])}, zip {human(info['zip']['bytes'])}")
    built = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = render(out, repos, args.console_url, built)
    assert "\u2014" not in page and "\u2013" not in page, "no dashes of that kind in the page"
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    publish = [{"path": "index.html"}]
    for info in repos:
        publish += [{"path": r["path"], "contentType": r["type"]} for r in info["rows"] if r["served"]]
        publish += [{"path": b["text"], "contentType": TEXT} for b in info["bundles"]]
    # the publisher takes at most 255 files in one call: split the list into pages
    pages = [publish[i:i + 255] for i in range(0, len(publish), 255)]
    for i, p in enumerate(pages, 1):
        with open(os.path.join(out, f"publish-files-{i}.json"), "w", encoding="utf-8") as fh:
            json.dump(p, fh, separators=(",", ":"))
    manifest = {"built": built, "repos": [{k: v for k, v in r.items() if k != "files"} for r in repos],
                "files": len(publish), "bytes": sum(os.path.getsize(os.path.join(out, p["path"])) for p in publish)}
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    # self-check: every listed file exists, every file is under its limit, the page is under 16 MB
    for p in publish:
        full = os.path.join(out, p["path"])
        assert os.path.isfile(full), full
        assert os.path.getsize(full) <= 16 * 1024 * 1024, (full, os.path.getsize(full))
        assert served(p["path"]) or p["path"].endswith(".txt"), p
    assert os.path.getsize(os.path.join(out, "index.html")) < 16 * 1024 * 1024
    print(f"{len(publish)} files to publish in {len(pages)} call(s), {human(manifest['bytes'])}; page {human(os.path.getsize(os.path.join(out, 'index.html')))}; wrote {out}")


if __name__ == "__main__":
    main()
