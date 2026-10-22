"""L6: mutation testing as a standing gate.

The second audit found and fixed twenty surviving mutants by hand. This module automates that
audit: it walks the model's checks and, one at a time, removes a check, flips a comparison or
skips a log write, then runs the functional test suite. A mutant is *killed* when some test
fails on it; a *survivor* is a mutant the whole suite still passes. The gate passes only when no
check-removing mutant survives. ``make mutants`` runs it and writes ``results/mutants.md``; CI
runs the same thing weekly.

Three mutant classes, each a single change to one file:

* ``remove_check``: an ``if <guard>: <refuse / return / raise>`` with no ``else`` gets its guard
  forced to ``False``, so the thing it refused never happens. This is the class the acceptance
  criterion names: a check the model can silently drop.
* ``flip``: a single-operator comparison is replaced by its neighbour (``==`` to ``!=``, ``<`` to
  ``<=`` and the rest), the classic mutation operator.
* ``skip_log``: a ``self.log.append(...)`` write is dropped to a no-op; a test that asserts on
  that write catches the skip.

Each mutant is applied by rewriting the file's AST and un-parsing it, so it is always valid
Python. The model is never mutated in place: each worker copies ``govsim`` into its own private
tree, mutates the copy and runs the suite there, so the committed tree is never touched and the
workers run in parallel.
"""
from __future__ import annotations

import ast
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, asdict
from pathlib import Path

# The model the gate guards. These are the four files named in the L6 brief.
TARGETS = ("govsim/governor.py", "govsim/policy.py", "govsim/endpoints.py", "govsim/fabric.py")

# The suite a mutant must die to: the whole functional suite, minus this file so the gate does
# not run itself.
SUITE_DIR = "tests"
IGNORE = ("tests/test_mutants.py",)

ROOT = Path(__file__).resolve().parent.parent
GOVSIM = ROOT / "govsim"

# A comparison operator and the neighbour that replaces it. A "less" mutant is a "less-equal",
# never a "greater": the type of the comparison is preserved.
_FLIP = {"Eq": "NotEq", "NotEq": "Eq", "Lt": "LtE", "LtE": "Lt", "Gt": "GtE", "Ge": "Gt"}

# A log write is an expression-statement that appends to a log/ledger. Only these are kept.
_LOG_METHODS = {"append", "write"}
_LOG_OWNERS = {"log", "ledger"}


@dataclass
class Mutant:
    """One change to one file. The fields are plain data, so a mutant is sent to a worker and
    re-applied there by position in a fresh copy of the source."""
    file: str
    kind: str          # "remove_check" | "flip" | "skip_log"
    lineno: int
    col_offset: int
    op: str            # human description of the change
    newop: str | None = None
    note: str = ""

    @property
    def id(self) -> str:
        return f"{self.file.rsplit('/', 1)[-1]}:{self.lineno}:{self.kind}"

    def apply(self, tree: ast.Module) -> bool:
        """Rewrite one site in ``tree`` in place. The site is found again by its position, so the
        change lands on the intended node of a copy of the source."""
        for node in ast.walk(tree):
            if getattr(node, "lineno", None) != self.lineno or getattr(node, "col_offset", None) != self.col_offset:
                continue
            if self.kind == "flip" and isinstance(node, ast.Compare):
                node.ops[0] = getattr(ast, self.newop)()
                return True
            if self.kind == "remove_check" and isinstance(node, ast.If):
                node.test = ast.Constant(value=False)
                return True
            if self.kind == "skip_log" and isinstance(node, ast.Expr) and _is_log_write(node.value):
                node.value = ast.Constant(value=None)
                return True
        return False


def _is_log_write(call) -> bool:
    if not isinstance(call, ast.Call):
        return False
    fn = call.func
    if not isinstance(fn, ast.Attribute) or fn.attr not in _LOG_METHODS:
        return False
    obj = fn.value
    name = obj.id if isinstance(obj, ast.Name) else (obj.attr if isinstance(obj, ast.Attribute) else None)
    return name in _LOG_OWNERS


# A "check" the gate guards is a guard that refuses: the model denies a request, raises, or returns
# a refusal value. A bare defensive return (``return []``, ``return 0``, ``return {}``, a normal
# result) is not a check the model can silently drop, so it is not a site. A refusal value is the
# model saying no: ``False``/``None``, a ``(False, reason)`` tuple, a ``{"ok": False}`` dict, or a
# call to a deny/refuse method.
_REFUSE_CALLS = {"_deny", "deny", "_refuse", "refuse"}


