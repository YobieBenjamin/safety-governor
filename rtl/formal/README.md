# Formal proofs on the generated Verilog (L7)

**Status: written, not yet run in the authoring environment.** `rtl/formal/` holds the property
files and the job runner; the solver has not run here. `make formal` runs `run_formal.py`: for each
hard-core block it injects `<block>.svh` in front of the final `endmodule` of `rtl/gen/<block>.v`
(the checked-in Verilog is never edited), then runs SymbiYosys (`mode prove`, engine `smtbmc z3`): a
bounded check, then k-induction, which is an unbounded proof when the induction closes.
`make formal-<block>` runs one block; `make formal-equiv` runs only the netlist equivalence.

`sby`, `yosys` and `z3` are in the program's container; a plain checkout has only `z3`. Where a job's
tool is absent, `run_formal.py` prints `SKIP` for that job and still exits 0, with a banner saying
no property was checked. **A `SKIP` is not a `PROVED`**: a green `make formal` in a tool-less checkout
means "nothing was checked," and the properties are checked for real when `make formal` is run in the
container. Outcomes print in four classes so a green run is never mistaken for a proof that did not
run:

    PROVED  <job>     a property held (a `prove` task)
    GAP OK  <job>     a task marked `expect fail` found its counterexample: the RTL gap it documents
                     is real. This is a finding, not a PASS.
    SKIP    <job>     the tool the job needs is absent; it was not run
    FAIL    <job>     a property that should hold was broken, or an expected counterexample was not found

The first run in the container may need fixes to property syntax or induction strengthening; the
outcomes below say what each job *asserts*, not what a run reported.

Reset is assumed low (`assume(!rst)`): the properties are about operation, and a power loss is the
high-water mark's job (`m_P8_hwm_floor`).

## Property map

P-numbers are those of `proofs/core_invariants.py` (the model-level theorems). A label marked
**analogue** states the same *spirit* on the RTL but is not the model's statement verbatim -- the
model's P6/P7/P13 are about "nothing executes while halted or heartbeat-lost," whereas the RTL blocks
below are about the rung and the levers that *enforce* it. "CP" is the commit-point protocol
(`proofs/commit_point.py`): of it the RTL holds only the hold (the rung does not leave HALT/SAFE
without `clear`) and the binding of a clearance to its command (the mailbox's check order).

| Block | Assertion prefix | P / CP | What it asserts |
|---|---|---|---|
| `ticket_store` | `t_P3_*` | P3 | a burned id stays stored and unchanged; no duplicate ids; a burned id is always `seen` and never burns twice -- the id is a solver-chosen constant, so the claim is for every id; a full store refuses |
| `epoch_reg` | `e_P9_*`, `e_P10_*` | P9, P10 (analogue) | the register changes only on `commit` with `quorum_ok`, then loads `new_epoch`; the host port has no effect. P10 here is an analogue: the block sees only `quorum_ok`, not the signature count |
| `monotonic_counter` | `m_P8_*` | P8 | the value never decreases (the one exception is the 2^64 wrap, below); `load_hwm` raises it to at least the fuse mark; `dec_req` changes nothing |
| `halt_seq` | `h_P5_*` | P5 | the rung never descends without `clear`; HALT and SAFE absorb; boot is the safe bottom with every lever held |
| | `h_P6_*` | P6 (analogue) | RUN is entered only when armed (no cause, `hb_ok`, `loop_sense`); the loop switch closes only when armed, opens on tamper, loop loss and command halt, and `clear` does not close it |
| | `h_P7_*`, `h_P13_*` | P7, P13 (analogue) | brake, reset, power and ports follow the rung exactly; every rung but RUN applies the brake and closes the ports -- the levers that keep nothing passing while halted |
| `cap_table` | `c_P1_*` | P1, P4 | `allow` only against an entry that matches (point, peer, dir), is unexpired, has the current epoch tag and enough budget; an entry appears only by an insert with `mac_ok`; the budget never rises on lookup (no underflow) |
| `mailbox` | `b_P3_*`, `b_P4_*`, `b_P12_*`, `b_P13_*`, `b_CP_*` | P3, P4, P12, P13, CP | dispatch only on a verified signature over the same command (`b_P12`); sequence above the slot's last (`b_P3`), epoch matched or exempt (`b_P4`); a `needs_run` command not dispatched while the rung is not RUN (`b_P13`, analogue); the checks run in order and the first failure is the status (`b_CP`); a wrong-command or bad-signature frame consumes nothing; the last-seq registers only rise. `b_P13` and the mailbox `b_P3`/`b_P12` default task lean on the front-end contract below |

## Tasks that are expected to fail (findings about the RTL)

Each is a `bmc` task with `expect fail`: the run prints `GAP OK` when the counterexample is found
(that is the task succeeding -- the documented gap is real), and is not a `PASS`. They say which
assumption the proofs lean on, and are the disproof of the three candidate RTL gaps.

| Task | Finding |
|---|---|
| `monotonic_counter:wrap` | `inc` at 2^64-1 wraps to 0. Unreachable in practice (2^64 microseconds), but the block does not saturate. The `prove` task carries that one step as an escape clause, so P8 asserts as "never decreases except the wrap"; the `wrap` task asserts the strict form and is the counterexample (reached by loading a free `hwm` of 2^64-1, then incrementing -- two steps). A saturating increment would make P8 unconditional. |
| `mailbox:nolatch` | The mailbox does not latch `frame_seq`, `key_slot` or `cmd` at the doorbell; it reads them live in VERIFY. If they change between doorbell and `sig_done`, a command dispatches with a sequence that is not above the last one (and `last_seq` can move backwards). The default `prove` task assumes the front end holds the frame while the mailbox is in VERIFY; `nolatch` drops that assumption and is the counterexample. Fix: latch the frame at the doorbell. |
| `mailbox:midhalt` | `running` is checked only at the doorbell. If the rung leaves RUN during VERIFY, a `needs_run` command still dispatches. `midhalt` is the counterexample (a P13 analogue). Fix: re-check `running` at dispatch. |

## Netlist equivalence

`equiv:<block>` synthesizes `rtl/gen/<block>.v` with Yosys (`synth`, `abc -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX`) and proves it equivalent to the generated Verilog with `equiv_make`, `equiv_simple` and `equiv_induct` (sequential, matched registers, induction).

This is an in-flow **Yosys** gate netlist, **not** the LibreLane netlist the brief names: `make gds`
needs Docker and the PDK and no netlist from it is checked in, so the real comparison cannot run here.
The Yosys check does prove the `abc`-mapped netlist equivalent to the generated Verilog, which is a
meaningful gate-level equivalence for these blocks. Comparing the real `governor_core` netlist would
need its standard-cell models; that job is not written.
