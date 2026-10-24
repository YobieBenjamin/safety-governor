# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Test-suite sensitivity: one-line mutants of the Amaranth source, each of which must make the conformance test
for its requirement FAIL BY ASSERTION. A mutant that the test survives means the test does not really check that
line. A mutant that crashes the harness (an import, elaboration or tool error) is not a catch and is reported as
an error.

    python -m rtl.conformance.mutants N     # run mutant N in this process and print one JSON line

The runner (python -m rtl.conformance) starts one subprocess per mutant, so no mutant can leak into another run.
"""
from __future__ import annotations

import importlib
import inspect
import json
import os
import sys

# (requirement, source file in rtl/governor_rtl, old text (must occur once), new text, the test that must catch it)
MUTANTS: list[tuple[str, str, str, str, str]] = [
    # Registered name: REQUIREMENT-COUNTER-REFUSES-DECREMENT (old ID R-002 is kept because code matches on it)
    ("R-002", "monotonic.py", "self.refused.eq(self.dec_req)", "self.refused.eq(0)",
     "test_mono_decrement_request_refused_and_value_kept"),
    # Registered name: REQUIREMENT-COUNTER-FUSE-HIGH-WATER-MARK (old ID R-003 is kept because code matches on it)
    ("R-003", "monotonic.py", "with m.If(self.hwm > self.value):", "with m.If(self.hwm != self.value):",
     "test_mono_lower_high_water_mark_cannot_pull_back"),
    # Registered name: REQUIREMENT-MEASUREMENT-EXTEND-ONLY (old ID R-004 is kept because code matches on it)
    ("R-004", "measure_reg.py", "with m.If(self.extend):", "with m.If(self.extend | self.hash_done):",
     "test_meas_engine_output_without_request_ignored"),
    # Registered name: REQUIREMENT-EPOCH-CHANGES-ONLY-WITH-QUORUM (old ID R-007 is kept because code matches on it)
    ("R-007", "epoch_reg.py", "with m.If(self.commit & self.quorum_ok):", "with m.If(self.commit):",
     "test_epoch_commit_without_quorum_ignored"),
    # Registered name: REQUIREMENT-LIFECYCLE-MONOTONE-NO-DEBUG (old ID R-010 is kept because code matches on it)
    ("R-010", "lifecycle.py", "with m.If(self.advance_to > self.state):", "with m.If(self.advance_to != self.state):",
     "test_lifecycle_never_moves_down_by_advance"),
    # Registered name: REQUIREMENT-PRODUCTION-HAS-NO-DEBUG (old ID R-011 is kept because code matches on it)
    ("R-011", "lifecycle.py", "self.debug_grant.eq(self.debug_req & self.loaded & (self.state < PRODUCTION)),",
     "self.debug_grant.eq(self.debug_req & self.loaded & (self.state <= PRODUCTION)),", "test_lifecycle_debug_refused_in_production_and_later"),
    # Registered name: REQUIREMENT-CAPABILITY-REFUSES-ON-EXPIRY (old ID R-017 is kept because code matches on it)
    ("R-017", "cap_table.py", "with m.Elif(self.expiry[hit] <= self.now):", "with m.Elif(self.expiry[hit] < self.now):",
     "test_cap_refuses_at_expiry_and_drops_entry"),
    # Registered name: REQUIREMENT-CAPABILITY-REFUSES-STALE-TAG (old ID R-018 is kept because code matches on it)
    ("R-018", "cap_table.py", "with m.Elif(self.etag[hit] != self.epoch_tag):", "with m.Elif(0):",
     "test_cap_refuses_on_epoch_tag_mismatch"),
    # Registered name: REQUIREMENT-MAC-CHECKED-AT-INSERTION (old ID R-019 is kept because code matches on it)
    ("R-019", "cap_table.py", "with m.Elif(self.ins & self.mac_ok & found):", "with m.Elif(self.ins & found):",
     "test_cap_insert_needs_mac"),
    # Registered name: REQUIREMENT-BUDGET-NEVER-UNDERFLOWS (old ID R-020 is kept because code matches on it)
    ("R-020", "cap_table.py", "with m.Elif(self.budget[hit] < self.lk_bytes):", "with m.Elif(0):",
     "test_cap_refuses_more_than_remaining_budget"),
    # Registered name: REQUIREMENT-PORT-OPEN-ONLY-WITH-ENTRY (old ID R-024 is kept because code matches on it)
    ("R-024", "top.py", "c.clear_all.eq(self.halt.ports_closed)", "c.clear_all.eq(0)",
     "test_core_tables_empty_whenever_not_running"),
    # Registered name: REQUIREMENT-BURNED-TICKET-NEVER-ADMITTED (old ID R-027 is kept because code matches on it)
    ("R-027", "ticket_store.py", "m.d.comb += self.seen.eq(match)", "m.d.comb += self.seen.eq(0)",
     "test_ticket_seen_after_burn"),
    # Registered name: REQUIREMENT-HEARTBEAT-EXPIRES-ON-TIME (old ID R-029 is kept because code matches on it)
    ("R-029", "heartbeat.py", "m.d.sync += self.remaining.eq(self.remaining - 1)", "m.d.sync += self.remaining.eq(self.remaining - 0)",
     "test_hb_expires_on_the_window_th_tick"),
    # Registered name: REQUIREMENT-HEARTBEAT-RELOADS-ONLY-ON-VALID (old ID R-030 is kept because code matches on it)
    ("R-030", "heartbeat.py", "with m.If(self.hb_valid):", "with m.If(self.hb_valid | (self.window != 0)):",
     "test_hb_reload_only_on_valid"),
    # Registered name: REQUIREMENT-RUNG-CLIMBS-ON-CAUSES (old ID R-034 is kept because code matches on it)
    ("R-034", "halt.py", "with m.Elif((self.hb_expired | self.local_trip | self.cmd_throttle) & (self.state == RUN)):",
     "with m.Elif((self.hb_expired | self.cmd_throttle) & (self.state == RUN)):", "test_halt_local_trip_throttles"),
    # Registered name: REQUIREMENT-LEVERS-FOLLOW-RUNG (old ID R-036 is kept because code matches on it)
    ("R-036", "halt.py", "self.perst.eq((self.state == HALTED_INITIAL) | (self.state == HALT) | (self.state == SAFE)),",
     "self.perst.eq((self.state == HALTED_INITIAL) | (self.state == HALT)),", "test_halt_levers_follow_every_rung"),
    # Registered name: REQUIREMENT-SWITCH-CLOSES-ONLY-WHEN-ARMED (old ID R-037 is kept because code matches on it)
    ("R-037", "halt.py", "with m.Elif((self.state == HALTED_INITIAL) & (self.cause == C_NONE) & self.hb_ok):",
     "with m.Elif((self.state == HALTED_INITIAL) & (self.cause == C_NONE)):", "test_halt_no_arming_without_heartbeat"),
    # Registered name: REQUIREMENT-CLEAR-KEEPS-SWITCH-OPEN (old ID R-039 is kept because code matches on it)
    ("R-039", "halt.py", "m.d.sync += [self.state.eq(HALTED_INITIAL), self.cause.eq(C_NONE), self.timer.eq(0)]",
     "m.d.sync += [self.state.eq(HALTED_INITIAL), self.cause.eq(C_NONE), self.timer.eq(0), self.switch_open.eq(0)]",
     "test_halt_clear_does_not_close_the_switch_until_armed"),
    # Registered name: REQUIREMENT-CORE-BOOTS-HALTED-SAFE (old ID R-045 is kept because code matches on it)
    ("R-045", "halt.py", "self.switch_open = Signal(init=1)", "self.switch_open = Signal(init=0)",
     "test_core_boot_state_levers_and_switch"),
    # Registered name: REQUIREMENT-LOOP-LOSS-DEBOUNCE (old ID R-049 is kept because code matches on it)
    ("R-049", "halt_loop.py", "self.loop_lost.eq(self.count >= self.debounce)", "self.loop_lost.eq(self.count >= 1)",
     "test_loop_one_noisy_sample_is_not_a_loss"),
    # Registered name: REQUIREMENT-METER-HOST-WRITE-REFUSED (old ID R-051 is kept because code matches on it)
    ("R-051", "meter.py", "self.host_wr_refused.eq(self.host_wr)]", "self.host_wr_refused.eq(0)]",
     "test_meter_host_write_refused_and_flagged"),
    # Registered name: REQUIREMENT-SEQUENCE-ABOVE-LAST-ACCEPTED (old ID R-054 is kept because code matches on it)
    ("R-054", "mailbox.py", "m.d.comb += seq_ok.eq(self.frame_seq > self.last_seq[self.key_slot])",
     "m.d.comb += seq_ok.eq(self.frame_seq >= self.last_seq[self.key_slot])", "test_mbox_good_frame_dispatches_once"),
    # Registered name: REQUIREMENT-FRAME-EPOCH-MUST-MATCH (old ID R-055 is kept because code matches on it)
    ("R-055", "mailbox.py", "with m.Elif(~(self.epoch_match | self.epoch_exempt)):", "with m.Elif(~self.epoch_match):",
     "test_mbox_stale_epoch_refused_unless_exempt"),
    # Registered name: REQUIREMENT-SIGNED-PAYLOAD-NAMES-COMMAND (old ID R-057 is kept because code matches on it)
    ("R-057", "mailbox.py", "with m.If(self.sig_ok & (self.signed_cmd == self.cmd)):", "with m.If(self.sig_ok):",
     "test_mbox_signed_for_another_command_is_status_7"),
    # Registered name: REQUIREMENT-SEQUENCE-REGISTER-PER-KEY (old ID R-060 is kept because code matches on it)
    ("R-060", "top.py", "self.csr_rdata.eq(self.mbox.last_seq[0])", "self.csr_rdata.eq(self.mbox.last_seq[1])",
     "test_core_mbox_status_and_seq_csrs"),
    # Registered name: REQUIREMENT-MAILBOX-STATUS-CODES (old ID R-061 is kept because code matches on it)
    ("R-061", "mailbox.py", "with m.Elif(self.needs_run & ~self.running):", "with m.Elif(0):",
     "test_mbox_refused_when_not_running"),
    # Registered name: REQUIREMENT-ALARM-CLEAR-NEEDS-AUTHORIZATION (old ID R-070 is kept because code matches on it)
    ("R-070", "alarms.py",
     "m.d.comb += cleared.eq(self.alarms & ~(self.clear_mask & self.clear_authorized.replicate(len(self.alarms))))",
     "m.d.comb += cleared.eq(self.alarms & ~self.clear_mask)", "test_alarm_clear_needs_authorization"),
    # Operator signals, 23 October 2026
    # Registered name: REQUIREMENT-HALT-OPENS-LOOP-EVERY-RUNG (old ID R-144 is kept because code matches on it)
    ("R-144", "halt.py", "            m.d.sync += self.switch_open.eq(1)\n        with m.Elif(self.cmd_halt):",
     "            pass\n        with m.Elif(self.cmd_halt):", "test_calls_halt_opens_loop_from_every_rung"),
    # Registered name: REQUIREMENT-EXCLUDE-ONLY-WHILE-WAITING (old ID R-149 is kept because code matches on it)
    ("R-149", "halt.py", "with m.Elif(self.cmd_exclude & (self.state == HALTED_INITIAL) & (self.cause == C_NONE)):",
     "with m.Elif(self.cmd_exclude):", "test_calls_exclude_does_nothing_outside_waiting_for_first_heartbeat"),
    # Registered name: REQUIREMENT-HARDWARE-ALARMS-SEQUENCER-ONLY (old ID R-148 is kept because code matches on it)
    ("R-148", "top.py", "HW_ALARMS = (1 << ALARM_NO_FIRST_HEARTBEAT) | (1 << ALARM_EXCLUDED)", "HW_ALARMS = (1 << ALARM_EXCLUDED)",
     "test_calls_firmware_cannot_raise_the_hardware_alarm_bits"),
]

HERE = os.path.dirname(os.path.abspath(__file__))
RTL_SRC = os.path.join(os.path.dirname(HERE), "governor_rtl")


def apply(src_file: str, old: str, new: str) -> None:
    """Re-execute one block's source, with the mutation, inside its own module, and point every importer at it."""
    path = os.path.join(RTL_SRC, src_file)
    src = open(path, encoding="utf-8").read()
    if src.count(old) != 1:
        raise RuntimeError(f"mutant text not found exactly once in {src_file}: {old!r}")
    modname = "rtl.governor_rtl." + src_file[:-3]
    mod = importlib.import_module(modname)
    exec(compile(src.replace(old, new), path + " (mutant)", "exec"), mod.__dict__)
    pkg = importlib.import_module("rtl.governor_rtl")
    top = importlib.import_module("rtl.governor_rtl.top")
    for name, obj in list(mod.__dict__.items()):
        if inspect.isclass(obj) and obj.__module__ == modname:
            for other in (pkg, top):
                if name in other.__dict__:
                    setattr(other, name, obj)


def main(argv: list[str]) -> int:
    import warnings
    warnings.filterwarnings("ignore", message=".*created but never used.*")
    i = int(argv[0])
    req, src_file, old, new, test_name = MUTANTS[i]
    from . import load_tests
    from .framework import REGISTRY, run_one
    load_tests()
    t = next(t for t in REGISTRY if t.name == test_name)
    try:
        apply(src_file, old, new)
    except Exception as e:   # noqa: BLE001
        print(json.dumps({"i": i, "status": "error", "detail": f"mutant not applied: {e}"}))
        return 0
    o = run_one(t)
    print(json.dumps({"i": i, "status": o.status, "detail": o.detail[:300]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
