# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""The capstone: one command that runs the whole proof and emits one bit.

    python -m govsim.prove            # run everything, print VERDICT: 1 or VERDICT: 0
    python -m govsim.prove --write     # also write results/PROOF.md and results/proof-manifest.json
    python -m govsim.prove --quick     # skip the full pytest sweep (everything else still runs)

This is the artifact that turns "I have a simulation" into "here is a proof you can run yourself and
cannot break." It runs every layer of evidence and collapses them to a single verdict:

    VERDICT = 1  iff  no component failed
    VERDICT = 0  otherwise

The layers:
  - red-team self-test : the oracle returns 0 on a deliberately broken gate (proves it is not vacuous)
  - red team           : one protected action, every attack the audit named, must all be repelled
  - formal proofs      : the abstract-machine invariants, the commit point, the min-cut argument
  - RTL conformance    : the RTL differential-conformance suite
  - RTL formal         : the RTL formal properties with planted mutants (needs yowasp-yosys)
  - experiments        : EXPERIMENT-ORIGIN-GATE, EXPERIMENT-CONTAINMENT, EXPERIMENT-ROAD-REACHABILITY, EXPERIMENT-CUSTOMER-CONFIRMATION
  - discriminating tests: the pytest suite, every fix with a test that fails before and passes after

A component needing a toolchain that is absent (RTL formal without yowasp-yosys) is recorded as
skipped, not passed, and the manifest says whether the verdict is full or software-only. A skipped
component never counts as a pass; a failed one forces VERDICT 0. The manifest is dated and pinned to
the exact commit, so the verdict is reproducible and a reviewer can rerun it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def have_yosys() -> bool:
    """True when the yowasp-yosys package imports. That package is the RTL formal toolchain. The import is only a
    presence check. When the package is absent, the RTL formal component is recorded as skipped, never as a pass."""
    try:
        import yowasp_yosys  # noqa: F401  (only checks that the package can be imported)
        return True
    except Exception:
        return False


# (key, description, argv, needs_yosys)
def components(quick: bool):
    """The components the proof runs, as (key, description, command, needs_yosys) tuples. The pytest sweep is added unless
    ``quick`` is set. Output: the list."""
    c = [
        ("redteam-selftest", "the red-team oracle returns 0 on a broken gate (non-vacuous)", [sys.executable, "-m", "govsim.redteam", "--selftest"], False),
        ("redteam", "capstone: one protected action, every attack the audit named", [sys.executable, "-m", "govsim.redteam"], False),
        ("proofs-core", "abstract-machine invariants (P0..P14, non-vacuity)", [sys.executable, "proofs/core_invariants.py"], False),
        ("proofs-commit", "the commit-point proof", [sys.executable, "proofs/commit_point.py"], False),
        ("proofs-killswitch", "no global kill switch / corrected min-cut", [sys.executable, "proofs/no_global_kill_switch.py"], False),
        ("conformance", "RTL differential-conformance suite", [sys.executable, "-m", "rtl.conformance"], False),
        ("rtl-formal", "RTL formal properties with planted mutants", [sys.executable, "-m", "rtl.formal"], True),
        ("exp-origin-gate", "W1: the origin gate (no key, no model)", [sys.executable, "-m", "govsim.origin_gate"], False),
        ("exp-containment", "P3b: containment measurement", [sys.executable, "-m", "govsim.containment"], False),
        ("exp-road", "A1: rulebook reachability audit", [sys.executable, "-m", "govsim.road_reachability"], False),
        ("exp-customer", "I1: the payer's own-key confirmation", [sys.executable, "-m", "govsim.customer_confirm"], False),
    ]
    if not quick:
        c.append(("unit-tests", "the discriminating test suite (fail-before, pass-after)", [sys.executable, "-m", "pytest", "-q"], False))
    return c


def git_commit() -> str:
    """The commit hash of this checkout, for the manifest. Returns "unknown" if git cannot be run."""
    try:
        return subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def run_component(key, desc, argv, needs_yosys, yosys_ok) -> dict:
    """Run one component as a subprocess from the repository root. Output: a record with its status. It is ``pass`` when
    the exit code is 0 and ``fail`` otherwise, including a timeout after 30 minutes or a crash. It is ``skipped`` when the
    component needs yosys and yosys is absent. A skipped component is never counted as a pass."""
    if needs_yosys and not yosys_ok:
        return {"key": key, "description": desc, "command": " ".join(argv[1:]) if argv and argv[0] == sys.executable else " ".join(argv),
                "status": "skipped", "note": "yowasp-yosys not installed in this environment; run on a host that has it for the full verdict"}
    cmd_str = "python " + " ".join(argv[1:])
    try:
        p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=1800)
        tail = (p.stdout or p.stderr or "").strip().splitlines()[-1:] or [""]
        return {"key": key, "description": desc, "command": cmd_str,
                "status": "pass" if p.returncode == 0 else "fail", "returncode": p.returncode, "last_line": tail[0][:200]}
    except subprocess.TimeoutExpired:
        return {"key": key, "description": desc, "command": cmd_str, "status": "fail", "note": "timed out"}
    except Exception as e:
        return {"key": key, "description": desc, "command": cmd_str, "status": "fail", "note": f"{type(e).__name__}: {str(e)[:120]}"}


