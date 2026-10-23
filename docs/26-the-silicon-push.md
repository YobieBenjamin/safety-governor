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

## Workstreams 1 and 2: proving the other twelve blocks (running)

Two agents, six blocks each. Each block is proven four ways (bounded check, induction, a randomized simulation against a separately written reference model, a second solver if one installs) and then attacked with at least four planted bugs. Plain-English notes with an analogy per block: `rtl/formal/PLAIN-ENGLISH-a.md` and `PLAIN-ENGLISH-b.md`. Results land here when they finish.

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

## Workstream 4: layout and signoff on SkyWater 130 nm (running)

Turning the circuit into the actual drawing of transistors and wires a foundry prints, then the checks a foundry demands before it'll take your money. Plain-English walk-through with an analogy per step: `hw/librelane/PLAIN-ENGLISH.md`. Toolchain attempts, failures included: `hw/librelane/TOOLCHAIN.md`.

## Workstream 5: FPGA and the management bus (running)

An FPGA is a reprogrammable chip: the dress rehearsal before the opening night that costs a mask set. SMBus is the server's management intercom, the wire the governor listens and answers on. Plain-English notes: `hw/fpga/PLAIN-ENGLISH.md`. The real bench needs my hands and a parts order; the plan lists exactly what.

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

## The scoreboard

| Workstream | Status | Where |
|---|---|---|
| 0. Halt sequencer proven on the Verilog | Done; 5 of 5 planted bugs caught after two rounds of fixing my own properties | `rtl/formal/`, `eda385f` |
| 1. Six blocks proven (mailbox and friends) | Running | `rtl/formal/` |
| 2. Six blocks proven (heartbeat to the full core) | Running | `rtl/formal/` |
| 3. 150 checks on the full-chip RTL | Attack-recipe version stopped by a safety check; conformance version done: 250 checks, 27 of 27 planted bugs caught, 15 disagreements (2 high) recorded | `rtl/conformance/` |
| 4. sky130 layout and signoff | Running | `hw/librelane/` |
| 5. FPGA and SMBus | Running | `hw/fpga/` |
| 6. Public interfaces | Done: 85 pins mapped, SPDM passes DMTF's tester (781 checks), nvtrust matches NVIDIA's verifier, 60-row compliance matrix; PCIe timing bug found and a fixed block written, not wired in yet | `docs/interfaces/`, `hw/pinout/` |

This page gets updated as each one finishes, with the bad news in the same font as the good.
