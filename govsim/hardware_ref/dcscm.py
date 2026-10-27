# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""OCP DC-SCM 2.x: the DC-SCI pin mapping checker and a model of LTPI link loss.

``check_mapping`` validates ``hw/pinout/dcscm_mapping.csv`` against the governor pinout
(``hw/pinout/governor_module.csv``), the public DC-SCI pin facts we could transcribe
(``hw/pinout/dcsci_public_pins.csv``, from the Project Argus spec, which states it follows the
OCP DC-SCI 2.0 pin definition) and the source register (``docs/interfaces/sources.csv``).
Every rule returns an error with a code, so a test can plant one fault and assert that exactly
that rule fires.

``LtpiLink`` models what LTPI 1.2 section 2.5.2 says about GPIO on link loss ("LTPI shall
maintain the state of the GPIOs exposed to the system") and the fail-safe override the
governor needs on top of it (REQUIREMENT-LINK-LOSS-ASSERTS-LEVERS). The spec text is the unsafe part: a governor
whose link drops while its levers are released leaves them released.

    python -m govsim.hardware_ref.dcscm      # check the CSV, print the no-public-home list
"""
from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import REPO

GOV_PINOUT = REPO / "hw/pinout/governor_module.csv"
MAPPING = REPO / "hw/pinout/dcscm_mapping.csv"
PUBLIC_PINS = REPO / "hw/pinout/dcsci_public_pins.csv"
SOURCES = REPO / "docs/interfaces/sources.csv"
REQ_DOC = REPO / "docs/interfaces/01-dcscm-dcsci-ltpi.md"

# The governor's levers: everything that can stop or reset a GPU or a switch. Each one must be
# accounted for, and each one carried over LTPI must name the fail-safe requirement it needs.
LEVERS = {"PWRBRK_N": 8, "PERST_N": 8, "PWR_EN": 8, "NVSW_RESET_N": 1, "PEX_RESET_N": 1}
HALT_CRITICAL = {"PWRBRK_N"}           # asserted on the 1 ms path: must ride a low-latency channel
STATUSES = {"designed", "designed-open", "no-public-home", "intentionally-local", "proposed-missing-pin"}
ROUTES = {"dcsci", "ltpi", "module-local", "own-connector", "none"}
DIR_MAP = {"out": "output", "in": "input", "bidir": "inout"}
LTPI_RE = re.compile(r"^LTPI2?:(LL|NL)_GPIO_(SCM_HPM|HPM_SCM)\[(\d+)\]$")
# LTPI 1.2 section 2.2.1.1: the Default I/O Frame carries 2 bytes of LL GPIO and 2 bytes of NL GPIO.
LL_PER_FRAME = 16
NL_PER_FRAME = 16
# LTPI 1.2 Table 15, slowest listed rate (25 MHz SDR): 6.40 us constant, 19.20 us random latency.
LTPI_LL_WORST_US = 19.20
HALT_BOUND_US = 1000.0                 # docs/02-safety-fabric.md section 1
LOOP_WORST_US = 317.15                 # hw/loop/results.md worst case, includes 10 us lever assertion


@dataclass(frozen=True)
class Finding:
    code: str
    where: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.where}: {self.detail}"


def _read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r and not str(next(iter(r.values()), "")).startswith("#")]


def expand_governor_signals(rows: list[dict]) -> set[tuple[str, str]]:
    """(signal, instance) for every physical pin in governor_module.csv."""
    out: set[tuple[str, str]] = set()
    for r in rows:
        group, pin = r["group"], r["pin"]
        m = re.match(r"^(.*)\[(\d+):(\d+)\]$", pin)
        if m:
            base, hi, lo = m.group(1), int(m.group(2)), int(m.group(3))
            out.update((base, f"bit{i}") for i in range(lo, hi + 1))
            continue
        parts = pin.split("/")
        names = [parts[0]]
        prefix = parts[0].rsplit("_", 1)[0] + "_" if "_" in parts[0] else ""
        names += [prefix + p for p in parts[1:]]
        m = re.match(r"^slot(\d+)\.\.(\d+)$", group)
        instances = [f"slot{i}" for i in range(int(m.group(1)), int(m.group(2)) + 1)] if m else [""]
        out.update((n, i) for n in names for i in instances)
    return out


def source_ids(path: Path = SOURCES) -> set[str]:
    return {r["id"] for r in _read(path)}


def ref_ok(ref: str, ids: set[str]) -> bool:
    """A spec_ref is a ';'-separated list; each item starts with a source id, a repo path, or
    is the literal 'no public source'."""
    if not ref.strip():
        return False
    for item in (x.strip() for x in ref.split(";")):
        if item == "no public source":
            continue
        head = item.split()[0]
        if head in ids or head.startswith(("docs/", "hw/", "rtl/", "govsim/")):
            continue
        return False
    return True


def check_mapping(mapping: list[dict] | None = None, governor: list[dict] | None = None,
                  public_pins: list[dict] | None = None, ids: set[str] | None = None,
                  req_text: str | None = None) -> list[Finding]:
    mapping = _read(MAPPING) if mapping is None else mapping
    governor = _read(GOV_PINOUT) if governor is None else governor
    public_pins = _read(PUBLIC_PINS) if public_pins is None else public_pins
    ids = source_ids() if ids is None else ids
    req_text = (REQ_DOC.read_text(encoding="utf-8") if REQ_DOC.exists() else "") if req_text is None else req_text
    errs: list[Finding] = []
    pins = {p["pin"]: p for p in public_pins}
    gov = expand_governor_signals(governor)

    seen_keys: dict[tuple[str, str], int] = {}
    pin_users: dict[str, str] = {}
    chan_users: dict[str, str] = {}
    for n, r in enumerate(mapping, start=2):
        sig, inst = r["governor_signal"], r["instance"]
        where = f"line {n} {sig}{'.' + inst if inst else ''}"
        key = (sig, inst)
        seen_keys[key] = seen_keys.get(key, 0) + 1
        if seen_keys[key] > 1:
            errs.append(Finding("DUP_SIGNAL", where, "signal mapped twice"))
        proposed = sig.startswith("+")
        if not proposed and key not in gov:
            errs.append(Finding("UNKNOWN_SIGNAL", where, "not a pin of hw/pinout/governor_module.csv (prefix '+' for a proposed addition)"))
        if r["status"] not in STATUSES:
            errs.append(Finding("BAD_STATUS", where, r["status"]))
        if proposed and r["status"] not in ("designed", "proposed-missing-pin"):
            errs.append(Finding("BAD_STATUS", where, "a '+' row is module infrastructure (designed) or a proposed pin"))
        if r["route"] not in ROUTES:
            errs.append(Finding("BAD_ROUTE", where, r["route"]))
        if not ref_ok(r["spec_ref"], ids):
            errs.append(Finding("NO_SOURCE", where, f"spec_ref {r['spec_ref']!r} does not resolve to docs/interfaces/sources.csv"))
        if r["status"] == "no-public-home" and (r["route"] != "none" or not r["notes"].strip()):
            errs.append(Finding("NO_HOME_UNEXPLAINED", where, "a signal with no public home needs route=none and a note saying why"))
        if r["route"] == "none" and r["status"] != "no-public-home":
            errs.append(Finding("NO_HOME_UNFLAGGED", where, "route none must be flagged no-public-home"))

        if r["route"] == "dcsci":
            fn = r["dcsci_function"]
            plist = [p.strip() for p in r["dcsci_pin"].split(";") if p.strip()]
            if not plist:
                errs.append(Finding("NO_PIN", where, "dcsci route without a pin"))
            if len(plist) > 1 and fn != "GND":
                errs.append(Finding("MULTI_PIN", where, "only GND may list several pins in one row"))
            for p in plist:
                if p not in pins:
                    errs.append(Finding("PIN_NOT_PUBLIC", where, f"{p} is not in dcsci_public_pins.csv"))
                    continue
                if p in pin_users:
                    errs.append(Finding("PIN_REUSED", where, f"{p} already used by {pin_users[p]}"))
                pin_users[p] = where
                facts = pins[p]
                if fn not in facts["functions"].split("|"):
                    errs.append(Finding("FUNC_NOT_ON_PIN", where, f"{fn} is not a function of {p} ({facts['functions']})"))
                if fn == "GND":
                    continue
                if r["gov_voltage"] != facts["voltage"] and not r["translator"].strip():
                    errs.append(Finding("VOLTAGE", where, f"governor {r['gov_voltage']} V vs DC-SCI {p} {facts['voltage']} with no translator"))
                if DIR_MAP.get(r["gov_dir"]) != facts["scm_direction"]:
                    errs.append(Finding("DIRECTION", where, f"governor {r['gov_dir']} vs DC-SCI {p} {facts['scm_direction']} (SCM view)"))
        if r["route"] == "ltpi":
            ch = r["ltpi_channel"]
            m = LTPI_RE.match(ch)
            if not m:
                errs.append(Finding("LTPI_CHANNEL", where, f"{ch!r} is not LTPI[2]:(LL|NL)_GPIO_(SCM_HPM|HPM_SCM)[n]"))
            else:
                kind, way, idx = m.group(1), m.group(2), int(m.group(3))
                if ch in chan_users:
                    errs.append(Finding("LTPI_REUSED", where, f"{ch} already used by {chan_users[ch]}"))
                chan_users[ch] = where
                if idx >= (LL_PER_FRAME if kind == "LL" else NL_PER_FRAME):
                    errs.append(Finding("LTPI_FRAME", where, f"{kind} index {idx} does not fit the Default I/O Frame (LTPI 1.2 2.2.1.1)"))
                want = "SCM_HPM" if r["gov_dir"] == "out" else "HPM_SCM"
                if way != want:
                    errs.append(Finding("DIRECTION", where, f"governor {r['gov_dir']} on an {way} channel"))
                if sig in HALT_CRITICAL and kind != "LL":
                    errs.append(Finding("LTPI_LATENCY", where, "a halt-path lever must ride a low-latency GPIO"))
            if not r["translator"].strip():
                errs.append(Finding("VOLTAGE", where, "an LTPI-tunnelled signal must name the HPM endpoint that drives it"))

    # every governor pin accounted for
    for key in sorted(gov - set(seen_keys)):
        errs.append(Finding("UNMAPPED", f"{key[0]}{'.' + key[1] if key[1] else ''}", "governor pin with no row in the mapping"))
    # every lever accounted for, and fail-safe on every tunnelled lever
    for lever, count in LEVERS.items():
        rows = [r for r in mapping if r["governor_signal"] == lever]
        if len(rows) != count:
            errs.append(Finding("LEVER_MISSING", lever, f"{len(rows)} rows, expected {count}"))
        for r in rows:
            if r["route"] == "ltpi":
                fs = r["fail_safe"].strip()
                if not fs:
                    errs.append(Finding("LEVER_NO_FAILSAFE", f"{lever}.{r['instance']}", "LTPI holds GPIO state on link loss (LTPI 1.2 2.5.2); a lever over LTPI must name its fail-safe requirement"))
                elif fs not in req_text:
                    errs.append(Finding("LEVER_NO_FAILSAFE", f"{lever}.{r['instance']}", f"{fs} is not defined in {REQ_DOC.name}"))
    # the 1 ms halt bound with the LTPI hop added on top of the loop worst case
    if any(r["governor_signal"] in HALT_CRITICAL and r["route"] == "ltpi" for r in mapping):
        total = LOOP_WORST_US + LTPI_LL_WORST_US
        if total > HALT_BOUND_US:
            errs.append(Finding("HALT_BOUND", "PWRBRK_N", f"{total:.2f} us > {HALT_BOUND_US} us"))
    return errs


def no_public_home(mapping: list[dict] | None = None) -> list[str]:
    mapping = _read(MAPPING) if mapping is None else mapping
    return [f"{r['governor_signal']}{'.' + r['instance'] if r['instance'] else ''}" for r in mapping if r["status"] == "no-public-home"]


# --------------------------------------------------------------------------- LTPI link-loss model
@dataclass
class LtpiLink:
    """GPIO tunnelled SCM to HPM. ``spec`` mode does what LTPI 1.2 2.5.2 says: on Link Lost the
    HPM side keeps the last GPIO values. ``failsafe`` mode adds REQUIREMENT-LINK-LOSS-ASSERTS-LEVERS: on Link Lost, and
    before the link first reaches Operational, the HPM endpoint drives every governor lever to
    its asserted value."""
    mode: str = "spec"
    safe_values: dict = field(default_factory=dict)       # channel -> value that means "lever asserted"
    operational: bool = False
    ever_operational: bool = False
    hpm_out: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.mode not in ("spec", "failsafe"):
            raise ValueError(self.mode)
        if self.mode == "failsafe":
            self.hpm_out = dict(self.safe_values)

    def train(self) -> None:
        self.operational = self.ever_operational = True

    def send(self, frame: dict) -> None:
        """One IO frame from the SCM: delivered only while the link is operational."""
        if self.operational:
            self.hpm_out.update(frame)

    def link_lost(self) -> None:
        self.operational = False
        if self.mode == "failsafe":
            self.hpm_out.update(self.safe_values)


def main(argv: list[str] | None = None) -> int:
    errs = check_mapping()
    rows = _read(MAPPING)
    print(f"dcscm_mapping.csv: {len(rows)} rows, {len(expand_governor_signals(_read(GOV_PINOUT)))} governor pins")
    for e in errs:
        print("  FAIL", e)
    homeless = no_public_home(rows)
    print(f"  no public home ({len(homeless)}): {', '.join(homeless)}")
    proposed = sorted({r['governor_signal'] for r in rows if r['status'] == 'proposed-missing-pin'})
    print(f"  proposed pins the governor lacks ({len(proposed)}): {', '.join(proposed)}")
    print("  CSV checker:", "PASS" if not errs else f"FAIL ({len(errs)})")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
