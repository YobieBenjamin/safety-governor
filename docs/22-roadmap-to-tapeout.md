# 22. The road to a chip we cannot fab: the whole program in five stages

> **Plain words first.** The goal has not moved. Prove or disprove the theory. If it survives, design the chip in software so that it fits NVIDIA's boards and talks only through NVIDIA's documented interfaces. Run the tests and the proofs on that chip. Finish the design to the point where a foundry could take it. Then stop, because nobody is going to hand me a mask set, and run the chip anyway, in simulation and on an FPGA, against the same catalogue of attacks the software passed. This document is that arc in one place, with what "done" means at each stage, what already exists, and the two walls I cannot talk my way through: the parts of NVIDIA's board specification that are under NDA, and the fab.
>
> **Backed by:** the experiment program (`20`) and its exit criteria, the run plan (`21`), the silicon plan (`08`) and its tape-out checklist, the verification plan (`07`), the proofs in `../proofs/`, the RTL in `../rtl/`, the LibreLane flow in `../hw/librelane/`, the board work in `../hw/pcb/`.

## Stage 1. Prove or disprove the theory, in software

This is the stage we are in. The claims were taken apart in `19`: L the logic, P the physical paths, C the cryptography, S the semantics the chip refuses to claim, N the numbers. Twenty-three experiments test them (`20`), agents run them in waves with a gate between (`21`), and every wave leaves a packet anyone can check (`../audit/wave-N/`).

Done means, in the words of `20`: every invariant in EXPERIMENT-CORE-INVARIANTS-BY-INDUCTION, EXPERIMENT-COMMIT-POINT-PROTOCOL-PROOF and WAVE-WIDEN-ABSTRACT-MACHINE proven and WAVE-TRACE-CONFORMANCE-REPLAY showing every simulation trace conforms to the proven machine; WAVE-DIFFERENTIAL-GATE-TEST showing two independent gates read one rulebook the same way on the whole catalogue and on random inputs; WAVE-MUTATION-TESTING-GATE leaving no check-removing mutant alive; WAVE-EXIT-REGISTER with no unaccounted physical path for at least one real tray, and now, for every lever, whether a module in the board's management slot can drive it and what else on the board can undo it; WAVE-OBSERVER-EVALUATION-SET, WAVE-OBSERVER-INDEPENDENCE and WAVE-OBSERVER-QUORUM-ARITHMETIC giving a witness quorum under the hazard budget for each modelled use case, or the design recording that for that use case the chip buys accountability rather than prevention; WAVE-DEPLOYMENT-OVERHEAD-SIMULATION under one percent and WAVE-FALSE-HALT-RATE-MODEL a rate an operator would accept; and a third, independent audit finding no claim without a source.

Disproved means any of: WAVE-DIFFERENTIAL-GATE-TEST showing the policy language itself is ambiguous; WAVE-EXIT-REGISTER finding a path that cannot be governed or bricked at the rack tier and that NVIDIA will not close; WAVE-OBSERVER-QUORUM-ARITHMETIC finding no affordable quorum for the use cases that justify the chip; WAVE-DEPLOYMENT-OVERHEAD-SIMULATION or EXPERIMENT-FPGA-BESIDE-REAL-GPU above what a buyer will pay. If one of those lands, that is the result, it gets published like any other, and the design goes back to the drawing board or into the drawer. The point of doing this in software is to find that out here, where it costs dollars, not there, where it costs a mask set.

Where it stands: the core invariants and the commit-point protocol are proven (`make proof`). Wave 1 built four experiments; three are in revision with specific findings, none has merged. Part 5 of the blog is the running account.

## Stage 2. Design the chip to fit NVIDIA's boards, in software

"Compliant to NVIDIA's board and chip specifications" has a precise meaning here, and an honest limit.

The chip is not on NVIDIA's die. It lives on the server maker's board, in the management-module slot or as a mezzanine, and reaches the GPU baseboard through the connector the board already has (`01`, `03`, `../hw/pcb/rack-integration.md`). So there are two specifications to fit, and they are not equally available:

- **The host-board side is public.** OCP's Datacenter Secure Control Module standard (DC-SCM 2.x) and its connector (DC-SCI), the LTPI sideband tunnel, the PCIe CEM signals (PERST#, PWRBRK#), SMBus and I2C. The governor module is designed to those documents, and nothing about that needs anyone's permission. That is Leg C in `08`.
- **The GPU-baseboard side is NVIDIA's, and the design guide for HGX is under NDA.** What the governor uses there is what the baseboard exposes at its connector and what NVIDIA documents in the open: the GPU's out-of-band management bus, the confidential-computing attestation report (the format and the verifier are public in nvtrust), Fabric Manager's partition interface, DOCA on the DPU. Everything beyond that is on the asks list in `03` §9, all of it firmware and software, and the design works with none of it granted. Experiment WAVE-EXIT-REGISTER carries the register of every physical path with a source per row; the rows only the design guide can settle are marked `NDA` and stay marked until someone with the guide fills them in. I will not claim compliance with a document I have not read.

