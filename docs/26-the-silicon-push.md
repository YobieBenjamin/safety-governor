# 26. The silicon push: everything we tried on the way to a chip, the wins and the faceplants

> **Plain words first.** Up to now almost every proof in this program was about a Python model of the chip, not the chip. That is like crash-testing a drawing of a car. On 22 and 23 October 2026 I started crash-testing the car itself: the actual circuit description a foundry would build from. Six workstreams ran at once. This page records every one of them, what worked, what failed, what got stopped and why, in plain English. The failures stay on the page. A lab notebook with only the good days in it is a brochure.

Every section below has the same four parts: what it is (with an analogy), what we did, what happened, and what is still open. Each workstream also has its own plain-English file next to its code, linked from its section.

## Why this stage matters, in one analogy

Think of the chip as a building's fire system. The Python model is the architect's drawing of the sprinklers. The proofs so far said the drawing is right: every room is covered, no valve can be shut from the lobby. But fires burn buildings, not drawings. The Verilog is the actual pipe layout handed to the plumbers. If the plumbers' layout has a valve the drawing doesn't, the drawing's proof is worthless. So this stage checks the pipes, not the drawing.

## Workstream 0: the first proof on the chip itself (done)

**What it is.** A "formal proof" is not a test. A test is trying a hundred doors to see if any open. A proof is showing from the blueprint that no door in the building can open, ever, from any position, without a key. The tool (yosys plus the z3 solver) does that exhaustively. "k-induction" is the trick that makes it cover every reachable state and not just the first few seconds: show that if the building is safe at any moment, it's still safe one tick later, and it was safe at the start, so it's safe forever. Like dominoes: the first one falls, and each one knocks the next.

**What we did.** The halt sequencer is the block that pulls the GPU's power brake, holds reset, and cuts power. It's the hand on the emergency stop. I wrote its rules down as assertions and proved them on `rtl/gen/halt_seq.v`, the generated Verilog:

- the brake, reset and power pins always follow the safety rung, with no register anyone could flip;
- once halted, the chip never goes back to running without an authorized CLEAR;
- tamper always lands in SAFE;
- a halt command is obeyed from every rung except SAFE (which already outranks it);
- the rungs climb on their timers, THROTTLE to HALT to SAFE.

Then I tried to break the proof on purpose. Five planted bugs, one line each, the kind a tired engineer writes at 2 a.m. (a halt that leaves the loop closed, a brake that lets go in THROTTLE, a halt command ignored once throttled). Every one now fails the proof. One command: `python -m rtl.formal`. It runs in CI.

**What went wrong first, and stays on the record.**

1. My first property said "in HALT the loop switch is always open." The proof said no. It was right and I was wrong: by design, a *local* cause (a lost heartbeat, a budget trip) climbs the rungs on this chip alone and keeps the loop closed, so neighbours aren't dragged down. The spec (`07`) says exactly that. I fixed the property, not the chip.
2. My first run "caught" all five planted bugs. It caught them because of a file-path error inside the tool, not because the proof saw them. That's a smoke detector that beeps because its battery is dying, then gets credit for finding a fire. The runner now refuses to count a tool error as a catch. This is the same trap the 22 October reviewer warned about, and I walked into it within an hour.
3. With the fix, two of the five planted bugs got through: "HALT never escalates to SAFE" and "a halt command is ignored once throttled." My rules only said the chip never gets *less* safe. They never said it has to get *more* safe when it should. A lock that never opens is safe, and also useless as a door. I added the climbing rules and the obey-the-halt rule; now all five are caught.

**The open question the proof surfaced.** A chip that loses its heartbeat powers itself all the way down to SAFE and never opens the loop to tell its neighbours. That matches the spec. Whether it *should* is a design decision for me, and it stays open on this page until I make it.

Commit `eda385f`.

## Workstreams 1 and 2: proving the other twelve blocks

Two agents, six blocks each, every block proven four ways: a bounded check, k-induction, a long randomized simulation against a reference model written separately from the spec (two people doing the same sum on separate sheets of paper), and more than one solver. Then planted bugs, at least four per block.

