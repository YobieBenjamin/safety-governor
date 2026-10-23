# Formal proofs on the generated Verilog (L7)

`make formal` runs `run_formal.py`: for each hard-core block it injects `<block>.svh` in front of the final `endmodule` of `rtl/gen/<block>.v` (the checked-in Verilog is never edited), then runs SymbiYosys (`mode prove`, engine `smtbmc z3`): a bounded check, then k-induction, which is an unbounded proof when the induction closes. `make formal-<block>` runs one block; `make formal-equiv` runs only the netlist equivalence.

Reset is assumed low (`assume(!rst)`): the properties are about operation, and a power loss is the high-water mark's job (`m_P8_hwm_floor`).

## Property map

P-numbers are those of `proofs/core_invariants.py` (the model-level theorems). "CP" is the commit-point protocol (`proofs/commit_point.py`), of which the RTL holds only the hold (the rung does not leave HALT/SAFE without `clear`) and the binding of a clearance to its command (the mailbox).

| Block | Assertion prefix | P / CP | What it says |
|---|---|---|---|
| `ticket_store` | `t_P3_*` | P3 | a burned id stays stored and unchanged; no duplicate ids; a burned id is always `seen` and never burns twice (the id is a solver-chosen constant, so it holds for every id); a full store refuses |
| `epoch_reg` | `e_P9_*`, `e_P10_*` | P9, P10 | the register changes only on `commit` with `quorum_ok`, then loads `new_epoch`; the host port has no effect |
| `monotonic_counter` | `m_P8_*` | P8 | the value never decreases (except the 2^64 wrap, below); `load_hwm` raises it to at least the fuse mark; `dec_req` changes nothing |
| `halt_seq` | `h_P5_*` | P5 | the rung never descends without `clear`; HALT and SAFE absorb |
| | `h_P6_*` | P6 | RUN is entered only when armed (no cause, `hb_ok`, `loop_sense`); the loop switch closes only when armed, opens on tamper, loop loss and command halt, and `clear` does not close it |
| | `h_P7_*`, `h_P13_*` | P7, P13 | brake, reset, power and ports follow the rung exactly; every rung but RUN applies the brake and closes the ports |
| `cap_table` | `c_P1_*` | P1, P4 | `allow` only against an entry that matches (point, peer, dir), is unexpired, has the current epoch tag and enough budget; an entry appears only by an insert with `mac_ok`; the budget never rises on lookup (no underflow) |
| `mailbox` | `b_P12_*`, `b_P3_*` | P10, P12, P3, CP | dispatch only on a verified signature over the same command; sequence above the slot's last; the checks run in order and the first failure is the status; a wrong-command or bad-signature frame consumes nothing; the last-seq registers only rise |

## Tasks that are expected to fail (findings about the RTL)

Each is a `bmc` task with `expect fail`: the run passes when the counterexample is found. They are not proofs; they say which assumption the proofs lean on.

| Task | Finding |
|---|---|
| `monotonic_counter:wrap` | `inc` at 2^64-1 wraps to 0. Unreachable in practice (2^64 microseconds), but the block does not saturate, so P8 is proven modulo that one step. A saturating increment would make P8 unconditional. |
| `mailbox:nolatch` | The mailbox does not latch `frame_seq`, `key_slot` or `cmd` at the doorbell; it reads them live in VERIFY. If they change between doorbell and `sig_done`, a command dispatches with a sequence that is not above the last one (and `last_seq` can move backwards). The `prove` task assumes the front end holds the frame while the mailbox is in VERIFY. Fix: latch the frame at the doorbell. |
| `mailbox:midhalt` | `running` is checked only at the doorbell. If the rung leaves RUN during VERIFY, a `needs_run` command still dispatches. Fix: re-check `running` at dispatch. |

## Netlist equivalence

`equiv:<block>` synthesizes `rtl/gen/<block>.v` with Yosys (`synth`, `abc -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX`) and proves it equivalent to the generated Verilog with `equiv_make`, `equiv_simple` and `equiv_induct` (sequential, matched registers, induction). This is the same synthesis front end that LibreLane uses, but it is not the LibreLane netlist: `make gds` needs Docker and the PDK, and no netlist from it is checked in. Comparing the real `governor_core` netlist needs its standard-cell models; that job is not written.