def build(quick: bool) -> dict:
    """Run every component and collapse the results into one record. The verdict is 1 only when nothing failed and at least
    one component passed. Coverage is ``software-only`` when yosys is absent, ``full`` when yosys is present and pytest ran,
    and ``no-pytest`` for a quick run with yosys present."""
    yosys_ok = have_yosys()
    results = [run_component(*c, yosys_ok) for c in components(quick)]
    failed = [r for r in results if r["status"] == "fail"]
    skipped = [r for r in results if r["status"] == "skipped"]
    passed = [r for r in results if r["status"] == "pass"]
    verdict = 1 if (not failed and passed) else 0   # one failure forces 0; a run where nothing passed is also 0
    coverage = "full" if yosys_ok and not quick else ("software-only" if not yosys_ok else "no-pytest")
    return {
        "verdict": verdict,
        "coverage": coverage,
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": git_commit(),
        "environment": {"python": sys.version.split()[0], "yowasp_yosys": yosys_ok, "pytest": not quick},
        "counts": {"pass": len(passed), "fail": len(failed), "skipped": len(skipped)},
        "components": results,
    }


def render(m: dict) -> str:
    """Turn the record into the markdown report (PROOF.md). Input: the record. Output: a string. This function writes no
    file. ``main`` writes it, and only with ``--write``."""
    v = m["verdict"]
    L = [f"# PROOF: the safety governor, in software", "",
         f"**VERDICT: {v}**  ({'every component holds' if v else 'A COMPONENT FAILED'})", "",
         f"- Generated: {m['generated']}", f"- Commit: `{m['commit']}`",
         f"- Coverage: {m['coverage']}" + ("" if m["coverage"] == "full" else "  (see skipped components)"),
         f"- Python {m['environment']['python']}; yowasp-yosys {'present' if m['environment']['yowasp_yosys'] else 'absent'}; "
         f"pytest {'run' if m['environment']['pytest'] else 'skipped (--quick)'}",
         f"- Components: {m['counts']['pass']} pass, {m['counts']['fail']} fail, {m['counts']['skipped']} skipped", "",
         "Reproduce: `python -m govsim.prove`. The verdict is 1 only if no component fails; a single "
         "failure forces 0. A component whose toolchain is absent is skipped, never counted as a pass.", "",
         "| Component | What it establishes | Result |", "|---|---|---|"]
    mark = {"pass": "pass", "fail": "**FAIL**", "skipped": "skipped"}
    for r in m["components"]:
        L.append(f"| `{r['key']}` | {r['description']} | {mark[r['status']]} |")
    L += ["", "## What a VERDICT of 1 means", "",
          "In the software model, every stated safety property holds, every planted mutant is caught, every "
          "named attack on the one protected effect is repelled, and the oracle that scores the red team is "
          "itself shown to return 0 when the gate is broken. It is binary and reproducible.", "",
          "## What it does not mean", "",
          "It is not silicon, it does not certify a policy is wise, and it does not close routes outside the "
          "modelled deployment. Those limits are stated in `results/redteam.md` and `docs/18`. The claim is "
          "narrow and strong: without current, valid authorization, the protected effect does not proceed."]
    if m["coverage"] != "full":
        L += ["", f"> Coverage is {m['coverage']}: "
              + ("the RTL formal layer was skipped because yowasp-yosys is absent here. Run `python -m govsim.prove` "
                 "on a host with the RTL toolchain for the full verdict." if not m["environment"]["yowasp_yosys"]
                 else "the pytest sweep was skipped (--quick).")]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    """Command-line entry point. Runs the components and prints one line per component, then the VERDICT. ``--write`` also
    overwrites results/PROOF.md and results/proof-manifest.json. ``--quick`` skips the pytest sweep. ``--json`` prints the
    record. Returns 0 when the verdict is 1."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--quick", action="store_true", help="skip the full pytest sweep")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    m = build(a.quick)
    for r in m["components"]:
        tag = {"pass": "PASS", "fail": "FAIL", "skipped": "SKIP"}[r["status"]]
        print(f"  {tag}  {r['key']}: {r['description']}")
    print(f"\nVERDICT: {m['verdict']}   (coverage: {m['coverage']}, {m['counts']['pass']} pass / {m['counts']['fail']} fail / {m['counts']['skipped']} skipped)")
    if a.write:
        os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
        open(os.path.join(ROOT, "results", "PROOF.md"), "w").write(render(m))
        json.dump(m, open(os.path.join(ROOT, "results", "proof-manifest.json"), "w"), indent=2)
        print("wrote results/PROOF.md and results/proof-manifest.json")
    if a.json:
        print(json.dumps(m))
    return 0 if m["verdict"] == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
