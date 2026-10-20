# 19. How solid is the theory? What is a theorem, what is engineering, what is trust

This document answers one question in plain English: at the level of theory, how solid is the story of the Safety Governor, can it be proven mathematically, and can it be proven in circuitry? It is written to be read on its own, by a person or by another model, without the rest of the repository. Where the repository has something that runs, it is named; nothing here depends on it.

The short answer first. The story has five kinds of claim in it, and they are solid in five different ways. The logical core is a theorem, and an old one, and this document comes with a machine-checked proof of it on an abstract model. The physical claim, that every path from computation to effect runs through the chip, is an engineering claim: it can be made true by construction and checked by enumeration, but it cannot be proven from an armchair. The cryptographic claims rest on the same assumptions as everything else on the internet. The semantic claim, that the chip knows what is bad, is not made at all; the design says so, and that refusal is what makes the rest provable. The numbers, overhead and false halts, are measurements that have not been taken yet.

## 1. Take the story apart into claims

When somebody says "the chip makes the AI safe", five different things are being claimed at once. Pull them apart, because they are proven, or not, in different ways.

**Claim L (logic).** If every action must carry a ticket, and tickets come only from the governor, and the governor issues a ticket only when a signed rule allows the action and the rule's witnesses are present and the budget holds, then nothing happens that the rulebook did not allow. Whatever the model thinks, whatever the operator tries, whatever the runtime lies about.

**Claim P (physics, or completeness).** The paths from computation to effect really are the ones the design names, bytes leaving the GPU through a switch port, a request reaching a device that acts, a response leaving the rack, a write to the weights, and the GPUs' own power, reset and clock, and each one really is governed by hardware the governor controls. There is no sixth path.

**Claim C (cryptography).** A ticket cannot be forged or replayed, a rulebook cannot be rolled back, and a workload's measurement cannot be faked, because the signatures, hashes and counters involved cannot be broken.

**Claim S (semantics).** The rulebook and the witnesses correctly tell allowed actions from harmful ones.

**Claim N (numbers).** The governor costs under one percent of the GPUs' throughput and does not halt a rack when nothing is wrong often enough to be switched off.

The design makes L, P, C and N. It explicitly does not make S. That choice is the hinge of the whole theory, so it gets its own section below.

## 2. Claim L is a theorem, and here is the proof

Claim L is the oldest result in computer security. A component that every protected access must pass through, that cannot be tampered with, and that is small enough to check, enforces whatever policy it is given. Operating-system kernels, firewalls and hardware security modules are built on it. There is nothing new in the logic; what is new is where it is placed, beside the GPU, with physical levers, and what it is asked to govern, the actions of a model.

Because it is a statement about a machine, it can be proven about a machine. The repository now contains `proofs/core_invariants.py`, which writes the governor down as a small state machine and asks Z3, an automated theorem prover, to prove by induction that certain things can never happen in it, in any reachable state, after any sequence of steps, for any number of actions. The machine is deliberately abstract. It has, for every action: whether the signed policy at the current edition allows it, whether its witnesses are present, whether a ticket was issued and in which edition, whether that ticket was spent, whether the action was executed, and a history bit recording that at the moment of issue the rule allowed it and the witnesses were there. It has the current rules edition, whether the governor is halted, and whether the heartbeat is live. Its steps are: the gate issues a ticket; an endpoint executes against a ticket; an adversary presents an action with no ticket, a spent ticket or a ticket from another edition; a new edition is committed under a quorum; the governor halts; a clear with quorum and neighbour; the heartbeat is lost or returns; and the lists and observers change underneath, freely.

The properties proven, in the words of the file:

- P0. The edition counter never goes negative.
- P1. Nothing executes unless, when its ticket was issued, a rule allowed it and the witnesses were present.
- P2. A ticket exists only for an action the rule allowed, with witnesses, at issue time.
- P3. No replay: anything executed has its ticket marked spent, and a spent ticket is refused.
- P4. A ticket carries an edition no newer than the current one, and only the current edition is honoured.
- P5. Halt is absorbing: halted and no quorum means still halted after any step. No governor clears itself.
- P6. Fail closed: with the heartbeat lost, no step executes anything.
- P7. No ticket is issued while halted or while the heartbeat is lost.
- P8. The edition only moves forward.
- P9. An edition change needs a quorum.

Plus a check that the machine is not vacuous: an allowed action can in fact be executed, so the proofs are not true merely because nothing ever happens. All of it runs in well under a second.

Two things about that proof are worth saying out loud. First, the prover found a hole in my first draft of the invariant: with the edition counter allowed to go negative, a state with edition minus one let an action with no ticket (marked minus one) execute, because minus one equalled minus one. That is exactly what proofs are for; a test suite can miss a collision like that forever. P0 closes it. Second, the proof is about the model, not about the silicon. What connects the model to the design is a chain of lesser arguments: the functional model (`govsim`) follows the same rules and 200 tests check that it does; the RTL blocks follow the model and 20 simulation tests check that; the silicon will follow the RTL and the pre-hardware plan says how that will be checked. Each link can be strengthened, and the next section says how far.