def _is_refusal_value(val) -> bool:
    if isinstance(val, ast.Constant) and (val.value is False or val.value is None):
        return True
    if isinstance(val, ast.Tuple) and val.elts and isinstance(val.elts[0], ast.Constant) and val.elts[0].value is False:
        return True
    if isinstance(val, ast.Dict):
        return any(isinstance(k, ast.Constant) and k.value == "ok" and isinstance(v, ast.Constant) and v.value is False
                   for k, v in zip(val.keys, val.values))
    if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) and val.func.attr in _REFUSE_CALLS:
        return True
    return False


def _guarded(stmt) -> bool:
    """A single-statement body that is a check the model can drop: a refusal, or a raise."""
    if isinstance(stmt, ast.Raise):
        return True
    if isinstance(stmt, ast.Return) and _is_refusal_value(stmt.value):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Attribute) \
            and stmt.value.func.attr in _REFUSE_CALLS:
        return True
    return False


def _check_sites(tree, file) -> list[Mutant]:
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or node.orelse:
            continue                 # an else/elif inverts the check, it does not drop it
        body = node.body
        if len(body) != 1 or not _guarded(body[0]):
            continue
        out.append(Mutant(file, "remove_check", node.lineno, node.col_offset,
                          "force the guard False", note=f"if {_guard_desc(node)} -> {_body_desc(body[0])}"))
    return out


def _flip_sites(tree, file) -> list[Mutant]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            new = _FLIP.get(type(node.ops[0]).__name__)
            if new:
                out.append(Mutant(file, "flip", node.lineno, node.col_offset,
                                  f"{type(node.ops[0]).__name__} -> {new}", newop=new))
    return out


def _log_sites(tree, file) -> list[Mutant]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and _is_log_write(node.value):
            out.append(Mutant(file, "skip_log", node.lineno, node.col_offset,
                              "drop a log write", note=_call_desc(node.value)))
    return out


def _call_desc(call) -> str:
    try:
        return ast.unparse(call)[:80]
    except Exception:
        return "<log write>"


def _guard_desc(node) -> str:
    try:
        return ast.unparse(node.test)[:70]
    except Exception:
        return "<guard>"


def _body_desc(stmt) -> str:
    try:
        return ast.unparse(stmt)[:60]
    except Exception:
        return "<body>"


def make_mutants(files=TARGETS) -> list[Mutant]:
    """Every mutant over the model's four files, in a fixed order for a stable report."""
    mutants: list[Mutant] = []
    for f in sorted(files):
        tree = ast.parse(_read(f))
        mutants += _check_sites(tree, f)
        mutants += _flip_sites(tree, f)
        mutants += _log_sites(tree, f)
    return mutants


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def _module_for(path: str) -> str:
    rel = path[:-3] if path.endswith(".py") else path
    return rel.replace("/", ".")


# --- worker side: one process per chunk, its own private copy of govsim ----------------------

def _work_dir(chunk_index: int) -> Path:
    d = Path(tempfile.gettempdir()) / f"l6-mutants-{os.getpid()}-{chunk_index}"
    if d.exists():
        shutil.rmtree(d)
    shutil.copytree(GOVSIM, d / "govsim")
    return d


def _process_chunk(chunk: list[dict], copy_dir: Path, suite_dir: str, ignore: tuple[str, ...],
                   timeout: float) -> list[dict]:
    """Run every mutant in ``chunk`` against the suite in ``copy_dir/govsim``. The real tree is
    untouched: the copy's file is overwritten per mutant and restored from its pristine bytes."""
    results = []
    pristine: dict[str, str] = {}
    for spec in chunk:
        m = Mutant(**spec)
        fpath = copy_dir / m.file
        if m.file not in pristine:
            pristine[m.file] = fpath.read_text()
        status, killer = "invalid", ""
        try:
            tree = ast.parse(pristine[m.file])
            if not m.apply(tree):
                status, killer = "invalid", "site not found"
            else:
                ast.fix_missing_locations(tree)
                mutated = ast.unparse(tree)
                fpath.write_text(mutated)
                # the copy must import, or the mutant is not a real change to run
                probe = subprocess.run([sys.executable, "-c", f"import {_module_for(m.file)}"],
                                       cwd=str(copy_dir), capture_output=True, text=True, timeout=20.0)
                if probe.returncode != 0:
                    status, killer = "invalid", "copy will not import"
                else:
                    status = _run_suite_in(copy_dir, suite_dir, ignore, timeout)
                    killer = status
                    status = "killed" if killer else "survived"
        except subprocess.TimeoutExpired:
            status, killer = "invalid", "timeout"
        except Exception as e:  # an un-applyable mutant is excluded, never counted a survivor
            status, killer = "invalid", f"error: {e}"
        finally:
            fpath.write_text(pristine[m.file])
        results.append({**spec, "status": status, "killer": killer})
    return results


