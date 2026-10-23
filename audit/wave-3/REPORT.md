# Wave report

Generated 2026-10-22 20:48 from `/Volumes/External_4TB/Safety Experiments/safety-governor/.agents/wave-3`.

| issue | backend | outcome | acceptance | pull request | turns | est. cost | wall time | attempts |
|---|---|---|---|---|---|---|---|---|
| L7 | cloud | done: 1 commit(s), 40 turns | fail (exit 2) | https://github.com/YobieBenjamin/safety-governor/pull/24 | 40 | $1.24 | 7 min | 1 |
| N2 | cloud | done: 1 commit(s), 20 turns | pass | https://github.com/YobieBenjamin/safety-governor/pull/23 | 20 | $0.52 | 2 min | 1 |

Estimated API-equivalent spend for the wave: $1.76 (Claude Code's client-side estimate; a subscription is billed by its windows, not by this figure).

## L7: the agent's last words

`make formal` has not passed. It failed on its one run here because `sby` is missing, so no property, proof or equivalence check has been executed. This environment has z3 only. It has no `sby`, `yosys` or `yosys-smtbmc`, and the Yosys bundled with Amaranth has no Verilog frontend. The brief said the tools were installed, so I assumed the container would have them. I left the work committed.

**Built**
- `rtl/formal/` has property files for `ticket_store`, `epoch_reg`, `halt_seq`, `cap_table`, `monotonic_counter` and `mailbox`.
- The properties are injected before the final `endmodule` of the generated Verilog, so `rtl/gen` is untouched.
- Each assertion label carries its P-number.
- `rtl/formal/README.md` has the full property map.
- Each block runs under SymbiYosys, bounded check then k-induction (`mode prove`, `smtbmc z3`).
- A `make formal` target and per-block `make formal-<block>` targets are added; `rtl/formal/run_formal.py` drives them.
- A netlist-equivalence job synthesizes each block to a gate netlist with Yosys and compares it to `rtl/gen`.

**RTL gaps found by reading the code.** These are unconfirmed until the solver runs. Three tasks are set to expect a counterexample, so they pass when one is found.
- **Counter wrap:** `monotonic_counter` wraps from 2^64-1 to 0, so P8 holds only modulo that wrap.
- **Mailbox frame not latched:** `mailbox` reads `frame_seq`, `key_slot` and `cmd` live during VERIFY. If they change after the doorbell, a stale sequence can dispatch.
- **`running` not re-checked:** a command that needs RUN can dispatch after the rung has left RUN during VERIFY.

**Not verified**
- The first run in the container may need fixes to property syntax or induction strengthening.
- The equivalence compares against a Yosys-synthesized netlist, not the LibreLane one. `make gds` needs Docker, and no netlist is checked in. The `governor_core` netlist job is not written.
- The commit-point properties appear only as the halt hold and the clearance bound to its command, since the RTL has nothing more.

**Open questions**
- Should the three RTL gaps be fixed (saturating counter, latch at the doorbell, re-check `running` at dispatch) once confirmed?
- Where does the real LibreLane netlist come from for the final equivalence?

The failing output is recorded in `EXPERIMENTS.md`.

## N2: the agent's last words

N2 is built and committed (`ddfe3a6`). Expected false halts come to 0.830 per rack-year against a switch-off threshold of 1.24, but the failure rates behind that are my own planning values, not looked-up table entries.

- **Acceptance:** `python3 -m pytest -q tests/test_false_halt_model.py` passes, 19 tests. It took two runs: the first failed on a hand-arithmetic slip in my test (0.001347 where the formula gives 0.001338). I did not run the full suite.
- **What was built:**
  - `govsim/false_halt.py` is the rate model.
  - `docs/07` §5.1 is the numeric FMEA table.
  - The `EXPERIMENTS.md` row for N2 is marked done.
  - The tests reproduce the arithmetic by hand and check the debounce formulas against a simulated comparator.
- **Fault injection:** Eight modes are injected into `govsim` to confirm each one's effect and scope (rack-wide or one slot). They are power loss, wire cut, comparator stuck open, fabric port down, authority outage, readback stuck open, a missed heartbeat and a silent member.
- **Result:** 0.679 rack-wide and 0.151 single-slot false halts per rack-year, for a 72-governor loop.
- **Debounce:** With the two-sample debounce, sense transients contribute 0.084 per rack-year. With a single sample they would contribute 12.5, more than the whole interruption baseline.
- **Disproof threshold:** 1.24 false halts per rack-year, which is one tenth of 12.4 per 72-GPU rack-year. The 12.4 comes from Meta's Llama 3 report of 419 interruptions in 54 days on 16384 GPUs, quoted from memory. The "one tenth" is my judgement, not an operator measurement. The model sits at 67% of that threshold.
- **What would push it over:** transients at about 6e-4 per hour or more, or firmware watchdog trips above about 1100 FIT.
- **Sources are not verified:** I did not search the web and did not read the IEC 61508, IEC 62380, SN 29500 or MIL-HDBK-217F tables. The FIT rates are planning values at those sources' order of magnitude, and §5.1 says so. Rows with no public rate are marked "assumed".
- **Debounce not in the simulator:** `govsim` senses the loop with one sample, so the two-sample debounce lives only in the model and the doc. I left the simulator alone to avoid breaking existing tests.
- **Beacon window:** As built, the beacon decides on one beacon's reports, judged when the next heartbeat closes the window. That is two heartbeats of latency, not a two-beacon confirmation. The model supports `confirm=2` and §5.1 says so.
- **Open questions:**
  - Can someone check the rates against the real tables?
  - Is a tenth of the baseline the right line for operators?
  - N3 should measure the glitch rate and duration, which are the least-known inputs.
- No patches to other repositories were needed.