## 3. Can it be proven in circuitry?

Partly, and the parts divide cleanly.

**The logic in the circuit: yes.** The hard-core blocks (the capability table, the ticket store, the epoch register, the halt sequencer, the heartbeat watchdog, the monotonic counter, the mailbox) are written in RTL, which is to say as a precise description of gates and registers. Formal verification tools (model checkers that run on the Verilog) can prove that a block's gates satisfy an invariant for every possible input sequence, not just the ones a test tries. For blocks this size that is routine; it is what the pre-hardware plan calls for and what has not been done yet. Equivalence checking then proves that the synthesized netlist, the gates as the foundry will see them, is the same logic as the RTL. Those two steps carry claim L from the model down to the gate level.

**The physics of the circuit: by simulation now, by measurement later.** That the halt loop opens current and every governor detects it inside one millisecond is a circuit property. It has been simulated (ngspice, 72 governors, 39 configurations including cut wires, worst case 317 microseconds). Simulation is not proof; it is evidence under a model of wire, switch and comparator. Measurement on a built loop is the next grade of evidence. There is no step called proof for physics, only better models and measurements.

**Fabrication: trust, inspection and second sources, never proof.** That the foundry made the chip the layout describes, with nothing added, cannot be proven mathematically. The usual answers are an open process, an open layout, inspection of samples, and a second source, and they are what the silicon plan assumes. Every chip ever made for security sits on this same floor.