### Group B (heartbeat, meter, alarms, measurement register, loop, the whole core): done

- All six blocks proven, plus the halt sequencer, in **three independent solvers** (z3, yices, boolector). Three different mathematicians checking the same proof, none of them us.
- 36 planted bugs, all 36 caught by assertion.
- **For the whole core,** the rule that the host can't write anything except the mailbox doorbell is proven on the full-size circuit. It's a wiring fact, like showing there is no pipe from the lobby to the sprinkler valves at all. The other core rules (the pins follow the sequencer, the chip boots safe, any halt reaches the pins, no running without CLEAR, the heartbeat can't be stretched, a lost loop is always seen, an open loop stays open until CLEAR) are proven on a small build of the same design, with the argument for why size doesn't matter written in the proof file. Like testing a bridge design on a scale model: it only counts if you can show the physics doesn't change with size, and the argument is on the page for anyone to attack.
- **Two real bugs, both fixed,** each with a regression test that fails on the old circuit:
  1. **The meter could wrap around.** One big enough add moved a counter down, so a job could overspend and then read as under budget. An odometer rolling over so an old car looks new. The counters now stick at their maximum. The conformance suite had found the same bug independently (its F-11), so that finding is now closed and its test stays as a guard.
  2. **The heartbeat timer could be frozen.** The millisecond tick came from the low bits of a counter that one input could hold still. Hold it still and the "no heartbeat, shut down" timer never runs out. Gluing the hands of a dead man's switch. The tick now has its own counter.
- **Design questions for me** (in `rtl/formal/FINDINGS-b.md`):
  - A signed HALT to a chip already in SAFE doesn't open the loop to warn its neighbours. That contradicts the fabric spec (`02`). Leaning toward making it open.
  - At boot, one chip that never gets its first heartbeat holds the whole rack's loop open, so one missing heartbeat stops every machine until it arrives. Safe, maybe more than I want.
  - Confirmed, now proven rather than observed: a lost heartbeat takes one chip down to SAFE with the loop closed.
- **Spec mismatches recorded, not changed:** the hardware doesn't clamp the heartbeat window to the policy's expiry (only the software model does); the hardware meter has no END_MODEL freeze.
- **What didn't work:** a full-size "two copies of the core behave the same" proof ran 26 minutes without finishing on this machine, so the agent switched to the wiring proof plus the small build. Some proofs only finish in one of the three solvers here. The random core simulation caught 5 of 7 core bugs on its own; the proofs caught all 7. That's an argument for proofs, not against simulation.
- Plain English, one analogy per block, every dead end: `rtl/formal/PLAIN-ENGLISH-b.md`. Full run log: `rtl/formal/last-run-main.txt` (on the merged code: every property proven, every planted bug caught, 324 tests pass).

### Group A (mailbox, permissions table, ticket store, epoch, clock counter, lifecycle): done

- All six proven on the Verilog; five of them re-proven by a second solver. The ticket store is the exception: the second solver ran 15 minutes without finishing, and the run prints NOT RUN for it rather than pretending. It has one solver plus a 20,000-cycle random simulation.
- 38 planted bugs, all 38 caught on a real trace from reset (a stricter rule than before: a bug only counts as caught if the short, concrete check fails, not just the induction).
- **Two real bugs, fixed,** each with a regression test that fails on the old circuit:
  1. **The debug door stood open after every restart.** A chip whose fuses said "production" granted debug access from reset until firmware loaded the fuses. A bank vault that powers up with the door open and locks once the manager checks the logbook. Now debug needs a fuse load since the last reset. This is the dangerous half of conformance finding F-06; the other half (the lifecycle register reads "test" in that window, so software reading it is told the wrong thing) is still open.
  2. **The clock counter could roll over to zero,** reachable in two cycles by loading an all-ones value from the fuses. Every expiry check would then misread time. It now stops at the top. Conformance F-12, closed.
- **Eight open findings** in `rtl/formal/FINDINGS-a.md`, each with a check that must keep failing until it's fixed. The pattern worth knowing: three of them (the clock, the used-ticket store, the mailbox sequence numbers) are the circuit forgetting on restart what the spec says firmware and non-volatile memory must remember. A bouncer who forgets every face when the lights flicker. The memory belongs to firmware that isn't written yet; the tests that will hold it to account already exist. Also open: an old rulebook edition can be committed again in hardware (the firmware is supposed to stop that), expired permissions come back when the 32-bit clock wraps every 71.6 minutes, and the mailbox doesn't hold a message still while its signature is checked.
- **What didn't work** (full list in `rtl/formal/PLAIN-ENGLISH-a.md`): yosys silently turned references to a block's internal signals into free inputs, which would have made any proof using them worthless, so the runner now refuses every yosys warning. The agent was also blocked from writing its two report files and handed the text back; I committed it.

### The two serious conformance bugs: both fixed

- **Tamper now beats CLEAR** (F-05). Fixed in the halt sequencer, and the "unless cleared that same cycle" excuse is out of my own proof.
- **No debug at power-up** (F-06, the dangerous half), fixed by group A.
- Also fixed on the way: the FPGA work found a real board could never stay running, because the chip halted itself one cycle after starting on a stale loop reading. Running now needs a clean loop sample.

**The combined run** (every block, every fix, on one branch): 346 tests pass; every property proven on the Verilog, 13 core blocks plus SMBus, most in three solvers; every planted bug caught; conformance PASS with 12 open disagreements. Full log: `rtl/formal/last-run-main.txt`.

## Workstream 3: 150 checks against the full-chip RTL (stopped once, then done another way)

**What it is.** The software already survives 75 attacks and lets 12 legitimate operations through. The idea was to throw the same attacks, plus 75 new ones, at the chip's circuit and check it refuses for the same reasons the software does. Like checking the real building's locks against the same burglary list you used on the drawing.

**What happened.** The agent read everything, confirmed the existing catalogue still holds (75 of 75 blocked, 12 of 12 allowed), and confirmed the full chip simulates in under a second, so every attack can get a clean start. Then, while writing new ways to get past the governor's protections, it was stopped twice by Anthropic's own safety system. It stopped there, and I chose not to rephrase the work to get around that check, even though the target is my own simulated chip. That is a real limit of doing this work with an AI, and it goes on the record like any other result. (There is a certain irony in an AI safety system stopping work on an AI safety chip. It's also evidence that safety checks bolted onto models are blunt instruments, which is the whole premise of this program.)

**What it found before it stopped.**

- Most of the 75 existing attacks are decided by the chip's *firmware*, not its hard-wired logic. On the chip, the honest label for most rows is "firmware decides, hardware enforces." Think of a bank: the teller (firmware) decides whether your withdrawal slip is valid; the vault door (hardware) only opens when the teller presses the button. Testing the vault door can't tell you whether the teller is fooled.
- **Check order.** Settled below by the conformance run; the first guess was only half right.
- **Reset and replay (a modelling gap, not a chip bug).** The chip's circuit forgets used tickets and sequence numbers on reset. The spec (`04`) gives that memory to firmware and authenticated non-volatile storage, which the RTL doesn't model. So: spec assigns it to firmware; not modelled yet.

**Then: conformance testing (done).** With my go-ahead, a second agent did it the way chip teams do: the building inspector with the code book, walking room by room, rule by rule. No attack recipes. The safety system did not stop it.

- 125 rules quoted word for word from the spec (`04`, `07`). The run fails if a quote stops matching the spec, so the rulebook and the tests can't drift apart silently.
- 163 conformance tests on the chip's circuit, plus the 87 existing catalogue rows mapped to the rules they exercise: 250 checks against a target of 150. Honest footnote: the 87 catalogue rows run on the reference software stack, not the chip, so they count toward coverage but say nothing about the circuit. The 163 are the chip.
- 4,000 random mailbox messages and 14 written from the spec, fed to the chip circuit and the software model side by side, like two witnesses interviewed in separate rooms. The 14 spec messages all agree. Of the random ones, 3,690 agree and 310 fall into recorded disagreements; none unexplained.
- 27 deliberate bugs planted in the circuit; the tests caught all 27.
- One command: `python -m rtl.conformance`. Result: PASS, meaning the suite does what it claims, with 15 disagreements between the chip and its spec on the record in `rtl/conformance/FINDINGS.md`. Plain English: `rtl/conformance/PLAIN-ENGLISH.md`.

**The two that matter most (high severity, not fixed yet):**

- **F-05: CLEAR beats tamper.** If an authorized CLEAR and a one-cycle tamper pulse (a glitch detector firing) land in the same instant, the CLEAR wins, the tamper is forgotten, and the chip can re-arm and go back to running. The spec says tamper means SAFE, full stop. Analogy: the fire marshal signs the all-clear at the exact second the smoke detector chirps, and the chirp gets thrown away. And here is the embarrassing part: my own halt-sequencer proof in workstream 0 has the line "tamper always lands in SAFE *unless cleared that same cycle*". I wrote the bug's excuse into the proof. A proof only proves what you ask it, and I asked the wrong question. The fix goes in the circuit and that exception comes out of the proof.
- **F-06: the debug door is open at power-up.** The lifecycle register starts in TEST mode until firmware loads the fuse value, so for that window a production chip would grant debug access. The spec says debug is impossible in production. Analogy: a bank vault that boots up with the door open and only locks once the manager walks in and checks the logbook. The fix: the register must come out of reset in the most locked state and only ever unlock from fuses.

**Medium:** a signed HALT to a chip already in SAFE doesn't open the loop (and the software model gets the same case wrong a different way); the capability table can hold two entries for one port, so tightening a budget does nothing; the traffic meter wraps at 48 bits, about 281 terabytes. **Low:** the "millisecond" tick is really 1.024 ms, so every timer runs 2.4 percent long; a zero-byte lookup passes at zero budget; the 64-bit clock can wrap if the fuses read all ones; the mailbox doesn't hold the message steady while the signature is checked; and five smaller mismatches between the model and the spec text.

**The check-order question, settled.** The software model actually uses the chip's order for sequence and epoch. The real difference is where "is the chip running?" is checked: first in the software, third in the chip, and the spec never says. Also confirmed: the chip tells an unsigned message why it was refused before checking the signature. Both are spec decisions to make on purpose.

**What it can't cover:** physical claims (the real halt loop, levers on a real GPU, power loss) and firmware that doesn't exist yet.

**Next:** fix F-05 and F-06 in the circuit, use their reproducers as the regression tests, and take the "unless cleared" excuse out of the halt proof.

## Workstream 4: layout and signoff on SkyWater 130 nm (partial, stopped mid-routing)

**What it is.** Turning the circuit into the actual drawing of transistors and wires a foundry prints, then the checks a foundry demands before it will take your money. If the Verilog is the architect's plan, this is the construction drawing with every pipe, wire and bolt placed, and signoff is the building inspector who will not let you pour concrete until every code is met.

**What happened.**

- **Getting the tools was half the job.** Docker couldn't reach any container registry from this machine, Nix couldn't reach a binary cache, and the current LibreLane needs newer tools than any prebuilt version reachable here. The agent found a path that works: OpenLane 2.0.0 (LibreLane's earlier name) with tools from the conda litex-hub channel and the sky130 process kit downloaded straight from GitHub, after fixing four ways the tools refused to start. All of it is repeatable with one command, `hw/librelane/setup_toolchain.sh`, and every dead end is in `hw/librelane/TOOLCHAIN.md`.
- **The run got through floorplan, placement and the clock tree,** on the Verilog as it stood before the 23 October fixes, and was killed by a container restart in the middle of detailed routing. It was not restarted.
- **The good news:** the design maps cleanly onto a real foundry library: 117,929 cells, zero latches, 0.52 square millimetres of logic on a 1.8 mm by 1.8 mm die, 16 percent full. At the typical corner (25 C, 1.80 V) it meets timing at 50 MHz with 4.1 ns to spare.
- **The bad news, on the page:** timing fails at the slow corner (100 C, 1.60 V, -65.7 ns) and, oddly, at the fast one (-40 C, 1.95 V, -42.9 ns). A fast corner failing when the typical one passes is not how physics usually behaves, so that number points at a constraint or path problem to chase, not at a slow chip. And there were 1,037 antenna violations before routing. Antennas are long wires that collect charge during manufacturing and can blow the gate at the end of them, like a lightning rod wired to a light switch; the fix is protection diodes, which is real work.
- **Not reached:** design rule check, layout versus schematic, fill, power-drop analysis, the final GDS. So no box on the tape-out checklist that needs a finished layout is ticked.

**What finishes it.** Your Mac with Docker: the current LibreLane runs the same config unchanged, in about an hour instead of a day. First point it at the current Verilog, then fix the corner timing and the antennas. Plain English, step by step with an analogy each: `hw/librelane/PLAIN-ENGLISH.md`. Metrics at the last finished step: `hw/librelane/full4-metrics-at-step40.json`.

## Workstream 5: FPGA and the management bus (done, in software; nothing on real hardware yet)

**What it is.** An FPGA is a reprogrammable chip: the dress rehearsal before opening night, where opening night costs a mask set. SMBus is the server's management intercom, the wire the governor listens and answers on.

**What happened.**

- **The intercom, proven.** A new SMBus block (`rtl/governor_rtl/smbus.py`) answers reads of the chip's status registers and accepts exactly one kind of write: the mailbox doorbell, with a correct checksum, committed on STOP. A proof on the Verilog shows that for any waveform anyone can put on those two wires, nothing else in the chip changes. A guest can ring the front desk; the intercom has no button that unlocks the vault. 11 planted bugs, all caught.
- **The bitstream builds.** On a ULX3S board (Lattice ECP5 85F, open tools only): 21 percent of the logic, 15 percent of the flip-flops. One command: `hw/fpga/build.sh` (26 minutes here).
- **It does not reach 50 MHz.** Best is 37.9 MHz, so the bench build runs at 30 MHz. The slow path is the permissions-table lookup, which checks every entry in one cycle. That says nothing about the real chip on sky130, but it's a number, and it goes on the page.
- **The bench is one command.** `hw/fpga/BENCH.md` has the parts list (the board is US$275 from Crowd Supply, read on the day; the other prices weren't reachable), the wiring, and a Raspberry Pi script, `hw/fpga/host_test.py all --hours N`, that checks the registers and runs the overnight false-halt soak.
- **It found a real bug** (F1): with the loop sensor running from power-on, the chip halted itself one cycle after reaching RUN, so a real bench could never stay running. Fixed (above).

**What it can't do yet.** There is no processor or crypto engine on the FPGA, so the firmware-cost numbers aren't measured; the bench measures the hardware halt path and the false-halt rate. The PCIe adapter to a real GPU isn't designed. Nothing has run on a real board. Plain English, with the full "what didn't work" list: `hw/fpga/PLAIN-ENGLISH.md`.

## Workstream 6: the public NVIDIA-side interfaces (done)

**What it is.** A chip that's going to live in an NVIDIA server has to speak that server's languages and fit its sockets, the way an appliance has to fit the outlet and run on the local voltage. The public languages: the DC-SCM management module standard (the socket), the PCIe reset and power-brake wires (the off switch and the dimmer), SMBus (the building intercom), SPDM (a bouncer who checks your ID and then asks a question only the real you could answer) and NVIDIA's open nvtrust tools (NVIDIA's own ID checker for its GPUs). Anything only in NVIDIA's NDA design guide stays marked NDA. I don't claim compliance with a document I haven't read.

**What happened.** One command, `python -m govsim.hardware_ref`, runs seven checks and printed PASS when I re-ran it after the agent.

- **The socket.** All 85 governor pins mapped to the DC-SCM connector, with a public source per row (`hw/pinout/dcscm_mapping.csv`). A checker validates it, and it caught all 18 mistakes planted in it. Four pins have no public home and are marked open, not guessed.
- **The off switch: a real finding.** The existing halt circuit breaks three of the PCIe standard's timing rules for power-up and reset. Like a car that releases the parking brake before the engine has started. A new block (`rtl/governor_rtl/cem_sideband.py`) meets all three, and its checks caught five broken versions of it. The brake gets to the pin in 336 microseconds, inside the 1 ms bound. Honest limit: there is no public number for how fast a GPU actually slows down once the brake is pulled, so the bound is proven at the pin, not inside the GPU.
- **The bouncer: the first test against somebody else's code.** Until now the chip was only ever checked against its own models, which is grading your own homework. This time the governor's SPDM attestation was run against DMTF's reference implementation, libspdm, in both directions, at versions 1.1 and 1.2. DMTF's own conformance tester found a real bug on the first run (five failures; the log is kept). After the fix: 781 checks, zero failures. Corrupted signatures were refused by libspdm, so the pass means something.
- **NVIDIA's ID checker.** On NVIDIA's public Hopper sample report, our adapter reaches the same answers as NVIDIA's own verifier, including on a tampered copy.
- **The compliance matrix** (`docs/interfaces/COMPLIANCE-MATRIX.md`): 60 requirements, each with its source. 27 tested, 9 designed, 19 open, 1 members-only, 4 NDA. This is the document to hand an NVIDIA partner engineer.

**What it found that I don't like.**

- If the governor dies, the management link (LTPI) holds every signal in its last state, so a dead governor leaves its GPUs running. A guard who faints holding the door open. The agent wrote requirement REQ-LTPI-FS-1: the motherboard must pull the brakes itself when the link drops. That's a rule for server makers; our chip can't enforce it alone.
- The docs say PCIe reset is released after slot power is good; the circuit releases it on the same clock edge it turns the power on.
- The pinout is missing three kinds of pins this design needs (a reset input for the governor's own PCIe link, a power-good input per slot, the second LTPI link). Proposed, not added yet.

**What didn't work.** NVIDIA's revocation check needs a network connection this machine doesn't have, and the signing certificate on NVIDIA's test reference files had expired, so NVIDIA's own code rejects them offline. SPDM's transport layer and encrypted sessions aren't modelled. The new off-switch block isn't wired into the chip yet, on purpose, so it doesn't pull the rug out from under the proofs still running. Plain-English write-up with a "what didn't work" table: `docs/interfaces/PLAIN-ENGLISH.md`.

## Two design calls (23 October 2026, decided by Yobie)

The proofs handed me two questions. I answered both the same way: silently failing is a bullshit feature. A chip that is stopping things, or stopping itself, has to say so, out loud, by name, and an operator has to be able to read it off one chip over the management bus.

**Call 1: a HALT rings every bell, even on a floor that's already shut.** Before, a chip that lost its heartbeat climbed to SAFE on its own and cut its GPU's power, with its loop still closed so the neighbours kept running. Fine. But if the authority then sent that chip a signed HALT, meaning "stop the whole domain", the chip ignored it, because it was already in SAFE. That's a fire alarm pull station that does nothing if the sprinklers on that floor already went off. Pulling the alarm has to ring on every floor.

- What changed: a HALT now opens the loop switch on every rung, SAFE included. The chip stays in SAFE (power off; SAFE outranks HALT), and CAUSE now says "command", so the log says who stopped it. Tamper keeps its own cause. The priority order is unchanged: tamper, then an authorized CLEAR, then everything else.
- The software model had the same case wrong a different way: it dropped from SAFE to HALT and turned slot power back on. It now never moves down a rung.
- Evidence: proven by k-induction on the generated Verilog in three solvers (`rtl/formal/halt_seq.sv`, the H rules; `governor_core.sv`, rule G3 at the pins). The old behaviour is planted back as a bug, twice (the chip's version and the model's version), and both are caught by assertion. The old "design fact" that said HALT in SAFE does nothing is deleted. Conformance finding F-07 is closed; its reproducers now pass and stay as guards, and they fail by assertion on the old circuit.

**Call 2: one dead smoke detector can hold the building, but it has to say which one, and bypassing it needs the building manager's signature.** At boot, a chip that never gets its first heartbeat keeps its loop switch open, so nobody in the rack can start. That stays: fail closed. What was wrong is that it failed silently. The operator saw "the rack won't start" and had to go hunting.

- Loud and named: after a boot window (5 seconds on the chip) the hardware itself raises a sticky alarm, NO_FIRST_HEARTBEAT (ALARMS bit 31), shows it live in CAUSE bit 3, and BOOT_WAIT says how long it has waited. Firmware can't fake it or raise it; only the sequencer can, and only an authorized clear removes it. It can never fire on a chip that has had its heartbeat. The model logs it with the chip id and boot time and sends it on the fabric so the neighbours log it too.
- The way out: a new signed command, EXCLUDE, under the same rules as CLEAR (the authority's key, never the heartbeat key, bound to this chip, expiring in under a minute, typed so nothing else can pose as it). The excluded chip closes its own loop switch so the rest of the rack can run, and keeps its own brake, reset and power-off on, so its GPUs never run. It only works on a chip waiting for its first heartbeat; it does nothing at all to a chip halted by a loop break, a command or tamper. A real heartbeat ends it the normal way; so does a reset, or a HALT or tamper (with the loop open). Excluded is its own alarm bit (30) and CAUSE bit 4, and the log names who signed it. Like a building manager signing to bypass one faulty detector: allowed, logged, and the room stays locked.
- Evidence: proven on the Verilog: an excluded chip's levers stay on until a valid heartbeat; EXCLUDE can't close the loop of a chip halted by loop loss, command or tamper; a two-copy proof shows EXCLUDE changes not one register outside "waiting for the first heartbeat"; the alarm rises when the window passes and never once armed; at the pins and in the ALARMS and CAUSE registers (rules G7 to G9). Thirteen new planted bugs, all caught by assertion. Random simulation against a separately written model of the sequencer and the core, the conformance suite (nine new requirement rows quoting the new spec sentences, 30 of 30 planted bugs caught), and model tests in `tests/test_yobie_calls.py`.

Spec: `04` sections 2, 3 and 9, `02` section 1, `07` the halt row. Code: `rtl/governor_rtl/halt.py`, `top.py`, `alarms.py`, `govsim/governor.py`, `govsim/reasons.py`.

## The scoreboard

| Workstream | Status | Where |
|---|---|---|
| 0. Halt sequencer proven on the Verilog | Done; 5 of 5 planted bugs caught after two rounds of fixing my own properties | `rtl/formal/`, `eda385f` |
| 1. Six blocks proven (mailbox and friends) | Done: 38 of 38 planted bugs caught, 2 real bugs fixed (debug at power-up, counter wrap), 8 open findings | `rtl/formal/` |
| 2. Six blocks proven (heartbeat to the full core) | Done: 3 solvers, 36 of 36 planted bugs caught, 2 real bugs fixed (meter wrap, frozen heartbeat clock), 2 design questions for me | `rtl/formal/` |
| 3. 150 checks on the full-chip RTL | Attack-recipe version stopped by a safety check; conformance version done: 250 checks, 27 of 27 planted bugs caught, 15 disagreements found; both high ones fixed, 12 open | `rtl/conformance/` |
| 4. sky130 layout and signoff | Partial: toolchain found, synthesis to clock tree done (0 latches, typical corner met at 50 MHz); slow and fast corners fail, 1,037 antenna violations; routing interrupted, no DRC/LVS/GDS | `hw/librelane/` |
| 5. FPGA and SMBus | Done in software: SMBus proven (11 of 11 bugs caught), ULX3S bitstream at 30 MHz (50 MHz not met), bench plan; nothing on real hardware yet | `hw/fpga/` |
| 6. Public interfaces | Done: 85 pins mapped, SPDM passes DMTF's tester (781 checks), nvtrust matches NVIDIA's verifier, 60-row compliance matrix; PCIe timing bug found and a fixed block written, not wired in yet | `docs/interfaces/`, `hw/pinout/` |

This page gets updated as each one finishes, with the bad news in the same font as the good.
