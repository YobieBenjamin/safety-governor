"""One command for the interfaces work:

    python -m govsim.hardware_ref            # everything; interop runs if spdm-emu is built
    python -m govsim.hardware_ref --build    # also clone and build spdm-emu first (a few minutes)

Steps, each PASS or FAIL (interop may be SKIPPED, with the reason, when the binaries are absent):
  1. DC-SCI mapping checker on hw/pinout/dcscm_mapping.csv
  2. PCIe CEM timing on the RTL halt sequencer, with and without the CEM shaper
  3. SPDM responder against the governor's own requester, 1.1 and 1.2, in process
  4. NVIDIA nvtrust public sample through the adapter (crypto checks must pass)
  5. SPDM interop against libspdm and the DMTF responder validator
  6. compliance matrix: every row sourced, every evidence file present, Markdown in sync
  7. style: no em dash in anything this work wrote
"""
from __future__ import annotations

import sys
import time

from . import REPO


def step(name, fn):
    t = time.time()
    try:
        rc = fn()
    except Exception as e:                       # a crash is a failure, never a pass
        print(f"  error: {e!r}")
        rc = 1
    status = {0: "PASS", 2: "SKIPPED"}.get(rc, "FAIL")
    print(f"[{status}] {name} ({time.time() - t:.0f} s)")
    return rc


def spdm_selftest() -> int:
    from govsim.clock import SimClock
    from govsim.governor import Governor
    from . import spdm
    g = Governor("selftest", SimClock())
    ident = spdm.GovernorIdentity(g.root, spdm.test_ca())
    for v in (spdm.V11, spdm.V12):
        r = spdm.Responder(ident)
        out = spdm.Requester(r.handle, ident.chain_ders[0], want_version=v).attest(raw=True)
        print(f"  SPDM {out['version']}: {len(out['measurements'])} signed measurement blocks verified")
    return 0


def nvtrust_sample() -> int:
    from . import nvtrust
    s = nvtrust.summary()
    for k, v in s["checks"].items():
        print(f"  {k:<17} {v}")
    return 0 if all(v.startswith("ok") for k, v in s["checks"].items() if "CRYPTO" in v) else 1


def no_em_dash() -> int:
    paths = list((REPO / "docs/interfaces").rglob("*")) + list((REPO / "govsim/hardware_ref").glob("*.py")) + \
        [REPO / p for p in ("hw/pinout/dcscm_mapping.csv", "hw/pinout/dcsci_public_pins.csv", "rtl/governor_rtl/cem_sideband.py",
                            "tools/interfaces/nvtrust_oracle.py")] + list((REPO / "tests").glob("test_if_*.py"))
    bad = [p for p in paths if p.is_file() and p.suffix in (".md", ".py", ".csv", ".txt") and chr(0x2014) in p.read_text(encoding="utf-8", errors="ignore")]
    for p in bad:
        print(f"  em dash in {p.relative_to(REPO)}")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    from . import cem, dcscm, interop, matrix
    rcs = [
        step("1 DC-SCI mapping", lambda: dcscm.main([])),
        step("2 PCIe CEM timing", lambda: cem.main([])),
        step("3 SPDM in process", spdm_selftest),
        step("4 nvtrust sample", nvtrust_sample),
        step("5 SPDM interop", lambda: interop.main(["--build"] if "--build" in argv else [])),
        step("6 compliance matrix", lambda: matrix.main(["--check"])),
        step("7 style", no_em_dash),
    ]
    failed = [i + 1 for i, rc in enumerate(rcs) if rc not in (0, 2)]
    skipped = [i + 1 for i, rc in enumerate(rcs) if rc == 2]
    print("interfaces:", "FAIL steps " + str(failed) if failed else "PASS" + (f" (skipped {skipped})" if skipped else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
