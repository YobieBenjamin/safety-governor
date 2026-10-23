# Conformance findings: where the RTL, the model or the spec disagree

Every finding here has at least one reproducer in `rtl/conformance/` that asserts what the spec requires and,
on today's code, **fails by assertion**. `python -m rtl.conformance` runs them all; if a reproducer ever starts
passing (someone fixed it), the run fails until this file is updated, so the record cannot go stale quietly.
Nothing in `rtl/governor_rtl/` was changed on this branch. Fixes are suggested, not made.

Who disagrees with whom is stated per finding: RTL vs spec, RTL vs model (govsim), model vs spec, or the spec
against itself. Severity is my call: **high** (a safety property fails), **medium** (a stated rule fails in a
reachable case), **low** (edge case, unreachable in practice, or a reporting difference).

| Id | Severity | What | Who disagrees |
|---|---|---|---|
| F-01 | low | Mailbox: where the run-state check sits in the order | RTL vs model; spec silent |
| F-02 | low | Mailbox: sequence number 0 on a key's first frame | RTL vs model; spec silent |
| F-03 | low | Model's heartbeat path checks the signature first | model vs spec and RTL |
| F-04 | low | Model's CLEAR handler reports one reason for every failure | model vs spec |
| F-05 | high, **closed** | CLEAR and tamper in the same cycle: CLEAR wins, the tamper is lost (fixed: tamper outranks CLEAR, branch fix/halt) | RTL vs spec and model (lead a) |
| F-06 | high | Lifecycle reads TEST and grants debug before the fuse load | RTL vs spec (lead b) |
| F-07 | medium | A signed HALT to a governor already in SAFE | RTL vs spec; model vs spec, differently |
| F-08 | low | The "millisecond" tick is 1,024 microseconds | RTL vs spec |
| F-09 | low | A zero-byte lookup passes at zero budget | RTL and model vs spec |
| F-10 | medium | Capability table holds two entries for one key | RTL vs spec and model |
| F-11 | medium, **closed** | Meter counters wrap at 48 bits (fixed: counters saturate, `acce09f`) | RTL vs spec |
| F-12 | low | Monotonic counter wraps from an all-ones high-water mark | RTL vs spec |
| F-13 | low | Mailbox does not latch the frame between doorbell and verdict | an RTL interface assumption the spec never states |
| F-14 | low | Register map's MBOX_STATUS row has no status 7 | spec vs spec |
| F-15 | low | 07 says switch_open sets on loop_lost; RTL and model only do it in RUN or THROTTLE | spec text vs RTL and model |

---

## F-01 Mailbox: where the run-state check sits in the order

**The lead was:** the RTL checks sequence, epoch, run state, then signature; govsim checks a different order, so
the reported reason can differ.

**What I found:** half right. `_check_signed` in `govsim/governor.py` checks in exactly the RTL's order for the
four checks it does (sequence, epoch, signature, what was signed). The difference is the run-state check. The
model does it first, in `Governor.command`, before `_check_signed` is ever called. The RTL does it third, after
sequence and epoch. docs/04 section 3 gives the order "sequence, epoch, signature, what was signed" and says the
model and the RTL "check in the same order and a test in each suite pins it", but it never says where run state
goes. The spec is silent and the two implementations picked different places.

**When it shows:** only for a command class that needs RUN (REQUEST, SIGN_OUTPUT, CAP_REQUEST, BEGIN_MODEL,
END_MODEL, ROSTER_JOIN) arriving while the governor is not in RUN, that also has a bad sequence number or a stale
epoch. The RTL says 4 (bad sequence) or 5 (bad epoch); the model says `mailbox.governor_not_running`. Both refuse;
only the reason differs. In the 4,000-frame random run, 253 frames fall in this class.

**Reproducers:** `test_diff_finding_replayed_request_while_not_running`,
`test_diff_finding_stale_request_while_not_running`.

**Noted, as asked:** the RTL reports sequence, epoch and run-state reasons **before the signature is verified**
(the crypto core is never asked; `verify_req` stays low). The model does the same for sequence and epoch. So an
unauthenticated sender can learn from MBOX_STATUS whether a sequence number is still fresh for a key slot and
whether the governor is running. Most of that is public anyway (EPOCH, STATE and MBOX_SEQ for slot 0 are readable
CSRs). The upside is real: a flood of replays never costs a 17 ms signature verification. I would keep the order
and write it down.

