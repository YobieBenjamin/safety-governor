# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""SPDM interoperability against DMTF's own tools (libspdm via spdm-emu, and the
SPDM-Responder-Validator), with negative controls so a pass means something.

    python -m govsim.hardware_ref.interop            # needs the spdm-emu binaries
    python -m govsim.hardware_ref.interop --build    # clone the pinned commits and build them first

Binaries are looked up in $SPDM_EMU_BIN, then /tmp/exp-interfaces/spdm/spdm-emu/build/bin.
The build needs git, cmake and a C compiler, about 150 MB of disk and a few minutes on two
cores; it uses mbedtls, not OpenSSL, to keep the clone small.

Runs, each with an expected outcome:
  EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION  libspdm requester (spdm_requester_emu) -> governor responder, SPDM 1.1     expect success
  EXPERIMENT-SPDM-INTEROP-RAW-MEASUREMENTS  same, SPDM 1.2, raw measurements, signature on every GET_MEASUREMENTS        expect success
  EXPERIMENT-SPDM-FLIPPED-CHALLENGE-SIGNATURE  same as EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION, governor corrupts one CHALLENGE_AUTH signature bit              expect failure
  EXPERIMENT-SPDM-FLIPPED-MEASUREMENT-SIGNATURE  same as EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION, governor corrupts one MEASUREMENTS signature bit                expect failure
  EXPERIMENT-SPDM-REQUESTER-TRUSTS-SAMPLE-ROOT  same as EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION, requester trusts libspdm's sample root, not the governor's       expect "no authority"
  B   DMTF SPDM-Responder-Validator -> governor responder                         expect 0 failed assertions
  EXPERIMENT-SPDM-GOVERNOR-REQUESTS-EARLIER-VERSION  governor requester -> libspdm responder (spdm_responder_emu), SPDM 1.1     expect success
  EXPERIMENT-SPDM-GOVERNOR-REQUESTS-LATER-VERSION  same, SPDM 1.2                                                              expect success
  EXPERIMENT-SPDM-GOVERNOR-TRUSTS-WRONG-ROOT  governor requester trusting the wrong root -> libspdm responder             expect failure