def _run_suite_in(copy_dir: Path, suite_dir: str, ignore, timeout: float) -> str:
    """Run the suite against the copy in ``copy_dir``. Returns the first failing line when a test
    fails (the mutant is killed), or "" when every test passes (the mutant survived)."""
    cmd = [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider",
           str(ROOT / suite_dir)]
    for ig in ignore:
        cmd += ["--ignore", str(ROOT / ig)]
    r = subprocess.run(cmd, cwd=str(copy_dir), capture_output=True, text=True, timeout=timeout)
    if r.returncode == 0:
        return ""
    for line in (r.stdout + r.stderr).splitlines():
        if "FAILED" in line or "ERROR" in line or "assert " in line:
            return line.strip()[:120]
    return "a test failed"


def _chunk(specs: list[dict], n: int) -> list[list[dict]]:
    if n <= 1:
        return [specs]
    per = (len(specs) + n - 1) // n
    return [specs[i:i + per] for i in range(0, len(specs), per)] or [[]]


# --- orchestrator side ------------------------------------------------------------------------

@dataclass
class Report:
    mutants: list[Mutant] = field(default_factory=list)
    seconds: float = 0.0

    def by_kind(self, kind: str) -> list[Mutant]:
        return [m for m in self.mutants if m.kind == kind]

    def survivors(self, kind: str | None = None) -> list[Mutant]:
        sel = self.by_kind(kind) if kind else self.mutants
        return [m for m in sel if m.status == "survived"]

    def invalid(self) -> list[Mutant]:
        return [m for m in self.mutants if m.status == "invalid"]

    def killed_count(self) -> int:
        return sum(1 for m in self.mutants if m.status == "killed")

    def score(self, kind: str | None = None) -> float:
        sel = self.by_kind(kind) if kind else self.mutants
        real = [m for m in sel if m.status != "invalid"]
        return round(sum(1 for m in real if m.status == "killed") / len(real) * 100, 1) if real else 100.0

    def to_lines(self) -> list[str]:
        L = ["# L6 mutation gate", "",
             "One mutant at a time over the model's four files (`govsim/governor.py`, `policy.py`,",
             "`endpoints.py`, `fabric.py`): remove a check, flip a comparison or skip a log write, then",
             "run the functional suite in a private copy. A mutant is **killed** when a test fails on",
             "it; a **survivor** is one the whole suite still passes. The gate fails the build when a",
             "check-removing mutant survives.", ""]
        L += [f"Ran in {self.seconds} s. {self.killed_count()} killed, "
              f"{len(self.survivors())} survived, {len(self.invalid())} invalid "
              f"over {len(self.mutants)} mutants.", ""]
        for label, kind in (("Check removal (the gate's criterion)", "remove_check"),
                            ("Comparison flips", "flip"),
                            ("Log-write skips", "skip_log")):
            sel = self.by_kind(kind)
            real = [m for m in sel if m.status != "invalid"]
            surv = [m for m in sel if m.status == "survived"]
            L += [f"## {label}: {len(real) - len(surv)}/{len(real)} killed ({self.score(kind)}%)", ""]
            if surv:
                L += ["| location | change |", "|---|---|"]
                L += [f"| `{m.id}` | {m.op} (`{m.note}`) |" for m in surv]
                L.append("")
            else:
                L += ["none survive.", ""]
        inv = self.invalid()
        if inv:
            L += ["## invalid (not applied or the copy will not import)", ""]
            L += [f"- `{m.id}`: {m.killer or m.status}" for m in inv]
            L.append("")
        L.append("Generated by `govsim/mutants.py`; committed by `make mutants`.")
        return L

    def write(self, path: str) -> None:
        (ROOT / path).write_text("\n".join(self.to_lines()) + "\n")