Done means: the register map, mailbox, policy image, request and ticket formats frozen (`04`); every block on the die written in RTL with its invariants (`07` §3) and the generated Verilog matching the sources; the module's schematic-level interface to a DC-SCM 2.x host board and to the baseboard connector written down pin by pin (`../hw/pinout/`, `../hw/pcb/`); the loop circuit re-simulated against a real board's parasitics once the board exists on paper (`11`); and the WAVE-EXIT-REGISTER register with no `unaccounted` row that is not marked `NDA`.

Where it stands: the hard-core blocks exist in Amaranth with 20 simulation tests and generated Verilog (`../rtl/`); the pinout and the rack integration reference exist; the full peripheral set on an OpenTitan base is the work `08` §2.6 schedules first.

## Stage 3. Run the tests and the proofs on the chip

The same discipline as stage 1, one level down. Done means:

- **Formal on the Verilog (WAVE-FORMAL-PROOFS-ON-VERILOG).** The invariants proven on the abstract machine in `../proofs/` are proven again on the RTL blocks with a model checker, and equivalence checking shows the synthesized netlist is the same logic as the RTL. That closes the gap `19` §3 names: the proof is about the model until this is done.
- **The catalogue against the chip.** The same 75 attacks and 12 baselines, plus the governor's own 200 hypothesis tests, driven into the full-chip RTL simulation through the mailbox, with the same reason codes coming back. A reason code that differs between the model and the chip is a bug in one of them, and the trace says which.
- **Gate-level simulation.** The signed-off netlist with timing annotation, run through the same catalogue, so that what we simulated is what the layout is.
- **The circuit.** The halt loop measured, not only simulated, on a bench loop of real wire and real comparators (`11`, `../hw/loop/`).

## Stage 4. Finish the design to the point where a foundry could take it

This is the LibreLane flow on SkyWater sky130, Leg A in `08`, chosen because the process design kit and every tool in the flow are open, so there is no step a reader cannot repeat. Done is the tape-out checklist in `08` §5, every box ticked: synthesis clean with no latches and no loops; timing met at the three corners with margin; DRC clean in Magic and KLayout; LVS clean in Netgen; antenna, fill and density inside the deck's windows; IR drop under budget; the GDS matching the shuttle's template outside the user area; lifecycle fuses behaving; the firmware image measured and the DICE vectors matching the model.

The deliverable is a tape-out package that could go to a shuttle tomorrow: the GDS, LEF and DEF, the netlist, the timing and signoff reports, the RTL and the formal proofs, the testbench and the catalogue results at every level, the firmware image, the pinout, the board reference, the assumptions register, and a manifest with the hash of every file. Under version control, reproducible by `make gds` on a machine with Docker.

## Stage 5. Stop, and run it anyway

We will not get a chip back. A shuttle slot is money and a year, and that is the day someone with both reads this and decides to. What we can do is run the chip three ways, which is more than most designs get before silicon:

1. **The full-chip RTL** under the whole catalogue, the same reason codes as the software, as in stage 3.
2. **The gate-level netlist** from the signed-off layout, with timing, under the same catalogue.
3. **An FPGA** carrying the governor core, wired to a real board's management bus, a real PCIe switch and a real DPU where I can get them, measuring the three cost numbers the models only estimate (EXPERIMENT-FPGA-BESIDE-REAL-GPU in `20`): firmware share, engine utilisation, record latency, and the false-halt rate over weeks of a loop beacon. `18` calls this the measurement that settles the overhead question, and it is the last thing in the program that can disprove the chip without a fab.

If all of that holds, the claim at the end is not "the chip works". It is: the logic is proven, the circuit is simulated and bench-measured, the layout is clean for a real process, and the chip runs the same catalogue the software runs, with the same answers, in RTL, in gates and on an FPGA. What remains is a shuttle slot and the two walls: the NDA rows in WAVE-EXIT-REGISTER, and the fab. Both are someone else's decision, and the package will be sitting there, public, with its hashes, when they make it.

## The order of work from here

1. Finish wave 1 through the gate; start waves 2 and 3 (`21`). Stage 1.
2. WAVE-EXIT-REGISTER with the retrofit columns; the OpenTitan-based peripheral set in RTL; the module interface pin by pin. Stage 2.
3. WAVE-FORMAL-PROOFS-ON-VERILOG and the catalogue against the full-chip RTL. Stage 3.
4. The LibreLane signoff and the package. Stage 4.
5. The FPGA. Stage 5.

Each stage publishes what it finds, good or bad, in the same voice as the first five posts.