Results go to docs/interfaces/results/spdm-interop.md (and the validator's full log next to it).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from . import REPO
from . import spdm

PINS = {"spdm-emu": ("https://github.com/DMTF/spdm-emu.git", "f7fa18367a967a6fde2b2537a457bc374fe81e21")}
DEFAULT_ROOT = Path("/tmp/exp-interfaces/spdm")
RESULTS = REPO / "docs/interfaces/results"
COMMON = ["--trans", "NONE", "--hash", "SHA_384", "--asym", "ECDSA_P384", "--meas_spec", "DMTF", "--meas_hash", "SHA_384"]


def bin_dir() -> Path | None:
    for p in (os.environ.get("SPDM_EMU_BIN"), str(DEFAULT_ROOT / "spdm-emu/build/bin")):
        if p and (Path(p) / "spdm_requester_emu").exists():
            return Path(p)
    return None


def build(root: Path = DEFAULT_ROOT) -> Path:
    url, sha = PINS["spdm-emu"]
    src = root / "spdm-emu"
    root.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        subprocess.run(["git", "clone", "-q", url, str(src)], check=True)
    subprocess.run(["git", "-C", str(src), "checkout", "-q", sha], check=True)
    subprocess.run(["git", "-C", str(src), "submodule", "update", "--init", "-q", "libspdm", "SPDM-Responder-Validator"], check=True)
    subprocess.run(["git", "-C", str(src / "libspdm"), "submodule", "update", "--init", "-q", "--depth", "1", "os_stub/mbedtlslib/mbedtls"], check=True)
    b = src / "build"
    b.mkdir(exist_ok=True)
    nice = ["nice", "-n", "10"]
    subprocess.run(nice + ["cmake", "-DARCH=x64", "-DTOOLCHAIN=GCC", "-DTARGET=Release", "-DCRYPTO=mbedtls", ".."], cwd=b, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(nice + ["make", "copy_sample_key"], cwd=b, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(nice + ["make", "-j2"], cwd=b, check=True, stdout=subprocess.DEVNULL)
    return b / "bin"


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def make_identity():
    from govsim.clock import SimClock
    from govsim.fuses import Fuses
    from govsim.governor import Governor
    g = Governor("interop", SimClock(), fuses=Fuses(chip_id="1e7e40p0000000a1", uds=b"\x5a" * 32))   # fixed TEST identity: stable results
    return spdm.GovernorIdentity(g.root, spdm.test_ca(), epoch=g.epoch or "")


def workdir(bins: Path, root_der: bytes | None) -> Path:
    d = Path(tempfile.mkdtemp(prefix="spdm-interop-"))
    for k in ("ecp384", "rsa2048", "rsa3072"):
        if (bins / k).exists():
            shutil.copytree(bins / k, d / k)
    if root_der is not None:
        (d / "ecp384/ca.cert.der").write_bytes(root_der)
    return d


def run_requester_emu(bins: Path, ident, extra: list[str], mutant: str = "", trust_governor: bool = True) -> dict:
    port = free_port()
    resp = spdm.Responder(ident)
    if mutant:
        orig = resp._handle

        def handle(req, orig=orig):
            rsp = orig(req)
            if mutant == "chal_sig" and rsp[1] == spdm.CHALLENGE_AUTH:
                rsp = rsp[:-1] + bytes([rsp[-1] ^ 1])
            if mutant == "meas_sig" and rsp[1] == spdm.MEASUREMENTS and req[2] & 1:
                rsp = rsp[:-1] + bytes([rsp[-1] ^ 1])
            return rsp
        resp._handle = handle
    ready = threading.Event()
    box: dict = {}

    def serve():
        try:
            box["events"] = spdm.serve_emu(resp, port, ready=ready, timeout=60)
        except Exception as e:                     # recorded, never a pass
            box["error"] = repr(e)
            ready.set()
    th = threading.Thread(target=serve, daemon=True)
    th.start()
    ready.wait(10)
    d = workdir(bins, ident.chain_ders[0] if trust_governor else None)
    p = subprocess.run([str(bins / "spdm_requester_emu"), "--port", str(port)] + COMMON + extra + ["-v"],
                       cwd=d, capture_output=True, text=True, timeout=120)
    th.join(10)
    out = p.stdout + p.stderr
    errors = [l.strip() for l in out.splitlines() if l.startswith("ERROR")]
    shutil.rmtree(d, ignore_errors=True)
    return {"exit": p.returncode, "errors": errors, "no_authority": "LIBSPDM_STATUS_VERIF_NO_AUTHORITY" in out,
            "requests": len(resp.log), "server": box.get("error") or box.get("events")}


def run_validator(bins: Path, ident) -> dict:
    port = free_port()
    resp = spdm.Responder(ident)
    ready = threading.Event()
    th = threading.Thread(target=lambda: spdm.serve_emu(resp, port, ready=ready, timeout=300), daemon=True)
    th.start()
    ready.wait(10)
    d = workdir(bins, ident.chain_ders[0])
    p = subprocess.run([str(bins / "spdm_device_validator_sample"), "--port", str(port)] + COMMON, cwd=d, capture_output=True, text=True, timeout=600)
    th.join(10)
    log = (d / "test.log").read_text() if (d / "test.log").exists() else ""
    m = re.search(r"test suite \(spdm_responder_conformance_test\) - pass: (\d+), fail: (\d+)", log)
    not_tested = sorted({re.sub(r" - setup enter$", "", l.strip().replace("test case ", "")) for i, l in enumerate(log.splitlines())
                         if "setup enter" in l and i + 2 < len(log.splitlines()) and "NOT_TESTED" in log.splitlines()[i + 2]})
    shutil.rmtree(d, ignore_errors=True)
    return {"exit": p.returncode, "pass": int(m.group(1)) if m else None, "fail": int(m.group(2)) if m else None,
            "not_tested": not_tested, "requests": len(resp.log), "log": log}


def run_responder_emu(bins: Path, ver: str, trust_libspdm_root: bool = True) -> dict:
    port = free_port()
    d = workdir(bins, None)
    proc = subprocess.Popen([str(bins / "spdm_responder_emu"), "--port", str(port), "--ver", ver] + COMMON, cwd=d,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    root = (d / "ecp384/ca.cert.der").read_bytes() if trust_libspdm_root else make_identity().chain_ders[0]
    out: dict = {}
    try:
        send, close = spdm.emu_client(port)
        q = spdm.Requester(send, root, want_version=int(ver.replace(".", ""), 16))
        try:
            r = q.attest()
            out = {"ok": True, "version": r["version"], "indices": sorted(r["measurements"]), "chain_certs": len(q.certs)}
        except spdm.SpdmError as e:
            out = {"ok": False, "error": str(e)}
        finally:
            close()
    finally:
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(d, ignore_errors=True)
    return out


def run_all(bins: Path) -> tuple[bool, dict]:
    ident = make_identity()
    r: dict = {}
    r["EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION"] = run_requester_emu(bins, ident, ["--ver", "1.1", "--cap", "CERT,CHAL", "--exe_conn", "DIGEST,CERT,CHAL,MEAS", "--basic_mut_auth", "NO"])
    r["EXPERIMENT-SPDM-INTEROP-RAW-MEASUREMENTS"] = run_requester_emu(bins, ident, ["--ver", "1.2", "--cap", "CERT,CHAL", "--exe_conn", "DIGEST,CERT,CHAL,MEAS", "--basic_mut_auth", "NO", "--meas_att", "RAW,SIG"])
    r["EXPERIMENT-SPDM-FLIPPED-CHALLENGE-SIGNATURE"] = run_requester_emu(bins, ident, ["--ver", "1.1", "--cap", "CERT,CHAL", "--exe_conn", "DIGEST,CERT,CHAL,MEAS", "--basic_mut_auth", "NO"], mutant="chal_sig")
    r["EXPERIMENT-SPDM-FLIPPED-MEASUREMENT-SIGNATURE"] = run_requester_emu(bins, ident, ["--ver", "1.1", "--cap", "CERT,CHAL", "--exe_conn", "DIGEST,CERT,CHAL,MEAS", "--basic_mut_auth", "NO"], mutant="meas_sig")
    r["EXPERIMENT-SPDM-REQUESTER-TRUSTS-SAMPLE-ROOT"] = run_requester_emu(bins, ident, ["--ver", "1.1", "--cap", "CERT,CHAL", "--exe_conn", "DIGEST,CERT,CHAL,MEAS", "--basic_mut_auth", "NO"], trust_governor=False)
    r["B"] = run_validator(bins, ident)
    r["EXPERIMENT-SPDM-GOVERNOR-REQUESTS-EARLIER-VERSION"] = run_responder_emu(bins, "1.1")
    r["EXPERIMENT-SPDM-GOVERNOR-REQUESTS-LATER-VERSION"] = run_responder_emu(bins, "1.2")
    r["EXPERIMENT-SPDM-GOVERNOR-TRUSTS-WRONG-ROOT"] = run_responder_emu(bins, "1.1", trust_libspdm_root=False)
    verdict = {
        "EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION": r["EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION"]["exit"] == 0 and not r["EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION"]["errors"] and not r["EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION"]["no_authority"],
        "EXPERIMENT-SPDM-INTEROP-RAW-MEASUREMENTS": r["EXPERIMENT-SPDM-INTEROP-RAW-MEASUREMENTS"]["exit"] == 0 and not r["EXPERIMENT-SPDM-INTEROP-RAW-MEASUREMENTS"]["errors"] and not r["EXPERIMENT-SPDM-INTEROP-RAW-MEASUREMENTS"]["no_authority"],
        "EXPERIMENT-SPDM-FLIPPED-CHALLENGE-SIGNATURE": r["EXPERIMENT-SPDM-FLIPPED-CHALLENGE-SIGNATURE"]["exit"] != 0 and any("authentication" in e for e in r["EXPERIMENT-SPDM-FLIPPED-CHALLENGE-SIGNATURE"]["errors"]),
        "EXPERIMENT-SPDM-FLIPPED-MEASUREMENT-SIGNATURE": r["EXPERIMENT-SPDM-FLIPPED-MEASUREMENT-SIGNATURE"]["exit"] != 0 and any("measurement" in e for e in r["EXPERIMENT-SPDM-FLIPPED-MEASUREMENT-SIGNATURE"]["errors"]),
        "EXPERIMENT-SPDM-REQUESTER-TRUSTS-SAMPLE-ROOT": r["EXPERIMENT-SPDM-REQUESTER-TRUSTS-SAMPLE-ROOT"]["no_authority"],
        "B": r["B"]["fail"] == 0 and (r["B"]["pass"] or 0) > 0,
        "EXPERIMENT-SPDM-GOVERNOR-REQUESTS-EARLIER-VERSION": r["EXPERIMENT-SPDM-GOVERNOR-REQUESTS-EARLIER-VERSION"].get("ok") is True,
        "EXPERIMENT-SPDM-GOVERNOR-REQUESTS-LATER-VERSION": r["EXPERIMENT-SPDM-GOVERNOR-REQUESTS-LATER-VERSION"].get("ok") is True,
        "EXPERIMENT-SPDM-GOVERNOR-TRUSTS-WRONG-ROOT": r["EXPERIMENT-SPDM-GOVERNOR-TRUSTS-WRONG-ROOT"].get("ok") is False and "pinned root" in r["EXPERIMENT-SPDM-GOVERNOR-TRUSTS-WRONG-ROOT"].get("error", ""),
    }
    return all(verdict.values()), {"runs": r, "verdict": verdict}


def write_report(res: dict) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "spdm-validator-latest.log").write_text(res["runs"]["B"].pop("log", ""))
    (RESULTS / "spdm-interop.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    v, r = res["verdict"], res["runs"]
    lines = ["# SPDM interop results", "",
             "Generated by `python -m govsim.hardware_ref.interop` (do not edit; rerun instead).",
             f"spdm-emu {PINS['spdm-emu'][1]} built with mbedtls; libspdm and SPDM-Responder-Validator at the submodule commits it pins.", "",
             "| Run | What | Expected | Result |", "|---|---|---|---|"]
    desc = {
        "EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION": ("libspdm requester -> governor responder, SPDM 1.1", "success"),
        "EXPERIMENT-SPDM-INTEROP-RAW-MEASUREMENTS": ("libspdm requester -> governor responder, SPDM 1.2, raw measurements, signed every time", "success"),
        "EXPERIMENT-SPDM-FLIPPED-CHALLENGE-SIGNATURE": ("EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION with one CHALLENGE_AUTH signature bit flipped by the governor", "libspdm rejects"),
        "EXPERIMENT-SPDM-FLIPPED-MEASUREMENT-SIGNATURE": ("EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION with one MEASUREMENTS signature bit flipped by the governor", "libspdm rejects"),
        "EXPERIMENT-SPDM-REQUESTER-TRUSTS-SAMPLE-ROOT": ("EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION with libspdm trusting its own sample root instead of the governor's", "libspdm says no authority"),
        "B": ("DMTF SPDM-Responder-Validator -> governor responder", "0 failed assertions"),
        "EXPERIMENT-SPDM-GOVERNOR-REQUESTS-EARLIER-VERSION": ("governor requester -> libspdm responder, SPDM 1.1", "success"),
        "EXPERIMENT-SPDM-GOVERNOR-REQUESTS-LATER-VERSION": ("governor requester -> libspdm responder, SPDM 1.2", "success"),
        "EXPERIMENT-SPDM-GOVERNOR-TRUSTS-WRONG-ROOT": ("governor requester trusting the wrong root -> libspdm responder", "governor requester rejects"),
    }
    for k in ("EXPERIMENT-SPDM-INTEROP-EARLIER-VERSION", "EXPERIMENT-SPDM-INTEROP-RAW-MEASUREMENTS", "EXPERIMENT-SPDM-FLIPPED-CHALLENGE-SIGNATURE", "EXPERIMENT-SPDM-FLIPPED-MEASUREMENT-SIGNATURE", "EXPERIMENT-SPDM-REQUESTER-TRUSTS-SAMPLE-ROOT", "B", "EXPERIMENT-SPDM-GOVERNOR-REQUESTS-EARLIER-VERSION", "EXPERIMENT-SPDM-GOVERNOR-REQUESTS-LATER-VERSION", "EXPERIMENT-SPDM-GOVERNOR-TRUSTS-WRONG-ROOT"):
        d, e = desc[k]
        detail = r[k]
        if k == "B":
            got = f"{detail['pass']} pass, {detail['fail']} fail, {len(detail['not_tested'])} cases not tested"
        elif k.startswith("A"):
            got = f"exit {detail['exit']}; {'; '.join(detail['errors']) or 'no errors'}{'; no authority' if detail['no_authority'] else ''}"
        else:
            got = f"verified {detail.get('version')} indices {detail.get('indices')}" if detail.get("ok") else f"rejected: {detail.get('error')}"
        lines.append(f"| {k} | {d} | {e} | {'PASS' if v[k] else 'FAIL'}: {got} |")
    lines += ["", "Validator cases it could not run against this responder (setup needs a feature we do not implement):", ""]
    lines += [f"- {c}" for c in r["B"]["not_tested"]]
    lines += ["", "**Overall: " + ("PASS" if all(v.values()) else "FAIL") + "**", ""]
    p = RESULTS / "spdm-interop.md"
    p.write_text("\n".join(lines))
    return p


def main(argv: list[str]) -> int:
    bins = bin_dir()
    if bins is None and "--build" in argv:
        bins = build()
    if bins is None:
        print("spdm interop: SKIPPED, spdm-emu binaries not found (set SPDM_EMU_BIN or pass --build)")
        return 2
    ok, res = run_all(bins)
    p = write_report(res)
    for k, v in res["verdict"].items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"spdm interop: {'PASS' if ok else 'FAIL'} -> {p.relative_to(REPO)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