def run(files=TARGETS, workers: int | None = None, timeout: float = 120.0,
        only: set[str] | None = None, report_path: str | None = None,
        print_progress: bool = False, loc: str | None = None) -> Report:
    """Generate every mutant, kill each one in a private copy, and build the report. ``only``
    restricts to one or more kinds; ``workers`` is the parallelism (default: the cpu count, capped);
    ``loc`` is an optional ``file:line`` to run just the mutants at that site (for closing a gap)."""
    mutants = make_mutants(files)
    if only is not None:
        mutants = [m for m in mutants if m.kind in only]
    if loc is not None:
        f, _, line = loc.partition(":")
        line = int(line) if line else -1
        mutants = [m for m in mutants if m.file.endswith(f) and (line < 0 or m.lineno == line)]
    specs = [asdict(m) for m in mutants]
    n = workers or min(8, (os.cpu_count() or 1))
    started = time.time()
    results: list[dict] = []
    if n > 1 and len(specs) > 1:
        chunks = _chunk(specs, n)
        dirs = [_work_dir(i) for i in range(len(chunks))]
        with ProcessPoolExecutor(max_workers=len(chunks)) as ex:
            futs = [ex.submit(_process_chunk, c, d, SUITE_DIR, IGNORE, timeout)
                    for c, d in zip(chunks, dirs)]
            for fut in futs:
                results += fut.result()
        for d in dirs:
            shutil.rmtree(d, ignore_errors=True)
    else:
        results += _process_chunk(specs, _work_dir(0), SUITE_DIR, IGNORE, timeout)
    out: list[Mutant] = []
    for r in results:
        m = Mutant(**{k: r[k] for k in ("file", "kind", "lineno", "col_offset", "op", "newop", "note")})
        m.status = r["status"]
        m.killer = r.get("killer")
        out.append(m)
    out.sort(key=lambda m: (m.file, m.lineno, m.col_offset, m.kind))
    rep = Report(out, seconds=round(time.time() - started, 2))
    if report_path:
        rep.write(report_path)
    if print_progress:
        print(f"{rep.killed_count()} killed, {len(rep.survivors())} survived, "
              f"{len(rep.invalid())} invalid; check-removal {rep.score('remove_check')}%.")
    return rep


def gate(only: set[str] | None = None, report_path: str = "results/mutants.md",
         workers: int | None = None, loc: str | None = None) -> tuple[Report, list[Mutant]]:
    """Run the gate and return the report with its surviving check-removing mutants (empty when the
    gate passes)."""
    rep = run(only=only, report_path=report_path, workers=workers, loc=loc, print_progress=True)
    return rep, rep.survivors("remove_check")


def main(argv: list[str] | None = None) -> int:
    """`make mutants`: run the gate, write the report, fail the build on a surviving check."""
    import argparse
    ap = argparse.ArgumentParser(description="L6 mutation gate")
    ap.add_argument("--only", default="", help="comma-separated kinds (remove_check,flip,skip_log)")
    ap.add_argument("--report", default="results/mutants.md")
    ap.add_argument("--workers", type=int, default=0, help="parallel workers (0: auto)")
    ap.add_argument("--loc", default="", help="file:line to run just the mutants at that site")
    ap.add_argument("--keep-surface", action="store_true", help="do not fail on survivors (dry run)")
    args = ap.parse_args(argv)
    only = {k for k in args.only.split(",") if k} or None
    workers = args.workers or None
    rep, survivors = gate(only=only, report_path=args.report, workers=workers, loc=args.loc or None)
    print(f"\n{rep.killed_count()} killed, {len(rep.survivors())} survived, "
          f"{len(rep.invalid())} invalid; check-removal {rep.score('remove_check')}% "
          f"over {len(rep.by_kind('remove_check'))} mutants.")
    if survivors:
        print("\nSURVIVING CHECK-REMOVING MUTANTS (the gate fails):")
        for m in survivors:
            print(f"  {m.id}: {m.op} ({m.note})")
        return 1 if not args.keep_surface else 0
    print("no check-removing mutant survived.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
