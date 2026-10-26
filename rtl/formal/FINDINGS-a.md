# WAVE-FORMAL-PROOFS-ON-VERILOG findings, second set (mailbox, cap_table, ticket_store, epoch_reg, monotonic_counter, lifecycle)

Each open finding has a property file under `findings_a/` that `python -m rtl.formal` must see FAIL by a
bounded-check assertion. If one starts to pass, the run says NOT REPRODUCED and fails, so this list can't go stale
quietly.

## Fixed

- **RTL-DEBUG-WINDOW-AFTER-RESET, lifecycle: a debug window after every reset.** The register reset to TEST and
  `debug_grant = debug_req & (state < PRODUCTION)`, so a chip whose fuses said PRODUCTION answered debug from reset
  release until firmware strobed `load`. Fix: a `loaded` flag; debug needs a fuse load since the last reset.
  Regression: `test_no_debug_window_after_reset_on_a_production_chip` (rtl/tests/test_blocks_a.py), plus the first
  lifecycle mutant, which puts the window back. One existing test expected debug straight after reset; it now loads
  the fuses first. This is the same bug the conformance suite found as its CONFORMANCE-DEBUG-BEFORE-FUSE-LOAD.
- **RTL-COUNTER-WRAPPED-TO-ZERO, monotonic_counter: wrap to zero.** `value + 1` wrapped to 0, and the top was reachable in two cycles by
  loading an all-ones high-water mark through `load_hwm`. Fix: saturate. Regression:
  `test_counter_saturates_instead_of_wrapping`, plus the first monotonic mutant. Same bug as conformance CONFORMANCE-MONOTONIC-COUNTER-WRAPS.

## Open

- **RTL-COUNTER-ROLLBACK-ACROSS-RESET: rollback across a reset.** The counter returns to the fuse mark, not its last value. Firmware obligations
  nobody has written down yet: strobe `load_hwm` before anything reads the counter, and burn the mark often enough.
  Reproducer: `findings_a/monotonic_counter_reset_rollback.sv`.
- **RTL-OLD-EPOCH-RECOMMITTED: an old epoch can be committed again.** epoch_reg has no order and takes any quorum commit, including an old
  image. Anti-rollback lives in firmware (govsim `bump_policy`), not in hardware. Reproducer:
  `findings_a/epoch_reg_old_epoch_returns.sv`.
- **RTL-RESET-EMPTIES-TICKET-STORE: a reset empties the used-ticket store.** It's volatile with no restore path, so a used ticket gets in again
  after a reset. The spec gives this memory to firmware and authenticated non-volatile storage. Reproducer:
  `findings_a/ticket_store_reset_replay.sv`.
- **RTL-ZERO-BYTE-SPENT-LOOKUP: a zero-byte lookup passes on a spent capability.** docs/07 says "budget > 0", docs/04 says "refuses at zero";
  the RTL checks `budget >= bytes`, so 0 bytes on an empty entry is allowed, and exhausted entries stay valid.
  Reproducer: `findings_a/cap_table_zero_budget.sv`.
- **RTL-EXPIRED-CAPABILITIES-RETURN: expired capabilities come back.** Expiry is checked only on lookup, against `now`. top.py wires
  `now = mono[:32]`, the low 32 bits of the microsecond counter, which wrap every 71.6 minutes, and then stale
  entries allow again. Fix options: a coarse tick, a wider compare, or a sweep that drops expired entries.
  Reproducer: `findings_a/cap_table_expiry_comes_back.sv`.
- **RTL-RESET-ZEROES-MAILBOX-SEQUENCES: a reset zeroes the mailbox sequence numbers.** `last_seq` resets to 0 with no restore, so old signed frames
  replay. The epoch-exempt CLEAR passes every RTL check; only firmware's chip-id and expiry checks remain.
  Reproducer: `findings_a/mailbox_reset_replay.sv`.
- **RTL-MAILBOX-FRAME-NOT-HELD: the mailbox doesn't hold the frame still.** It checks `frame_seq`, `key_slot`, `cmd`, epoch and needs_run at
  the doorbell, then records the live values at sig_done. `running` is sampled only at the doorbell, so a halt
  during the signature check doesn't stop the dispatch. The mailbox proof states "fields hold still" as an
  assumption, out loud. Reproducers: `findings_a/mailbox_unlatched_frame.sv`, `findings_a/mailbox_halt_during_verify.sv`.
  Suggested fix: latch at the doorbell and re-check `running` at sig_done.
- **F10: spec text.** docs/04 section 2 lists MBOX_STATUS 0 to 6, without 7; in the RTL status 7 covers only the
  command byte. govsim checks NOT_RUNNING before the sequence check (`Governor.command`) and the RTL checks it third,
  while docs/04 says the two use the same order.

RTL-COUNTER-ROLLBACK-ACROSS-RESET, RTL-RESET-EMPTIES-TICKET-STORE and RTL-RESET-ZEROES-MAILBOX-SEQUENCES are the same shape: the circuit forgets on reset what the spec says firmware and non-volatile memory
must remember. They are open until that firmware exists and is tested against these reproducers.
