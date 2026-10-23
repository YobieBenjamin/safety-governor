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

## Workstream 3: 150 attacks against the full-chip RTL (stopped, partly)

**What it is.** The software already survives 75 attacks and lets 12 legitimate operations through. The idea was to throw the same attacks, plus 75 new ones, at the chip's circuit and check it refuses for the same reasons the software does. Like checking the real building's locks against the same burglary list you used on the drawing.

**What happened.** The agent read everything, confirmed the existing catalogue still holds (75 of 75 blocked, 12 of 12 allowed), and confirmed the full chip simulates in under a second, so every attack can get a clean start. Then, while writing new ways to get past the governor's protections, it was stopped twice by Anthropic's own safety system. It stopped there, and I chose not to rephrase the work to get around that check, even though the target is my own simulated chip. That is a real limit of doing this work with an AI, and it goes on the record like any other result. (There is a certain irony in an AI safety system stopping work on an AI safety chip. It's also evidence that safety checks bolted onto models are blunt instruments, which is the whole premise of this program.)

**What it found before it stopped.**

- Most of the 75 existing attacks are decided by the chip's *firmware*, not its hard-wired logic. On the chip, the honest label for most rows is "firmware decides, hardware enforces." Think of a bank: the teller (firmware) decides whether your withdrawal slip is valid; the vault door (hardware) only opens when the teller presses the button. Testing the vault door can't tell you whether the teller is fooled.
- **Check order (real, not a hole).** For a bad message, the chip checks sequence number, then epoch, then whether it's running, then the signature. The software checks in a different order, so the same bad message can get a different refusal reason. Nothing gets through either way, but two witnesses telling the same story differently is a problem in court. Also on the record: the chip answers the first three checks before it has verified the signature, so an unsigned message still learns why it was refused. Common in real designs; it should be a choice, not an accident.
- **Reset and replay (a modelling gap, not a chip bug).** The chip's circuit forgets used tickets and sequence numbers on reset. The spec (`04`) gives that memory to firmware and authenticated non-volatile storage, which the RTL doesn't model. So: spec assigns it to firmware; not modelled yet.
- **Clear and tamper in the same instant; the startup window before the fuses load.** Both unconfirmed. Workstreams 1 and 2 cover the blocks involved, so their proofs will settle them.

**What's next.** Instead of writing new attack recipes, turn every "must refuse" rule in the spec into a conformance test: the chip must refuse it, with the same reason the software model gives. Same ground, the way chip verification teams normally work. Waiting on my go-ahead.

## Workstream 4: layout and signoff on SkyWater 130 nm (running)

Turning the circuit into the actual drawing of transistors and wires a foundry prints, then the checks a foundry demands before it'll take your money. Plain-English walk-through with an analogy per step: `hw/librelane/PLAIN-ENGLISH.md`. Toolchain attempts, failures included: `hw/librelane/TOOLCHAIN.md`.

## Workstream 5: FPGA and the management bus (running)

An FPGA is a reprogrammable chip: the dress rehearsal before the opening night that costs a mask set. SMBus is the server's management intercom, the wire the governor listens and answers on. Plain-English notes: `hw/fpga/PLAIN-ENGLISH.md`. The real bench needs my hands and a parts order; the plan lists exactly what.

## Workstream 6: the public NVIDIA-side interfaces (running)

The plugs and protocols the chip must speak to live in an NVIDIA server: the DC-SCM management module standard, the PCIe reset and power-brake wires, SMBus, SPDM attestation, NVIDIA's open nvtrust tools. Anything only in NVIDIA's NDA design guide stays marked NDA. Plain-English notes: `docs/interfaces/PLAIN-ENGLISH.md`; the compliance matrix: `docs/interfaces/COMPLIANCE-MATRIX.md`.

## The scoreboard

| Workstream | Status | Where |
|---|---|---|
| 0. Halt sequencer proven on the Verilog | Done; 5 of 5 planted bugs caught after two rounds of fixing my own properties | `rtl/formal/`, `eda385f` |
| 1. Six blocks proven (mailbox and friends) | Running | `rtl/formal/` |
| 2. Six blocks proven (heartbeat to the full core) | Running | `rtl/formal/` |
| 3. 150 attacks on the full-chip RTL | Stopped by a safety check after inventory; four leads recorded; conformance testing proposed | this page |
| 4. sky130 layout and signoff | Running | `hw/librelane/` |
| 5. FPGA and SMBus | Running | `hw/fpga/` |
| 6. Public interfaces | Running | `docs/interfaces/` |

This page gets updated as each one finishes, with the bad news in the same font as the good.