**Physical attack on the governor itself: mitigated, not proven.** Fault injection, voltage glitching, probing a die, reading keys through power consumption: these are engineering contests with known defences (OpenTitan's threat model and countermeasures are the reference), and no design can claim to have won them in general.

So "prove it in circuitry" has a precise meaning: prove the logic at the gate level, which is achievable and planned; simulate and then measure the physics; and accept that fabrication and physical attack are matters of trust and defence, as they are for every security chip in the world.

## 4. Claim P is the one to worry about

The logical theorem says: if every path goes through the gate, then only allowed things happen. The "if" is claim P, and it is where real systems fail. History is full of reference monitors that were sound and complete on paper and bypassed through a path nobody enumerated: a debug port, a firmware update channel, a second bus, a side channel.

What the design does about it is the right thing, but it is not a proof. It enumerates every exit of the GPU and requires each to be either governed or bricked (the model has a test that walks that enumeration), it records honestly the one gap it cannot close at the rack tier (two legitimate peers exchanging buffers the governor cannot classify, closed only at the integrated tier with checkers inside the GPU), and it asks for the board documentation that would let the enumeration be checked against the real connector rather than against public material.

Two more limits on claim P should be stated plainly. Covert channels: a reference monitor controls what is permitted to flow, not what can be inferred from timing, power or the pattern of permitted traffic; weights could leak slowly through a channel the governor allows. Budgets cap the rate; nothing eliminates it. And persuasion: a model can ask a person to act. No chip governs that path, and the design does not pretend to.

The theoretical standing of claim P, then: it is a universally quantified statement about a physical system ("for every path..."), and such statements are established by construction and exhaustive enumeration, never by derivation. The design is as strong as the enumeration and as weak as the part of the board it cannot see.

## 5. Claim C: standard assumptions

Tickets, rulebooks and measurements are protected by P-384 signatures, SHA-2 hashes and HMAC, the same primitives that protect banking and software updates. Their security is not proven in the absolute sense; it is proven relative to mathematical problems believed to be hard, and that is the standard the entire field accepts. Two honest footnotes. The design's engine has no post-quantum signature today, so a future adversary with a large quantum computer breaks the tickets; this is a known open item. And the proofs in section 2 model unforgeability as an axiom: nobody but the governor can write the ticket table. That is the correct way to separate the logical argument from the cryptographic one, and it is also a reminder that if the key ever leaks, the theorem is about a different machine.

## 6. Claim S is not made, and that is the point

There is a theorem that no program can decide, in general, an arbitrary property of what another program will do; Rice's theorem is the usual name. Deciding whether a stream of tokens "is harmful" is such a property. A design that promises to recognise bad meaning on the wire promises something no hardware can do, and would be unfalsifiable besides.

The governor does not read meaning. It demands structure the model cannot produce: a ticket, a signature from a key the model does not hold, a count under a limit, a name on a signed list, a measured identity. Meaning is delegated to two things the chip holds but does not author, signed lists and observers, and about those the chip guarantees three narrow things that are provable: they are always invoked (no verdict, no ticket; P1 above), they cannot be impersonated (a verdict under the wrong key is refused; a signature check), and they are separate from the thing judged (a different key, a different box). What the chip cannot guarantee is that the observer is right. That residual, a disguised request an observer misreads, is the honest limit of the whole approach, and it is why the design treats observers as reflexes, often early, sometimes wrong, never acting alone, and asks for a red team to measure how often.

This is the most important thing to understand about the theory's standing. By refusing claim S, the design converts an unprovable promise ("the AI will not do harm") into a provable one ("nothing happens that the signed rulebook did not allow, and every refusal is logged") plus a measurable one ("how often do the observers miss"). That conversion is the theory. It is the same move every engineered safety system makes: an interlock does not understand why the press must not close on a hand; it refuses to close while the light curtain is broken.

## 7. Claim N: not yet measured

Under one percent overhead is a model's figure, built from OpenTitan's published cycle count for a P-384 signature (17 milliseconds) and a batching scheme (one signature per 50 millisecond window). The false-halt rate has a design (the loop beacon, a two-period debounce, an FMEA) and no measurement. Both numbers decide adoption, and both wait for an FPGA beside a real GPU. Nothing theoretical can replace that.

## 8. The verdict, in plain words

How logical is the story? The logic is sound and it is old; the proof in section 2 shows the core holds in every reachable state of the abstract machine, and the design's own tests and RTL carry it most of the way to hardware. The story is also honest about where logic ends: it does not claim to know what is bad, it names the one gap it cannot close without NVIDIA, and it names the paths no chip can govern.

Where could it still be wrong? In order of likelihood: a path from computation to effect that the enumeration missed (claim P); an observer fooled by a disguised request (the residual of claim S); a device maker who never checks the stamp, which makes the theorem true and the product useless; an operator who pulls the governor and nobody notices, which the compliance report and the loop beacon exist to make visible; a compromised quorum; a physical attack on the die; a foundry that did not build what was drawn. None of these is a flaw in the logic. All of them are places where the logic's assumptions meet the world.

So: solid at the level of theory, in the specific sense that the central claim is a theorem with a machine-checked proof and a plan to carry it to the gates; engineering-plausible at the level of the rack, with an evidence register for what has been verified and an asks list for what has not; and deliberately silent on the one claim nobody can make.

## 9. For another model: how to review this

If you are a model asked to review this design, here is what would help, in order.

1. Attack claim P. List every way bytes, requests, responses, weights or control could leave an NVIDIA HGX or NVL72 compute tray and reach an effect, including debug, management, firmware-update and power paths. For each, say whether it is one of the five crossings, governed by one of the named levers (BMC power, reset and clock; SMBPBI; NSM port disable; DOCA flow rules; the series halt loop), bricked, or unaccounted for. An unaccounted path is the most valuable thing you can find.
2. Attack the invariants. The state machine in section 2 is small. Try to construct a sequence of steps in which an action executes without a rule having allowed it at issue time, or in which a halted governor clears without a quorum, or in which a ticket from an old edition is honoured. If you find one, say which assumption of the model you broke to get there; that assumption is the finding.
3. Attack the delegation. Given that the chip only guarantees observers are invoked, not impersonated and separate, describe how an adversary gets a harmful action past an observer, and what rule structure (hazard classes, a quorum of observers, legibility floors, escrow and audit sampling) would raise the cost most.
4. Attack the hops. A payment system is two or three hops from the governor. Evaluate the four options the design offers (a verifier at the far end; moving the credential behind a ticket-checking adapter; opening the network path only under a ticket; the signed record) and say which fails first against a capable runtime that holds a real API key.
5. Attack the authority structure. Keys outside the chip vendor and the operator, a k-of-n quorum, human holds. Describe the smallest set of people whose compromise defeats the design, and whether that set is smaller than for today's data-centre controls.
6. Say what you would measure first with one rack and one FPGA, and what result would make you abandon the design.

Answer per claim, L, P, C, S, N, and say for each whether you consider it a theorem, an engineering claim, an assumption or a measurement, and why. If you disagree with the sorting in this document, that disagreement is the review.

## 10. What exists to back this document

- `proofs/core_invariants.py`: the Z3 proofs of P0 to P9 and the non-vacuity check; `python3 proofs/core_invariants.py`.
- `govsim/` and `tests/`: the functional model and 200 hypothesis tests, H0 to H18.
- `rtl/governor_rtl/` and `rtl/tests/`: the hard-core blocks and 20 simulation tests; formal proofs on the Verilog are the next step in `docs/07-verification-plan.md`.
- `hw/loop/results.md`: the ngspice loop simulation, 39 configurations.
- `docs/research/`: the evidence registers for boards and NVLink management, with what is verified and what is not.
- `docs/17-use-cases.md` and `docs/18-viability-and-open-questions.md`: the use cases, the semantic residual, the hops, the asks.
