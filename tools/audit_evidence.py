#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Does each audit regression fail for the intended security reason?

    python3 tools/audit_evidence.py [--hs ../hardware-and-silicon] [--out audit/external-2026-10-22/EVIDENCE.md]

For every implementation finding of the 22 October audit this script:
  1. copies the FIXED tree to a scratch folder and reverts that one fix (the smallest edit that
     restores the old behaviour, written out below so anyone can read exactly what is undone);
  2. runs the finding's regression tests there and requires each to FAIL with an assertion
     (AssertionError, or pytest's "DID NOT RAISE"), never with an import, attribute, type or name
     error, which would mean the test fails because the interface changed, not because the
     unauthorized operation was accepted;
  3. runs the finding's "legitimate operation still works" tests on the fixed tree and requires them
     to PASS, so the fix did not just refuse everything.
For hardware-and-silicon it also runs the regression file on the audited snapshot 11eb119 itself and
classifies every failure the same way. Writes a markdown table of what it saw.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

SG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTENDED = ("AssertionError", "Failed")      # "Failed" is pytest.raises' DID NOT RAISE: the old code accepted it

# finding id, repo, what the revert restores, [(file, fixed text, reverted text)], regression tests, positive tests
FINDINGS = [
    ("1", "sg", "the rulebook's own threshold decides how many signatures it needs (no floor, no configuration in force)",
     [("govsim/policy.py",
       "        if threshold < max(1, floor) or threshold > len(own_keys):\n            return False, reasons.POLICY_QUORUM\n        if trusted is not None:",
       "        if trusted is not None and False:"),
      ("govsim/policy.py",
       "            signers, required = own_keys, max(threshold, floor)",
       "            signers, required = own_keys, threshold"),
      ("govsim/policy.py",
       "        if required < max(1, floor):\n            return False, reasons.POLICY_QUORUM\n", "")],
     ["tests/test_h19_authorization.py::test_unsigned_image_with_threshold_zero_refused",
      "tests/test_h19_authorization.py::test_image_cannot_lower_k_below_the_fused_threshold",
      "tests/test_h19_authorization.py::test_the_quorum_in_force_cannot_go_below_the_manufacture_floor"],
     # the next two are hardening of the NEW rotation rule, not regressions for the audited defect (the old
     # code refused both cases too), so they belong with the tests that must pass on the fixed tree
     ["tests/test_h19_authorization.py::test_threshold_above_the_number_of_keys_refused",
      "tests/test_h19_authorization.py::test_fresh_keys_cannot_install_themselves",
      "tests/test_h19_authorization.py::test_an_edition_that_raises_k_binds_the_next_change",
      "tests/test_h19_authorization.py::test_the_current_quorum_can_rotate_the_governance_keys",
      "tests/test_h03_quorum.py"]),
    ("2", "sg", "all three locks off, as at dccc1e0: no command binding, no chip or expiry binding, and the heartbeat key may sign HALT and CLEAR",
     [("govsim/governor.py",
       "        if p.get(\"type\") != cmd.lower():\n            return False, reasons.MBOX_WRONG_COMMAND\n", ""),
      ("govsim/governor.py",
       "        if cls == \"authority\":\n            if p.get(\"chip_id\") != self.chip_id:",
       "        if False:\n            if p.get(\"chip_id\") != self.chip_id:"),
      ("govsim/governor.py",
       "            hexes = p.get(\"authority_keys\", [])",
       "            hexes = p.get(\"authority_keys\", []) + [p[\"heartbeat_key\"]]")],
     ["tests/test_h19_authorization.py::test_a_heartbeat_does_not_clear_a_halt",
      "tests/test_h19_authorization.py::test_the_heartbeat_key_cannot_sign_a_clear",
      "tests/test_h19_authorization.py::test_a_halt_is_not_a_clear",
      "tests/test_h19_authorization.py::test_an_approval_does_not_clear_an_alarm",
      "tests/test_h19_authorization.py::test_the_mailbox_names_the_wrong_command",
      "tests/test_h19_authorization.py::test_no_signed_message_is_accepted_by_a_command_it_was_not_signed_for"],
     ["tests/test_h11_halt_loop.py", "tests/test_h05_alarms.py", "tests/test_h08_override.py"]),
    ("2b", "sg", "a HALT or CLEAR need not name this chip or carry a live expiry",
     [("govsim/governor.py",
       "        if cls == \"authority\":\n            if p.get(\"chip_id\") != self.chip_id:",
       "        if False:\n            if p.get(\"chip_id\") != self.chip_id:")],
     ["tests/test_h19_authorization.py::test_a_clear_for_another_chip_is_refused",
      "tests/test_h19_authorization.py::test_an_expired_clear_is_refused",
      "tests/test_h19_authorization.py::test_a_clear_good_for_a_day_is_refused"],
     ["tests/test_h11_halt_loop.py"]),
    ("6", "sg", "a ticket issued before a halt commits during it (the code side of INVARIANT-NOTHING-EXECUTES-WHILE-HALTED)",
     [("govsim/governor.py",
       "            if self.state != RUN:\n                self.log.append(\"gate.commit_rejected\", {\"why\": reasons.MBOX_NOT_RUNNING})\n                return False\n", "")],
     ["tests/test_h19_authorization.py::test_a_ticket_issued_before_a_halt_does_not_execute_during_it"],
     ["tests/test_h00_contract.py::test_allowed_operation_succeeds"]),
    # Registered name: GAP-REVOCATIONS-UNENFORCED (old ID G1 is kept because code matches on it)
    ("G1", "sg", "revocations stored and never read",
     [("govsim/governor.py", "        return {kid: k for kid, k in keys.items() if kid not in revoked}", "        return keys"),
      ("govsim/governor.py",
       "        if cert[\"payload\"][\"chip_id\"] in set((self.policy or {}).get(\"revocations\", []))",
       "        if False and cert[\"payload\"][\"chip_id\"] in set((self.policy or {}).get(\"revocations\", []))")],
     ["tests/test_h20_closed_gaps.py::test_a_revoked_observer_key_is_not_a_witness",
      "tests/test_h20_closed_gaps.py::test_a_revoked_gpu_cannot_attest",
      "tests/test_h20_closed_gaps.py::test_a_revoked_approver_cannot_release_a_hold"],
     ["tests/test_h18_oversight.py", "tests/test_h01_attestation.py"]),
    # Registered name: GAP-SANDBOX-FLAG-IGNORED (old ID G2 is kept because code matches on it)
    ("G2", "sg", "CAP_REQUEST ignores the sandbox flag",
     [("govsim/governor.py", "        if self.policy.get(\"sandbox\") and peer != \"host\":", "        if False:")],
     ["tests/test_h20_closed_gaps.py::test_a_sandboxed_governor_grants_no_peer_capability"],
     ["tests/test_h20_closed_gaps.py::test_without_the_sandbox_the_same_request_is_granted"]),
    # Registered name: GAP-HAZARD-BUDGET-PER-GOVERNOR (old ID G3 is kept because code matches on it)
    ("G3", "sg", "each governor counts a session's hazards on its own ledger",
     [("govsim/governor.py",
       "        owner = self.policy[\"budget_owners\"][\"hazard\"]",
       "        owner = self.chip_id")],
     ["tests/test_h20_closed_gaps.py::test_a_session_spread_over_two_governors_gets_one_hazard_budget"],
     ["tests/test_h17_use_cases.py::test_session_hazard_budget_parks_the_session_and_raises_a_scoped_alarm"]),
    # Registered name: GAP-WORKLOAD-TOKEN-SURVIVES-RULE-CHANGE (old ID G5 is kept because code matches on it)
    ("G5", "sg", "a workload token survives an edition change",
     [("govsim/governor.py", "                self.fingerprint = digest([self.workload, self.epoch])\n", "                pass\n")],
     ["tests/test_h20_closed_gaps.py::test_a_workload_token_from_the_old_edition_is_refused"],
     ["tests/test_h01_attestation.py"]),
    ("3", "hs", "the gate key is seeded from the two alias public keys",
     [("hardware_ref/system.py",
       "    gate_key = cpu.derive_key(b\"gate-signing-key\")",
       "    gate_key = SigningKey.from_seed(hkdf(bytes.fromhex(cpu.alias_cert[\"payload\"][\"subject_pub\"]) + bytes.fromhex(gpu.alias_cert[\"payload\"][\"subject_pub\"]), b\"gate-signing-key\", 32))")],
     ["tests/test_audit_2026_10_22.py::test_gate_key_cannot_be_computed_from_public_quotes"],
     ["tests/test_audit_2026_10_22.py::test_gate_key_is_stable_across_restart_and_bound_to_the_chip", "tests/test_transactional.py"]),
    ("4", "hs", "an approval releases a hold from a replaced policy, and a new policy keeps old holds",
     [("hardware_ref/gate.py",
       "        if hold.get(\"policy_id\") != self.policy_id:",
       "        if False:"),
      ("hardware_ref/gate.py",
       "            for h in stale:\n                del self.state.holds[h]\n",
       "            stale = []\n")],
     ["tests/test_audit_2026_10_22.py::test_old_hold_cannot_be_approved_after_the_policy_tightens",
      "tests/test_audit_2026_10_22.py::test_a_hold_whose_policy_changed_is_refused_even_if_it_survived"],
     ["tests/test_audit_2026_10_22.py::test_a_hold_under_the_current_policy_still_approves", "tests/test_gate.py::test_hold_and_approval_flow"]),
    ("5", "hs", "the endpoint accepts any gate-signed epoch (no high-water mark)",
     [("hardware_ref/ledger.py",
       "            if version < cur_v or (version == cur_v and cur is not None and policy_id != cur):",
       "            if False:")],
     ["tests/test_audit_2026_10_22.py::test_replayed_old_epoch_is_refused_and_the_old_ticket_stays_dead"],
     ["tests/test_transactional.py::test_ticket_from_a_previous_policy_epoch_is_refused"]),
    ("5-commit", "hs", "the gate commits a ticket from a policy it has replaced",
     [("hardware_ref/gate.py",
       "            if p.get(\"policy_id\") != self.policy_id:\n                # the gate's own half",
       "            if False:\n                # the gate's own half")],
     ["tests/test_audit_2026_10_22.py::test_the_gate_refuses_to_commit_a_ticket_from_a_replaced_policy"],
     ["tests/test_transactional.py::test_allowed_payment_reserves_commits_and_executes"]),
    ("5b", "hs", "the gate reloads an older governance-signed policy",
     [("hardware_ref/gate.py",
       "            if version < self.state.data[\"policy_version\"]:",
       "            if False:"),
      ("hardware_ref/gate.py",
       "            if version == self.state.data[\"policy_version\"] and self.policy_id is not None and new_id != self.policy_id:",
       "            if False:")],
     ["tests/test_audit_2026_10_22.py::test_gate_refuses_an_older_governance_policy"],
     ["tests/test_audit_2026_10_22.py::test_reloading_the_same_document_is_fine_and_restart_keeps_the_newest_policy"]),
    ("5c", "hs", "an older revocation list replaces a newer one",
     [("hardware_ref/attest.py",
       "        newer_or_same(\"revocation-list\", payload, self._high_water)",
       "        pass")],
     ["tests/test_audit_2026_10_22.py::test_an_old_revocation_list_cannot_unrevoke_a_device"],
     ["tests/test_root_attest.py"]),
]


def junit(xml_path: str) -> dict[str, tuple[str, str]]:
    """test id -> (outcome, exception type) from pytest's junit xml."""
    out = {}
    if not os.path.exists(xml_path):
        return out
    for tc in ET.parse(xml_path).getroot().iter("testcase"):
        name = tc.get("classname", "").replace(".", "/") + ".py::" + tc.get("name", "")
        f, e = tc.find("failure"), tc.find("error")
        if f is not None:
            msg, t, body = f.get("message") or "", f.get("type") or "", f.text or ""
            ex = t.split(".")[-1] if t else ""
            if "DID NOT RAISE" in msg or "DID NOT RAISE" in body:
                ex = "Failed"
            elif not ex:
                # pytest leaves `type` empty for a plain failed assert; the traceback names the exception
                last = [ln for ln in body.splitlines() if ln.startswith("E ") and "Error" in ln]
                if msg.startswith("assert") or "AssertionError" in body:
                    ex = "AssertionError"
                elif last:
                    ex = last[-1][1:].strip().split(":")[0]
                else:
                    ex = msg.split(":")[0].strip() or "unknown"
            out[name] = ("failed", ex or "AssertionError")
        elif e is not None:
            out[name] = ("error", (e.get("type") or e.get("message") or "error").split(".")[-1])
        elif tc.find("skipped") is not None:
            out[name] = ("skipped", "")
        else:
            out[name] = ("passed", "")
    return out


def run_pytest(root: str, tests: list[str], py: str) -> dict[str, tuple[str, str]]:
    fd, xml = tempfile.mkstemp(suffix=".xml")      # never inside the repository
    os.close(fd)
    os.unlink(xml)
    subprocess.run([py, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}", *tests],
                   cwd=root, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": root})
    try:
        return junit(xml)
    finally:
        if os.path.exists(xml):
            os.unlink(xml)


def copy_tree(src: str, dst: str) -> None:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.egg-info", "build", ".agents", "node_modules", "results", "hw"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hs", default=os.path.join(os.path.dirname(SG), "hardware-and-silicon"))
    ap.add_argument("--out", default=os.path.join(SG, "audit", "external-2026-10-22", "EVIDENCE.md"))
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--hs-python", default=None)
    a = ap.parse_args()
    roots = {"sg": SG, "hs": os.path.abspath(a.hs)}
    pys = {"sg": a.python, "hs": a.hs_python or a.python}
    rows, ok_all = [], True
    tmp = tempfile.mkdtemp()
    try:
        for fid, repo, undo, edits, regress, positive in FINDINGS:
            work = os.path.join(tmp, f"{repo}-{fid}")
            copy_tree(roots[repo], work)
            applied = True
            for rel, fixed, old in edits:
                p = os.path.join(work, rel)
                s = open(p, encoding="utf-8").read()
                if s.count(fixed) != 1:
                    applied = False
                    print(f"[{fid}] could not find the fix in {rel}: {fixed[:60]!r}")
                    break
                open(p, "w", encoding="utf-8").write(s.replace(fixed, old))
            res = run_pytest(work, regress, pys[repo]) if applied else {}
            bad = []
            for t in regress:
                got = res.get(t)
                if got is None or got[0] != "failed" or got[1] not in INTENDED:
                    bad.append(f"{t.split('::')[-1]}: {got[0] + ' ' + got[1] if got else 'not run'}")
            pos = run_pytest(roots[repo], positive, pys[repo])
            pos_bad = [t for t, (o, _) in pos.items() if o != "passed"] or ([] if pos else ["no positive tests ran"])
            good = applied and not bad and not pos_bad
            ok_all &= good
            reasons = sorted({res[t][1] for t in regress if t in res and res[t][0] == "failed"})
            rows.append((fid, repo, undo, len(regress), sum(1 for t in regress if res.get(t, ("",))[0] == "failed"),
                         ", ".join(reasons) or "-", len(pos), "yes" if not pos_bad else "NO: " + "; ".join(pos_bad[:3]),
                         "holds" if good else "DOES NOT HOLD: " + ("revert not applied" if not applied else "; ".join(bad[:3]))))
            print(f"[{fid}] {'ok' if good else 'NOT OK'}  regressions failing for an assertion: {rows[-1][4]}/{len(regress)}  legitimate still works: {rows[-1][7]}")
        # the audited snapshot itself, for the reference stack
        snap = os.path.join(tmp, "hs-11eb119")
        subprocess.run(["git", "-C", roots["hs"], "worktree", "add", "-q", snap, "11eb119"], check=True, capture_output=True)
        shutil.copy(os.path.join(roots["hs"], "tests", "test_audit_2026_10_22.py"), os.path.join(snap, "tests"))
        res = run_pytest(snap, ["tests/test_audit_2026_10_22.py"], pys["hs"])
        subprocess.run(["git", "-C", roots["hs"], "worktree", "remove", "--force", snap], capture_output=True)
        snap_rows = sorted(res.items())
        wrong = [t for t, (o, ex) in snap_rows if o == "error" or (o == "failed" and ex not in INTENDED)]
        ok_all &= not wrong and sum(1 for _, (o, _) in snap_rows if o == "failed") >= 9
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    md = ["# Evidence: each regression fails for the intended reason",
          "",
          "Generated by `python3 tools/audit_evidence.py`. For each implementation finding the fix is reverted on a",
          "scratch copy of the fixed tree (the revert is written out in the script), the finding's regression tests are",
          "run there and must fail with an assertion (`AssertionError`, or pytest's `DID NOT RAISE`, shown as `Failed`),",
          "never with an import, attribute, type or name error; and the finding's legitimate-operation tests must pass",
          "on the fixed tree.",
          "",
          "| Finding | Repo | What the revert restores | Regressions failing for an assertion | Failure types | Must-pass tests on the fixed tree (legitimate operations, and hardening of new rules) | All pass | Verdict |",
          "|---|---|---|---|---|---|---|---|"]
    for fid, repo, undo, n, nf, why, npos, works, verdict in rows:
        md.append(f"| {fid} | {'safety-governor' if repo == 'sg' else 'hardware-and-silicon'} | {undo} | {nf} of {n} | {why} | {npos} | {works} | {verdict} |")
    md += ["", "## The reference stack's regression file on the audited snapshot `11eb119`", "",
           "| Test | Outcome on 11eb119 | Failure type |", "|---|---|---|"]
    for t, (o, ex) in snap_rows:
        md.append(f"| `{t.split('::')[-1]}` | {o} | {ex or '-'} |")
    md += ["", "The governor's regressions cannot run on `dccc1e0` unchanged, because the fix changed the signing interface",
           "(every signed command now names itself), so the revert table above is the evidence for the governor's findings;",
           "`audit/external-2026-10-22/repro_sg.py` shows the old behaviour on `dccc1e0` itself through the old interface.",
           "", f"Overall: {'every regression fails for the intended reason and every legitimate path still works' if ok_all else 'SOMETHING DOES NOT HOLD (see the table)'}."]
    open(a.out, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("wrote", a.out)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