**Suggested fix:** decide where run state goes, put it in docs/04 section 3, and move one implementation to match
(moving the model's run check after `_check_signed` is the smaller change).

## F-02 Mailbox: sequence number 0 on a key's first frame

The model starts each key's last-accepted sequence at -1 (`self.mbox_seq.get(signer, -1)`), so a first frame with
seq 0 is accepted. The RTL's `last_seq` registers reset to 0 and the check is `frame_seq > last_seq`, so seq 0 is
never accepted on any key. The spec says "greater than the last accepted one" and does not say what that is before
anything has been accepted. Harmless (every signer the model uses starts at 1), but the two disagree.

**Reproducer:** `test_diff_finding_first_sequence_number_zero`. **Fix:** say "sequence numbers start at 1" in docs/04
and start the model at 0.

## F-03 Model's heartbeat path checks the signature first

HEARTBEAT does not go through `_check_signed` in the model; `_heartbeat` checks signature, then the signed type,
then sequence, then epoch. The spec's mailbox order (sequence, epoch, signature, type) applies to every frame, and
the RTL applies it to heartbeats like anything else. So a replayed heartbeat with a broken signature is 4 in the RTL
and `heartbeat.bad_signature` in the model, and a frame signed as something else presented as HEARTBEAT is 7 (wrong
command) in the RTL and `heartbeat.bad_signature` in the model. 54 frames in the random run.

**Reproducers:** `test_diff_finding_replayed_forged_heartbeat`, `test_diff_finding_heartbeat_signed_as_something_else`.
**Fix:** run heartbeats through `_check_signed` (keeping the staged-epoch acceptance), or say in docs/04 that the
heartbeat path has its own order.

## F-04 Model's CLEAR handler reports one reason for every failure

The spec: "The first failing check is the reason reported." `_cmd_clear` turns every `_check_signed` failure into
`clear.unauthorized`, so a replayed CLEAR is reported as unauthorized, not as a bad sequence. The RTL's MBOX_STATUS
would still say 4, so the silicon side is fine; the model's reason codes are not.

**Reproducer:** `test_model_finding_clear_collapses_reasons`. **Fix:** return `why` from `_check_signed`, or log both.

## F-05 CLEAR and tamper in the same cycle (lead a) (closed)

**What the spec requires.** docs/07 section 4: tamper (mesh cut, glitch injection, temperature excursion) means
"keys zeroized, state SAFE". docs/07 section 3: the rung "never descends without clear". The FMEA row for a clock
glitch: "Zeroize, SAFE". Nothing anywhere lets a CLEAR outrank a tamper. The model agrees: `tamper_event` goes to
SAFE and zeroizes, and every command after that, CLEAR included, is refused with `tamper.zeroized`
(`test_model_tamper_is_safe_and_unclearable` passes).

**What the RTL does.** In `halt.py` the `clear` branch is the first `If`, ahead of `tamper`. If an authorized CLEAR
strobe and a tamper arrive in the same cycle, the sequencer goes to HALTED_INITIAL with cause none. Two cases:

- tamper held as a level (a cut mesh stays cut): one cycle in HALTED_INITIAL, then SAFE. During that cycle the
  levers are the boot rung's (brake, reset, power off), so the GPU is not released. Ugly but safe
  (`test_level_tamper_with_clear_settles_in_safe` passes).
- tamper as a one-cycle strobe (a glitch detector pulse): the tamper is gone. The sequencer sits in HALTED_INITIAL
  with no cause, and if a heartbeat is live and the loop is closed it **re-arms and goes back to RUN**. The
  reproducer shows exactly that: state 1 (RUN), cause 0, three cycles later.

Related: the RTL will also take a CLEAR strobe out of SAFE when the cause is tamper. It relies on the firmware
never strobing CLEAR after a tamper (in the model the keys are gone, so no CLEAR can verify). That is
firmware-owned (R-074), but the hard core could carry it cheaply.

**Reproducers:** `test_finding_clear_and_tamper_pulse_same_cycle_ends_safe`,
`test_finding_clear_and_tamper_same_cycle_never_leaves_safe_rung`.

**Suggested fix:** move the `tamper` branch above `clear` in `HaltSeq.elaborate`, make the tamper cause sticky (CLEAR
does nothing while `cause == C_TAMPER`), and add a formal property for it next to `rtl/formal/halt_seq.sv`.

**Closed** on branch fix/halt (23 October 2026): the tamper branch now comes before the CLEAR branch in `HaltSeq`, both reproducers pass and stay as guards, and the halt proof's "unless cleared that same cycle" exception, which excused this bug, is gone (`rtl/formal/halt_seq.sv`, with a mutant that puts CLEAR first again and is caught).

## F-06 Lifecycle register between reset and the fuse load (lead b)

**What the spec requires.** docs/07 section 1, H15: "Production silicon has no debug path." Section 3: in
PRODUCTION, `debug_grant` is never asserted. The register map says LIFECYCLE is fuse-backed and monotone.

**What the RTL does.** `Lifecycle.state` is a plain register that resets to 0, which is TEST. It takes the fused
value only when something strobes `load`, and in `GovernorCore`, `life.load` is a port the firmware drives. So from
reset until the firmware gets round to the fuse load, a part fused PRODUCTION reads LIFECYCLE = 0 (test) and
`debug_grant = debug_req & (state < PRODUCTION)` is 1. A debug request in that window is granted. After the load it
is dead for good (`test_lifecycle_after_load_debug_is_dead` passes).

This is the classic lifecycle-controller mistake. Real designs avoid it by resetting to the most restrictive state
and sensing the fuses in hardware before anything can ask (OpenTitan's lifecycle controller keeps debug off until
the OTP state has been read and decoded).

**Reproducers:** `test_finding_lifecycle_debug_before_fuse_load`, `test_finding_core_reports_test_lifecycle_before_fuse_load`.

**Suggested fix:** reset `state` to a most-restrictive "not yet loaded" value, or add a `loaded` flag that holds
`debug_grant` at 0 until the fuse load, and drive the load from a reset sequencer rather than firmware.

## F-07 A signed HALT to a governor already in SAFE

A governor whose heartbeat lapsed climbs THROTTLE, HALT, SAFE on its timers with its loop switch closed, which is
right: local causes do not stop the rack. Now the authority sends that governor a signed HALT, a loop-opening cause
that is supposed to stop the whole domain.

- **RTL:** `cmd_halt` is gated with `state != SAFE`, so it is ignored. The state stays SAFE, the loop switch stays
  closed, and this governor does not stop the rest of the domain. docs/07 section 3 says `switch_open` "sets on ...
  cmd_halt". Reproducer: `test_finding_cmd_halt_in_safe_opens_the_loop`.
- **Model:** `enter_safe_mode` applies the HALT rung because the cause opens the loop, so it moves **down** from SAFE
  to HALT and turns slot power back on (`pwr_en` true). The loop does open. docs/07 section 3 says the rung never
  descends without CLEAR. Reproducer: `test_model_finding_halt_in_safe_does_not_descend`.

Each gets half of it right. The spec wants both: stay in SAFE, and open the loop.

**Suggested fix (RTL):** let `cmd_halt` set `switch_open` and the cause in every state, and change the state only if
the new rung is higher. **(Model):** in `enter_safe_mode`, never apply a rung lower than the current one; open the
loop separately.

## F-08 The "millisecond" tick is 1,024 microseconds

docs/04 section 9: the RTL timers "run on a millisecond tick derived from the microsecond counter"; HB_REMAIN is
"Heartbeat time remaining, milliseconds". `top.py` makes the slow strobe every 2^10 = 1,024 microsecond ticks. So
every timer stated in milliseconds runs 2.4 percent long: a 5 s heartbeat expiry becomes 5.12 s, T_throttle 30 s
becomes 30.72 s, T_halt 300 s becomes 307.2 s. The direction matters: a lapsed heartbeat keeps the GPU running
120 ms longer than the policy says.

**Reproducer:** `test_finding_heartbeat_expires_on_time` (a 2 ms window still live after 2,001 us).
**Fix:** a divide-by-1,000 counter, or have the firmware scale every window by 1,000/1,024 and say so in docs/04.

## F-09 A zero-byte lookup passes at zero budget

docs/04 section 5: a lookup "refuses at zero". With the budget spent to exactly 0, a zero-byte lookup is allowed by
the RTL (`budget < bytes` is false for 0 < 0), and the model's `Switch` does the same. Whether a zero-byte transfer
matters depends on the switch; the text and the code disagree either way.

**Reproducer:** `test_finding_cap_refuses_at_zero_budget`. **Fix:** refuse when `budget == 0`, or reword the spec to
"refuses a lookup larger than the remaining budget".

## F-10 Capability table holds two entries for one key

docs/04 section 5: the table is "a content-addressable memory keyed on (point, peer, dir)". The model's `Switch`
treats the key as unique: programming the same key again replaces the entry. The RTL inserts into the first free
slot without looking for an existing entry, and the lookup's priority encoder answers from the lowest slot. Two
consequences, one in each direction:

- **fail-open:** tightening a capability (1,000 bytes reprogrammed to 10) leaves the old 1,000 usable.
  Reproducer: `test_finding_cap_reprogramming_a_key_replaces_it`.
- **fail-closed:** after an epoch switch in RUN, the firmware re-derives the port under the new tag, but the stale
  entry sits in a lower slot and is hit first, so the new, valid capability is refused `R_STALE_EPOCH`. Stale
  entries also fill the 8 slots, since nothing removes them except expiry-on-lookup or `clear_all`.
  Reproducer: `test_finding_cap_rederived_after_epoch_switch_is_usable`.

The random differential against the model's `Switch` (`test_diff_cap_table_random_against_model_switch`) agrees on
every one of 1,280 lookups and every remaining budget, as long as keys never overlap; overlap is exactly this finding.

**Fix:** on insert, overwrite a matching valid entry instead of taking a free slot; on an epoch switch, drop entries
whose tag no longer matches (or clear the table and re-derive).

## F-11 Meter counters wrap at 48 bits (closed)

docs/07 section 3: meter counters "only increment". The register map gives each counter 64 bits; the prototype core
uses 48 (docs/04 section 5 says so). A 48-bit bytes-out counter wraps after 2^48 bytes, about 281 TB, which a
long-lived slot serving a busy model can reach. The wrap looks like the counter going backwards.

**Reproducer:** `test_finding_meter_counter_wraps_at_48_bits`. **Fix:** saturate instead of wrapping (and raise an
alarm), or use 64 bits in the product.

**Closed.** The L7 group B proofs found the same bug independently (one big add could move a counter down) and the
meter now saturates at its maximum (merge `acce09f`, regression in `rtl/tests/test_l7b_regressions.py`). The
reproducer above now passes and stays in the suite as a guard. The alarm on saturation is not added yet.

## F-12 Monotonic counter wraps from an all-ones high-water mark

The 64-bit counter cannot wrap by counting (that takes 584,000 years). But `load_hwm` accepts any value above the
current one, and a fuse array that reads all ones (erased or failed) loads 2^64 - 1; the next tick wraps the
governor's clock to 0, which every expiry check would then misread.

**Reproducer:** `test_finding_mono_wraps_from_an_all_ones_high_water_mark`. **Fix:** saturate at the top, and treat an
all-ones high-water mark as a fuse read failure (boot refused, as the FMEA row already says for fuse failures).

## F-13 Mailbox does not latch the frame between doorbell and verdict

The Mailbox reads `frame_seq`, `key_slot` and `cmd` from its ports at the doorbell (to check them) and again at
`sig_done` (to store and dispatch them). It never latches them. If the values on the ports change while the crypto
core works, the RTL dispatches a frame whose sequence was never checked, and `last_seq` moves backwards (10 to 3 in
the reproducer), which reopens every sequence number in between. The invariant in docs/07 ("No command is
dispatched unless frame_seq is above the key slot's last accepted sequence") holds only if whoever drives those
ports holds them steady, and nothing in the spec says so.

Today the firmware drives those ports, so this is an interface assumption, not something a host can reach
directly. It is the kind of assumption that breaks when someone later wires the ring buffer straight to the ports.

**Reproducer:** `test_finding_mailbox_sequence_never_moves_backwards`. **Fix:** latch the frame fields on the doorbell
and use the latched copy in VERIFY, or write the hold requirement into docs/04 and the block's docstring.

## F-14 Register map's MBOX_STATUS row has no status 7

docs/04 section 3 and the RTL both use MBOX_STATUS 7 for a good signature over a different command, and section 3
says "RTL status 7". The register map row for MBOX_STATUS still lists 0 to 6.

**Reproducer:** `test_finding_spec_status_table_lists_status_7`. **Fix:** add "7 wrong command" to the row.

## F-15 07 says switch_open sets on loop_lost; RTL and model only do it in RUN or THROTTLE

docs/07 section 3: `switch_open` "sets on `loop_lost`, `tamper` or `cmd_halt`". The RTL acts on `loop_lost` only in RUN
or THROTTLE (`in_run`), and so does the model's `sense_loop`. A governor already in HALT on a local cause, switch
closed, that sees the loop drop keeps its switch closed. The loop is already open somewhere, so the domain stops
anyway; the effect is that this governor will not hold the loop open itself once the break is repaired. RTL and model
agree, so I read this as the spec sentence being broader than the design.

**Reproducer:** `test_finding_loop_lost_in_halt_sets_switch_open`. **Fix:** narrow the sentence in docs/07 to "sets on
loop_lost in RUN or THROTTLE", or widen both implementations.

---

## Checked and found to agree

So the list above is not read as "everything else went unexamined":

- Mailbox, hand-written frames from the spec: good HALT, replayed HALT, HALT with a stale epoch (exempt), a heartbeat
  presented as CLEAR (the 22 October case), stale REQUEST, forged REQUEST, REQUEST while not running, replayed and
  forged, stale and forged, not running and forged, CLEAR for another chip, expired CLEAR, two keys with independent
  counters, a good heartbeat. RTL and model agree on the reason and on the stored sequence for all fourteen.
- Mailbox, 4,000 random frames over twelve commands: 3,690 agree outright; every one of the other 310 is F-01, F-02
  or F-03. No unexplained disagreement.
- Capability table vs the model's `Switch`: agree on all 1,280 random lookups and every remaining budget with
  non-overlapping keys.
- Levers per rung: RTL and model identical for all five rungs. Boot state: identical.
