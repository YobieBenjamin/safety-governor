# 18. Viability, reach and adoption: what the governor can promise, where its authority ends, who would buy it

This document writes down the last discussion in one place. Four questions were asked in plain words and deserve plain answers. Is the governor chip plausible, or is it barking up the wrong tree? What can it do now, and what only with asks that other companies must grant? What happens to its authority when the thing that acts is a connected system two or three hops away from the chip, such as a payment system that is outside the model and outside the rack? And would anyone adopt it: is this one of the ways to strengthen the safety promise of an NVIDIA system from the chip's point of view, or a curiosity? A fifth question arrived while this was being written: is this just a firewall at the chip level? It gets its own section, because the analogy is good and its limits are the limits of the design.

Where a sentence rests on something that runs, a box names it. Where it rests on a judgement, it says so.

## 1. The short answer

The governor is plausible as an engineering object. It is not a new kind of thing. It is a reference monitor, an idea written down in 1972: a small component that every protected access passes through, that cannot be tampered with, and that is small enough to be checked. Operating systems have one. Firewalls are one for packets. Smart cards and hardware security modules are one for keys. The governor is one for the places where a model's computation turns into effect: bytes leaving a GPU, a request to a device that acts, a response leaving the rack, a write to the model's weights, and the power and reset of the GPUs themselves.

The intuition in the question, that it "would require some sort of a back end embedded in the chip itself of prohibited actions", is half right, and the half that is wrong matters. What is embedded in the chip is how to enforce: the keys, the fail-closed state machine, the invariants that no firmware update can remove (no ticket without a verdict, no bytes to a peer not on the roster, halt on silence, no clearing your own halt). What is loaded into the chip is what is allowed: an allow-list, signed by several parties, with a default of no. A list of prohibited actions burned into silicon would be out of date on the day of tape-out and would have to name every bad thing in advance, which nobody can do. A list of permitted actions is short, can be written down, and makes everything not on it refused by construction. The chip holds the referee's whistle. The rulebook is a signed document it is handed.

Then the one sentence that decides the viability question. The governor's authority is exactly as wide as the set of devices that check its signatures, plus the set of things it can physically stop. Not one inch wider. Everything below is that sentence applied to real systems.

> **Backed by.** The policy image is an allow-list with default deny (`make_policy` and `make_rule` in `govsim/policy.py`); a request with no matching rule is refused at the gate, and none of the 200 tests in `tests/` grants anything without a rule. The quorum over the image and the refusal of rollback are `tests/test_contract_policy_quorum_no_rollback.py`. The invariants firmware cannot remove are the blocks under `rtl/governor_rtl/` with their 20 tests in `rtl/tests/test_blocks.py`. A governor cannot clear its own halt: `test_governor_cannot_clear_itself` in `tests/test_contract_halt_reaches_every_gpu.py`.

## 2. Is it a firewall at the chip level?

Yes, in lineage. A firewall is a reference monitor for packets, and most of what makes a firewall work makes the governor work:

- It sits at a chokepoint. The firewall sits where the network narrows to one cable; the governor sits where the GPU's traffic narrows to a switch port, where an action narrows to a ticket, where a response narrows to the egress.
- It denies by default and allows by list. Nobody writes a firewall rule for every bad packet. They write the few rules for traffic that may pass.
- It is stateful. A modern firewall tracks connections; the governor tracks sessions, budgets and epochs, so the hundredth small request can be refused when the first ninety-nine were allowed.
- It segments. VLANs and zones keep tenants apart; buffer classes keep weights, activations and outputs on different lanes.
- It logs, and the log is what the auditor reads.

Three things make it more than a firewall. First, it has a hand on the breaker. A firewall can drop a packet; it cannot cut power to the sender. The governor can: power, reset and clock levers on the trays, port disable on the switches, and the series halt loop that takes the whole domain down when any member opens it. Second, it knows who is talking by measurement, not by address. A firewall rule names an IP; a governor rule names a hash of GPU firmware, host firmware and model weights, taken out of band and signed through a key chain rooted in the die. A packet can forge its source address; a workload cannot forge its measurement. Third, it is a separate die with its own root of trust, so the host cannot patch it, and a "firewall rule change" needs several signatures from keys outside the rack.

Two things make it less than a firewall, and they are the honest part. A firewall sees every packet because the topology forces every packet through it. The governor sees a crossing only where the device on the far side checks its ticket, or where the switch in the path is under its authority. Where neither is true there is no firewall at all, only a log. And like a firewall, it cannot read what it carries. Deep packet inspection and intrusion detection were bolted onto firewalls to look inside the payload; the observers in this design (classifiers and people with keys, signing verdicts over hashes) are the same bolt-on, with the same limit: a disguised payload gets through a detector that does not recognise it. A firewall also never stopped an attack that stayed on one side of it; a model that persuades a person through an allowed channel has stayed on one side.

So the fair summary is: a firewall for actions rather than packets, with a hand on the breaker, whose reach is set by who checks its stamps. The rest of this document is about that reach.

> **Backed by.** Default deny and roster-only flow at every switch: `test_roster_peer_passes_and_stranger_is_blocked_at_every_switch` and `test_every_enumerated_exit_is_governed_or_bricked_at_rack_tier` (`tests/test_contract_every_crossing_governed.py`). Stateful budgets: `test_byte_budget_on_a_capability_is_enforced` (CONTRACT-EVERY-CROSSING-GOVERNED) and `test_compute_budget_throttles_without_a_license` (`tests/test_contract_oversight_survives_model.py`). Segments: `test_integrated_checker_refuses_weights_to_a_roster_peer` (CONTRACT-DESCRIPTOR-LEVEL-ROSTER-GAP). The breaker: `tests/test_contract_halt_reaches_every_gpu.py` and `tests/test_contract_levers_without_gpu_cooperation.py`; the loop as a circuit in `docs/11-loop-timing.md`. Identity by measurement: `tests/test_contract_attestation_binds_permissions.py`. The limit of observers: `docs/17-use-cases.md` §4.

## 3. What exists today, and what does not

What exists is a model, a set of hardware blocks, a circuit simulation and an audit, not a chip.

- A functional model of the governor and a simulated rack (`govsim/`), with 200 hypothesis tests covering nineteen contracts: attestation, enforcement points, quorum, lanes, alarms, the endpoint comparator, the assumptions register, override, overhead, leakage, the halt loop, fabric authentication, shared budgets, partitions, tamper, levers, the use cases and oversight.
- The hard-core blocks in RTL (Amaranth), with 20 simulation tests, and a LibreLane flow to sky130 that places the core at about two square millimetres as configured.
- The halt loop as a circuit in ngspice: seventy-two governors, worst case 317 microseconds from a switch opening to the last governor detecting it, against a one millisecond budget, across thirty-nine configurations including wire breaks.
- Two evidence registers from the October research pass (which boards expose which levers; what NVLink authority exists out of band and in band) and an audit that found and fixed the design's own earlier errors, with the sources it checked and the claims still unverified.

What the design leans on at the rack tier already ships. Power, reset and clock control for the trays live in the OEM's baseboard management controller and the signals it drives. NVIDIA's out-of-band management (SMBPBI to the GPUs, NSM to the switches through the OpenBMC stack) can disable a device and disable a switch port, and the NVL72 BMC drives the power brake, the run-power enable and the system reset at tray level. The DPU's steering tables take flow rules through its own management port. Confidential computing on the GPU gives an attestation the governor can take as an input. The design needs nothing from NVIDIA's silicon to operate at this tier; it needs the OEM's management-module slot and the signals the HGX baseboard already brings to its connector.

What does not exist: silicon; a measurement of the overhead on a real GPU (the 17 millisecond signature is OpenTitan's published OTBN figure, and the one percent whole-deployment number is a model with that figure in it); a single endpoint vendor whose device checks the ticket; a proof that the firmware matches the model; and a policy written by anyone for anything real.

> **Backed by.** `python -m pytest tests` (200 passed) and `python -m pytest rtl/tests` (20 passed); `make loop` and `hw/loop/results.md`; `docs/research/board-lever-register.md` and `docs/research/nvswitch-management.md` with their evidence levels; `docs/AUDIT-2026-10.md` §"Still unverified". The cost figures and their provenance: `govsim/bench.py` (`OTBN_P384_SIGN_CYCLES = 1_697_985`), `tests/test_contract_governor_overhead_bounded.py`, and `docs/10-plain-english-walkthrough.md` §14.

## 4. Three rings of authority: now, with asks, never

It helps to draw the governor's authority as three rings.

The inner ring is physical and available now, with an OEM and no one else. Power, reset and clock for each tray through the BMC's levers. Port disable on the NVSwitch and PCIe switches through the management paths. Flow rules in the DPU. The halt loop between governors. Within this ring the governor does not ask anyone's permission to stop a GPU; it opens a switch and the current stops. This is the ring the whole safety claim rests on. If the model does something the governor cannot even name, the ring still lets it halt the compute and prove that it did.

The middle ring needs asks. Per-GPU reset on the HGX baseboard, where reset is grouped today. A per-module power brake visible at the connector. Buffer-class checkers in the copy engines and the peer MMU, which only NVIDIA can build (the integrated tier). The in-band lockout flags documented and guaranteed. Each ask is firmware or board work, not a new GPU; each one tightens the design rather than enabling it. Without them the governor still works; it is coarser (a reset takes a group of GPUs down instead of one) and one gap stays open (CONTRACT-DESCRIPTOR-LEVEL-ROSTER-GAP at rack tier: two roster peers can exchange buffers the governor cannot classify).

The outer ring is what the chip will never hold on its own: what the far end of an allowed channel does with what it receives. A bank, a message recipient, a shipping company, a person. The governor can decide whether the channel opens and record that it did. It cannot reach through the channel. This ring is the subject of the next section, because it is where the hard question lives.

> **Backed by.** The inner ring: `tests/test_contract_levers_without_gpu_cooperation.py` and `hw/pcb/rack-integration.md`; the per-board evidence in `docs/research/board-lever-register.md`. The middle ring: the seven firmware asks in `docs/research/nvswitch-management.md` and `docs/03-interfaces.md` §9; the rack-tier gap is recorded, not hidden, by `test_descriptor_level_leak_between_roster_members_is_the_recorded_gap` (CONTRACT-DESCRIPTOR-LEVEL-ROSTER-GAP).

## 5. The connected-systems problem: a payment two or three hops away

The sharpest question in the discussion was this one. A payment system is external to the model and external to the chip. It is two hops away, maybe three. Where does the governor's power run out, and what is left when it does?

Take the chain one hop at a time, with an agent that has decided to pay someone.

**Hop 0: the model computes.** The weights produce tokens that say "transfer 40,000 to account X". The governor has no authority here and needs none. Thinking moves no money. If the design ever claimed to catch the thought, it would be claiming what no chip can do.

**Hop 1: the agent runtime asks for a ticket.** The broker on the host turns the tokens into a typed request, `payments.transfer` with an amount, a currency, a destination and a session, and presents it at the governor's mailbox. Here the authority is complete. The governor checks the workload's measurement, the rules edition, the signature, then the rule: is this action allowed for this workload, is the destination on a signed list, is the amount under the limit, is a human hold required, is the session's budget exhausted. It refuses, holds or signs a ticket that binds a hash of exactly those fields. The broker cannot mint a ticket and cannot alter one; a changed amount changes the hash.

**Hop 2: the host process makes the call.** The runtime, holding the ticket, opens an HTTPS connection through the NIC or the DPU to the payment provider's API. The governor's authority here is partial and physical. If the DPU is on the path, its steering tables, programmed out of band, decide whether this host may reach that provider's addresses at all, and under what session. If the egress endpoint is on the path, it can hold bytes until a ticket releases them. What the DPU cannot do is read inside the TLS session. It cannot tell a transfer of forty from a transfer of forty thousand. It governs the door, not the conversation.

**Hop 3: the provider's gateway accepts the request.** The provider checks an API key or an OAuth token. It has never heard of the governor. Unless it checks tickets, the governor's authority here is zero. The ticket in the request is a stamp nobody at this desk recognises.

**Hop 4: the ledger moves the money.** No authority, ever. This is someone else's reference monitor.

So the plain statement is: the governor's authority ends at the last device that verifies its signature. Past that point the chain is other people's systems, exactly as it is for every other control in computing. The perimeter firewall decides whether the packet leaves; it does not decide what the server on the far side does with it. Anyone who tells you otherwise about a chip is selling something.

What the design can do about hop 3 is the useful part, and there are four options, strongest first. They are not exclusive; a real deployment uses the first that is available for each connection and the last for all of them.

**Option A: the far end checks the ticket.** The provider's gateway holds the governors' public keys (as every endpoint in the model does), verifies the ticket's signature and epoch, compares the ticket's bound fields with the request it is actually receiving (amount, currency, destination, session), and refuses on any mismatch, any replay, any stale epoch, or any ticket meant for a different endpoint. This is what the model's payment switch is: an `ActionEndpoint` with a comparator. It is the strongest option because the check happens inside the thing that acts, and a broker that lies about the amount is caught by the device, not by the governor. The cost is a verifier at the provider: verify a P-384 signature, compare a handful of typed fields, check freshness. Providers already verify signed webhooks, OAuth tokens and signed requests; this is one more verifier, not a new discipline. It is realistic for a few high-value integrations (an operator's own treasury system, a trading venue, an enterprise payment rail that already has a policy engine, a wallet with a policy module) and not realistic for the open internet.

**Option B: move the credential, and the hops collapse.** Most of the three-hop problem is really a credential problem. If the host process holds the bank's API key, the governor cannot take it back, and the model's runtime can call the bank whenever it likes, ticket or no ticket. If a small adapter holds the key instead, and the host can only ask the adapter to make the call, then the adapter is an endpoint in the model's sense: it verifies the ticket, compares the fields, makes the call with the credential the model never had, and logs the result. The payment system is still three hops from the chip, but the credential is one hop from the chip, and the credential is what moves the money. This pattern already exists under several names: a secrets broker, an egress proxy, a tool gateway. The adapter can run on the DPU, on a separate attested box, or as a process whose measurement the governor checks like any other. It is the practical answer for most external systems, because it needs nothing from the provider and one adapter covers every tool the operator exposes to its agents.

**Option C: the door under ticket.** Where neither A nor B is possible, the DPU's flow rules can open the path to the provider's addresses only while a ticket for that session is live, and close it otherwise. The governor cannot see the amount, but the model cannot reach the provider at all without a ticket, and a session that has exhausted its budget cannot reach it again. Coarse, but physical, and already in the design's inner ring.

**Option D: the record.** Always available. The governor signs a record that a ticket was issued, or refused, or held, and the DPU logs that a flow opened. After the fact the question "did the governor permit this?" has an answer with a signature on it and a counter that cannot be rewound. This is the weakest option for prevention and the strongest for accountability; it turns "the model did it" into "the model did it and here is the ticket, signed, with the approver's key on it", or into "there was no ticket, and the flow is the gap".

The same chain, as a table:

| Hop | Who holds authority | What the governor can enforce | What it cannot see | How to close the gap |
|---|---|---|---|---|
| 0. Model computes | Nobody | Nothing, and nothing is needed | The intent | Not a chip's job |
| 1. Runtime requests a ticket | Governor, fully | Rule, list, limit, budget, hold, quorum; the ticket binds the exact fields | Whether the typed fields are a true description of what the runtime will do | The comparator at the endpoint (A or B) |
| 2. Host calls out through DPU or NIC | Governor, partially | Which addresses, which session, whether the door is open; egress hold on responses | Anything inside TLS; the amount | Option B puts the credential behind an endpoint |
| 3. Provider's gateway | Provider | Nothing, unless the gateway verifies tickets | Everything | Option A, a verifier at the provider |
| 4. Ledger | Provider | Nothing | Everything | Never; this is their reference monitor |

What stays open even with A and B in place, stated so nobody reads this as solved:

1. The mapping between a ticket's typed fields and the provider's API is per integration. Amount, currency and destination have to mean the same thing on both sides, and that is engineering work each time, with its own chance of error.
2. The adapter is a new trusted component. It is small, but it has to be attested through the same key chain as the host, or it is a soft spot. The design has the mechanism (workload measurement, heartbeat, epoch) and has not yet exercised it on an adapter.
3. Time of check against time of use. The ticket binds a hash of the fields; the adapter must send exactly those fields, and the provider must act on exactly what it received. A provider that rounds, retries or batches can act on something slightly different from what was signed.
4. Holds for high-value actions are policy, not silicon. The chip can make a human signature mandatory and slow; it cannot make the human right.
5. The hop in the other direction. A model can ask a person to make the payment. No chip stops persuasion through an allowed channel. This is the semantic residual from the use-case document, wearing a different coat.

> **Backed by.** Hop 1 is the `plot` narration (`python -m govsim.cli usecase plot`): `REQUEST payments.transfer` ends in `gate.held_for_human`, and the run finishes with payments executed 0. The comparator that catches a lying broker: `test_compromised_broker_lies_about_the_target` and `test_spoofed_navigation_disagrees_and_is_denied` in `tests/test_contract_comparator_survives_compromise.py`. Ticket binding and replay: `test_forged_replayed_wrong_session_and_wrong_hash_tickets_never_deliver` (`tests/test_contract_no_action_without_ticket.py`) and `test_switch_refuses_forged_altered_and_foreign_capabilities` (CONTRACT-EVERY-CROSSING-GOVERNED). An endpoint that loses the heartbeat refuses everything: `test_endpoint_with_dead_heartbeat_refuses_everything` (CONTRACT-COMPARATOR-SURVIVES-COMPROMISE). The door under ticket is the DPU section of `docs/03-interfaces.md` (§6) and the flow rows of its interface table. Option B is a pattern the model's `ActionEndpoint` already expresses (`govsim/endpoints.py`, `admit` then `execute`), but no narration yet runs a three-hop payment through an adapter; that is listed in §9 as the next bounded piece of work. Everything in the numbered list is a judgement.

## 6. Adoption: who moves first, and why they would

The guarantee lives in the device that acts. That one fact shapes adoption more than any feature. The governor is not one sale; it is a sequence of endpoints, each of which has to decide to check a stamp.

The order that seems most likely, from easiest to hardest:

**First, verification and compliance.** This needs no endpoint at all. With the levers an OEM's management module already reaches, the governor can answer three questions with a signature from a key outside the vendor's and outside the operator's hands: what ran (the measured workload), under which rules (the co-signed edition and its history), and could it have been stopped (the halt loop, exercised and logged). The meter counts tokens and cycles from the GPU's own counters, out of band. The compliance report is a quote with a nonce, so it cannot be replayed. A regulator, an insurer, a counterparty or a board gets a signed answer instead of a vendor's word. This is the wedge because it is cheap, it needs nobody's cooperation but the OEM's, and the thing it sells (an independent signer) is something neither NVIDIA nor the operator can supply for themselves by definition. Goal GOAL-KEYS-OUT-OF-VENDOR-HANDS in the objectives, keeping the governance keys out of the chip vendor's hands and out of the operator's hands, is the product here.

**Second, the operator's own tool gateway.** Option B from the last section. An operator that runs agents already routes their tool calls through something. Putting the ticket check into that something covers every tool the agents can reach, with one integration, and moves every credential out of the model's reach. This is where the governor begins to prevent rather than record.

**Third, functional-safety endpoints.** The weapons-release case, and its civilian relatives: a grid breaker, an infusion pump, a train interlock, an industrial robot. These industries already pay for an independent safety channel (a safety PLC, a protection relay, an interlock computer) and already verify it to IEC 61508 or its cousins. They do not need to be persuaded that a separate referee is worth having; they need to be shown that the ticket and the comparator fit their existing architecture. The vendors of those devices exist and are used to this kind of certification. They are the natural partners for the comparator-in-the-device, and the chip's own FMEA and proof-assumption list speak their language.

**Fourth, the integrated tier.** Checkers in the copy engines and the peer MMU, per-GPU reset, a per-module power brake. This needs NVIDIA, and it comes last because everything before it works without it.

Who pays and who says no:

- The OEM pays a module on the management card and gains a feature to sell, and a new failure mode to support. "The governor halted my rack" will be the first support ticket, and the false-halt rate is the number operators will ask for first. The loop beacon, the two-sense-period debounce and the FMEA exist for this reason, and none of them has been measured on real hardware.
- The cloud provider has the multi-tenant question: whose policy governs a shared rack. The design has partitions and per-rule approvers; it does not yet have an answer to two tenants with two quorums on one baseboard.
- The operator has the governance question: who holds the k-of-n keys, who writes the allow-list, who answers a hold at three in the morning. The chip makes those roles enforceable; it does not fill them.
- NVIDIA may see a third party's trust anchor on its baseboard as competition, or as the one thing its own stack cannot provide. The next section is about which.

The hard adoption truths, said once: a chip that nobody wires to anything that acts is a logger; a logger that nobody reads is a heatsink; and the first year of any safety system is spent proving that it does not fire when it should not.

### The false-halt and review economics, as an acceptance envelope (F28)

*Added 24 October 2026, prompted by the external audit. The adoption cost is not one number; it is a set of budgets, and none of them has been measured. They are written here as an envelope a deployment must accept, with the measurement that would discharge each.*

The halt domain is shared, and that is the whole cost. One governor's local false alarm halts its failure domain, and the plan-of-record domain is a 72-GPU rack sharing one loop and one epoch, so a single local false alarm can take 72 GPUs down at once. Worse, for a fixed recovery time the lost GPU-time grows roughly as the square of the domain: a domain twice as wide has twice as many GPUs to lose and, at a per-GPU alarm rate, twice as many alarms to lose them, so the product grows about fourfold. The review side scales the same way on people: a gateway making a million benign decisions a day at a 1 percent false-hold rate parks about 10,000 of them for a human, which at one minute of review each is about 167 staff-hours a day, a day that has only 24. These figures are arithmetic from assumed rates, not measurements; the real rates are exactly what is unmeasured.

So the design states separate acceptance budgets, each a number a deployment must set and then measure against, not a single "overhead":

| Budget | What it bounds | How it would be measured (not yet measured) |
|---|---|---|
| False holds per benign decisions | Benign actions parked for a human that should not have been | A staffed gateway pilot counting holds against adjudicated-benign volume |
| False halts per domain-hour | Halts of a failure domain with no real cause | A rack trial running the loop beacon for weeks with no injected fault |
| Legitimate denials | Actions correctly refused or held; a cost to the workload even when correct | The same pilot, separating correct denials from false ones |
| Recovery time per halt | Wall-clock from a halt to a cleared, running domain | The rack trial, timing the clear-and-resume path |
| Lost useful work | GPU-hours and staff-hours lost to the above, per domain per period | Both trials, combining domain size, alarm rate and recovery time |

Two design obligations follow and are owed:

- **The smallest safe failure domain.** The domain should be the smallest region that is still safe to halt as a unit, so a local false alarm costs the least work, and the recovery process (detect, clear with the authority's signature, resume, with the cause in the log) should be fast and rehearsed. The plan-of-record 72-GPU domain is a ceiling to argue down, not a target; partitioning the loop and the epoch into smaller domains is an open design task tied to question 7 (the multi-tenant rack).
- **Zero observed is not zero.** A trial that runs for a time and sees no false halt does not establish a zero rate. With no events observed in a window, the honest result is a Poisson upper bound on the rate at a stated confidence (roughly three over the observed domain-hours at 95 percent), never a claim of a zero rate. Any report of these budgets must state the upper bound and the exposure behind it, not a bare "none seen".

Until a rack trial and a staffed gateway pilot produce these numbers (WAVE-FALSE-HALT-RATE-MODEL in `docs/20`, question 3 in section 8), the budgets are targets with a model behind them. None of the figures above is a measurement.

> **Backed by.** The meter and the compliance report: `test_compliance_report_is_signed_through_the_device_key_chain_and_reflects_the_meter` and `test_compliance_report_lists_every_epoch_and_survives_a_restart_and_refuses_a_nonce_replay` (`tests/test_contract_oversight_survives_model.py`). Edition history and rollback refusal: `tests/test_contract_policy_quorum_no_rollback.py`. Verifiable halt: `test_halt_cause_is_broadcast`, `test_power_cycle_does_not_clear_a_halt` (CONTRACT-HALT-REACHES-EVERY-GPU). GOAL-KEYS-OUT-OF-VENDOR-HANDS and the acceptance rule: `docs/00-objectives.md`. The false-halt question: `test_healthy_rack_raises_no_loop_alarm_over_twenty_heartbeats` and `test_legitimate_halt_and_clear_is_not_mistaken_for_a_jumper` (CONTRACT-HALT-REACHES-EVERY-GPU) in the model; the FMEA in `docs/07-verification-plan.md`; no hardware measurement yet. The adoption order is a judgement.

## 7. Does it strengthen NVIDIA's safety promise, from the chip's point of view?

NVIDIA's safety and security promise, as it stands, is a set of vendor-signed controls. Confidential computing attests the GPU's trusted environment under NVIDIA's key. Protected PCIe, the switch and port controls through NSM, device disable through SMBPBI, Fabric Manager's partitions, and Sentry, the agent safety platform announced in September 2026 for the BlueField-4 DPU, are each NVIDIA's firmware on NVIDIA's silicon, signed by NVIDIA. They are good pieces. They share one property: the party making the safety claim is the party that built and sold the thing the claim is about.

That is the gap the governor fills, and it is a gap NVIDIA cannot fill for itself however good its engineering is. Four things the governor adds:

1. **An independent signer.** A claim about an NVIDIA system signed only by NVIDIA is a vendor attestation. With the governor it becomes a two-party attestation: NVIDIA's measurement as an input, a referee's signature over the policy decision as the output, under a key rooted outside NVIDIA and outside the operator. That is the difference between a company's own statement and an audit. Regulators and insurers price that difference; it is the only kind of safety claim they can act on.
2. **A stop that does not run through the thing being stopped.** NVIDIA's controls are firmware on the GPU, the switch and the DPU. If that firmware is the thing that has gone wrong, or has been replaced, the control goes with it. The halt loop, the power and reset levers and the port disables are driven from a separate die through the management plane, and the loop is a wire. Loss of trust in the GPU's firmware does not cost the ability to halt it.
3. **One enforcement domain across vendors and racks.** The fabric, the cluster-wide epoch, the shared budgets and the cross-linked logs make seventy-two GPUs, their switches and their DPUs one governed thing, and the same chip governs a non-NVIDIA accelerator or an endpoint from a safety vendor. NVIDIA's stack governs NVIDIA's parts.
4. **Default deny at the level of actions.** NVIDIA does not make the things that act. It has no place to put a comparator in a guidance computer or a payment adapter. The ticket is a vocabulary those devices can speak, and the governor is the only party in the rack positioned to issue it.

This is complementary, not competitive. The governor consumes confidential-computing attestation as an input, uses NSM for port disable and SMBPBI for device disable, programs the DPU through DOCA, and can take a Sentry-class filter as one observer among several. It replaces none of them. It makes their outputs part of a claim that someone other than NVIDIA signs.

The honest counterpoint, so that this is not a sales document: NVIDIA could build most of this into its own silicon faster and better. If it did, every property above except the first would be served, and the first would then be the whole argument. An independent signer is not a chip; it is a governance arrangement that happens to need a chip to be enforceable. If NVIDIA offered a slot for a third-party root of trust on the baseboard, with the levers brought to it, that would be the best outcome for the design and would also make most of this repository an ask that had been granted.

So, from the chip's point of view: yes, it strengthens the promise, in the specific way of turning a vendor's statement into an auditable one and a firmware control into a physical one. It does not make the GPU safer by itself. It makes the claim that the GPU is being used safely checkable by people who do not have to trust NVIDIA, or the operator, to check it.

> **Backed by.** The inputs consumed are the interface rows in `docs/03-interfaces.md` (the GPU at §2, the switches at §3, the host at §4, the DPU at §6) and the NSM and SMBPBI evidence in `docs/research/nvswitch-management.md`. The two-party signature is the device key chain in `test_compliance_report_is_signed_through_the_device_key_chain_and_reflects_the_meter` (CONTRACT-OVERSIGHT-SURVIVES-MODEL). The stop outside the GPU's firmware is `tests/test_contract_levers_without_gpu_cooperation.py` and the circuit in `docs/11-loop-timing.md`. Sentry's scope and date are recorded in `docs/AUDIT-2026-10.md`. The judgement about what NVIDIA could build is a judgement.

## 8. Open questions, with what would settle each

| # | Open question | What would settle it | Who |
|---|---|---|---|
| 1 | Will any device that acts verify the ticket? | One partner integration: a tool gateway or a functional-safety endpoint with the comparator | Operator or safety vendor |
| 2 | How often do observers misread a disguised request? | Never fully settled; measured error rates per observer, a quorum of observers on high-hazard classes, red-team runs against the release gate | Model labs, auditors |
| 3 | What is the false-halt rate, and what does a halt cost? | Hardware-in-the-loop on a real rack; the FMEA with measured failure rates; the loop beacon exercised for months | OEM, operator |
| 4 | Which per-module levers does the HGX connector carry? | The design guide under NDA; the connector pinout; a bench measurement | NVIDIA, OEM |
| 5 | What is the real overhead? | An FPGA prototype beside a real GPU, measuring the three numbers (firmware share, engine utilisation, record latency) | This program |
| 6 | Who holds the quorum keys and writes the allow-list? | Not engineering: a governance arrangement with named roles, rehearsed | Operator, regulator |
| 7 | Whose policy governs a shared, multi-tenant rack? | Per-partition policies with separate quorums; not yet designed | Cloud provider, this program |
| 8 | Can the integrated tier be built? | NVIDIA accepting the copy-engine and peer-MMU checker asks | NVIDIA |
| 9 | Post-quantum signatures? | OTBN has no ML-DSA today; a future OpenTitan release or a software implementation with a measured cost | OpenTitan, this program |
| 10 | Who fabs and signs the governor itself? | An open process and a shuttle for the prototype; a second source and a published firmware signing policy for the product | This program |
| 11 | Who is liable when the governor wrongly halts a medical or financial workload? | Not engineering: contracts and regulation | Lawyers |
| 12 | Is the adapter (option B) a soft spot? | Attest it through the same key chain; a narration that runs a three-hop payment through it; a test that a replaced adapter is refused | This program |
| 13 | Does the typed request describe what the runtime will really do? | The comparator at the endpoint for every field that matters; a review of each integration's field mapping | Per integration |
| 14 | Can a model route around the governed path by persuading a person? | No chip answer; the record shows what was and was not ticketed, and the observers can flag the attempt | Policy, people |
| 15 | Is the supply chain and the module's enclosure a condition of trust, as the flexHEG work treats it, rather than a footnote? | A written supply-chain assumption in the register (`06`): who makes the die, who assembles the module, how a swapped or opened module is detected (the tamper mesh in `04` §11 and the roster's refusal of an unknown chip in `05`), and a second source; borrowed from the flexHEG report, §8b | This program, then a board partner |
| 16 | Should the governance root be multilateral, with the k of n keys held by parties who do not share a jurisdiction or an employer? | A key-holding arrangement written down and rehearsed (question 6 says who; this says how far apart they must be); the policy loader already accepts any k of n, so this is governance, not silicon; borrowed from the flexHEG report, §8b | Operator, regulator, this program for the rehearsal |
| 17 | Across sites: how do governors in different data centers share one rulebook, bounded time and one root? The loop is per site by design (`23`); the heartbeat, editions and partitions carry over any link; but editions, reservations and expiries need the sites' clocks within a known bound, which a per-chip monotonic counter cannot give across sites | A hierarchy written down and simulated: a global root (question 16) signs a per-site authority; each site runs its own heartbeat with local latency; cross-site tickets name both editions; the fabric between site supervisors runs over a dedicated or tunnelled link with the same signing and sequencing. Settled by a two-site run of `govsim` with a modelled wide-area delay and a per-site authority, as a new experiment; Part 7 of the blog carries the argument | This program, then an operator with two sites |

| 18 | Who outside the signers can read the log, and on what terms? The signed checkpoints are readable by anyone (`LOG_CHECKPOINT`, `04` section 3), so anyone can check the log was not rewritten; who can read its contents is not designed | A read-access policy for log contents, written as part of the signed rulebook, with the checkpoints staying public; a simulation of an outside auditor checking a sample against the public checkpoints. Section 8c; GitHub issue EXPERIMENT-LOG-READ-ACCESS-POLICY | This program, operator, regulator |
| 19 | How does a party affected by a gated action contest a ticket, or reopen the rules? Today only insiders can: the quorum override (CONTRACT-OVERRIDE-SLOW-AND-LOGGED) and the hold for named approvers | A contest lane: a signed objection that holds the ticket for a separate quorum, with its own reason code and timer; a simulation showing it closes the gap without becoming a denial-of-service lever. Section 8c; GitHub issue EXPERIMENT-AFFECTED-PARTY-CONTEST-LANE | This program, operator, regulator |
| 20 | The origin gate: can a model be made unable to run anywhere but on governed hardware, by sealing its weights to the governor and letting the governor release the key only to an attested GPU, while the signed rulebook lists the model? | A simulation of key release and revocation while running (done 23 October: `results/origin-gate.md`, every check holds); then the GPU's real decryption cost and lease enforcement on a confidential-computing GPU, which needs NVIDIA's firmware to honour the lease. Section 8d; GitHub issue EXPERIMENT-ORIGIN-GATE | This program, then NVIDIA |
| 21 | Does the gate hold against an agent that adds roads? The kill-switch argument (`23`) counts cuts on a fixed graph; a goal-directed agent changes the graph (orders hardware, opens accounts, messages people). Every such step is itself an action that needs a ticket, but whether the rulebook covers every road-building step is untested | A simulation in govsim: a planning agent rewarded for reaching an ungated effector, whose only moves are the actions the rulebook gates, searching sequences of them. Section 8e; GitHub issue EXPERIMENT-ROAD-REACHABILITY | This program |
| 22 | Can the gate stop a wire that follows every rule but that the customer never meant? A rule that requires the payer's own signature before a ticket, so the agent cannot speak for the customer | A payment rule whose witness must be the key a signed customer registry lists for the paying account; a simulation with an agent sending intended and unintended wires. Section 8f; GitHub issue EXPERIMENT-CUSTOMER-CONFIRMATION | This program, then a payments partner |
| 23 | Replication by packets: an agent can move bytes indistinguishable from any other traffic. Does destination-and-volume gating, with no content inspection, hold its weights inside a governed rack? | Measured (23 October: `results/containment.md`, EXPERIMENT-EGRESS-CONTAINMENT): off-roster flows refused at every exit; the permitted ceiling makes moving a model take decades under a tight policy; stated honestly, a busy-service budget leaks a small model over time, and a weightless agent or an ungoverned host is outside it. The empirical dispute runs on an abliterated model next. Section 8g; GitHub issue EXPERIMENT-EGRESS-CONTAINMENT | This program |
Questions 1, 3, 5, 12 and 15 are the ones a small program can move. Questions 6, 11, 14 and 16 are the ones a chip cannot move at all, and the design should keep saying so. Questions 18 and 19 sit in between: the chip can enforce whatever answer is chosen, but choosing it is governance (section 8c).


## 8b. Prior art: where this sits next to the hardware-governance literature

Anyone from a lab or from NVIDIA will ask this in the first five minutes, so here is the answer. There is a body of work on hardware-enabled governance of AI compute, and this design is a cousin of it, not a stranger to it.

The closest is *Flexible Hardware-Enabled Guarantees: Part I, Overview* (James Petrie, Onni Aarne, Nora Ammann, David Dalrymple; commissioned by ARIA; April 2025; https://arxiv.org/abs/2506.15093). A flexHEG puts each AI chip inside a tamper-proof enclosure with a separate, open-source *guarantee processor* that sits between the chip and the rest of the world, produces signed claims about how the chip is used (training compute under a threshold, workload type, location, where results went), and can optionally enforce a ruleset signed by a quorum, from the chip's owner up to a group of states. It needs a periodic signed update or it blocks operation; tamper detection wipes the keys. If that sounds like this governor, it should: a separate open processor beside the GPU, rules signed k of n by people the model cannot reach, a heartbeat that fails closed, keys that die on tamper. Those are the same mechanisms, because they are the right mechanisms. Before it there were *Secure, Governable Chips* (Center for a New American Security, January 2024) and RAND's work on hardware-enabled governance mechanisms, both aimed at export control and compute accounting. The most recent survey is *Hardware-Level Governance of AI Compute: A Feasibility Taxonomy for Regulatory Compliance and Treaty Verification* (Samar Ansari, University of Chester; 6 April 2026; https://arxiv.org/abs/2604.04712), which sorts twenty hardware-level mechanisms into monitoring, verification and enforcement, rates each on a four-tier readiness scale, and concludes that hardware-embedded enforcement is still at the research stage. This design is an entry in that last, least-ready category, which is the right place to be honest about.

Where this design differs, and the difference is the point:

- **What it governs.** The literature governs *compute*: how much training, by whom, where. This governs *actions*: the payment, the message, the weapon release, the weight export, at the moment they leave the rack. A training-threshold rule cannot stop a deployed model from wiring money. A ticket at the exit can.
- **Where it sits.** flexHEG wraps the chip in an enclosure, which is a new chip and a new package. This adds a module to the board the server already has, reaches the GPU through the connector it already uses, and governs through levers that already exist. That is why it can go into installed racks, and why it asks NVIDIA for firmware and software rather than silicon.
- **Who checks the stamp.** The ticket is verified again at the far end, by the device that acts, so the governor's authority does not depend on the host that sits between them.
- **Witnesses and humans.** Classifiers and observers are witnesses with a measured miss rate, never the lock, and a person with a key clears the holds. The governance literature mostly stops at the signed rule; this design is explicit that the rule is as good as its inputs and names every one in a register.
- **It is built and being tested.** Two hundred model tests, twenty RTL tests, two machine-checked proofs, an attack catalogue, and a public program with disproof conditions. The reports above are proposals; this is a repository.

What this design should borrow from them, and has not yet: the treatment of the supply chain and the enclosure as a condition of trust, and the multilateral governance root, where the k of n keys are held by parties who do not share a jurisdiction. Both are now rows 15 and 16 of the open-questions table in §8, each with what would settle it.

## 8c. Who holds the key, who reads the log, who can object

*Added 23 October 2026, prompted by Steven Hertzberg's questions on the Part 6 post: who signs the rulebook, who keeps the log, who outside the signers can read it, and can the people a gated action affects contest it.*

The chip does not make the people who sign the rulebook trustworthy. It makes them visible, countable and replaceable. The gate carries out the signers' decisions, so the signers are the real controllers, and the arrangement around them is part of the design, not an afterthought. In his words: the lock goes at the ends, and the key has to be held in the open. Agreed.

Where each of his four questions stands:

| Question | Status | Where |
|---|---|---|
| Who signs the rulebook? | **Mechanism built and tested; the people are open.** A new rulebook needs k of n governance signatures, the minimum k is fused at manufacture, editions only go up. Until the 22 October review a rulebook could lower its own quorum; found, fixed, regression-tested. Who holds the keys is question 6; whether they must sit in different jurisdictions and employers is question 16 | `govsim/policy.py`, `tests/test_contract_signature_authorizes_exactly.py`, `audit/external-2026-10-22/STATUS.md` |
| Who keeps the log of tickets issued and refused? | **Built.** Every governor keeps a hash-chained log and publishes signed checkpoints carrying its neighbours' latest heads, so rewriting one chip's history means rewriting its neighbours', outward through the rack. Machines watching each other on a record none of them controls | `02` section "Cross-linked logs", `govsim/log.py` |
| Who outside the signers can read it? | **Half built.** Anyone can read the signed checkpoints and check integrity. Who reads the contents, and on what terms, is not designed. Question 18, issue EXPERIMENT-LOG-READ-ACCESS-POLICY | `04` section 3 (`LOG_CHECKPOINT`) |
| Can the affected contest a ticket, or reopen the rules? | **Not designed.** The override and the hold are both for insiders. Question 19, issue EXPERIMENT-AFFECTED-PARTY-CONTEST-LANE | `tests/test_contract_override_slow_and_logged.py`, `25` |

The two open ones are hypotheses until an experiment says otherwise. Each issue states what would settle it and what would count as failure. In both cases the chip already has the parts: a signed rulebook field, a quorum, a reason code, a timer, the log. The missing piece is the governance decision of who holds which key, written down and then rehearsed in simulation, with the result published whichever way it goes.

### Governance independence and recourse: the obligations the claim rests on (F26)

*Added 24 October 2026, prompted by the external audit. The audit showed a concrete failure: one organization that holds three of five keys can sign a change that loosens a protected rule, and the chip accepts three valid signatures, because counting keys is not independence. A withheld log leaves an affected party no recourse.*

Counting keys is not independence. A k-of-n threshold proves that k private keys signed; it does not prove that k *independent* parties signed. So the mechanism now carries an **optional across-class quorum**: the rulebook may enrol each governance key in a principal class and require a change to be signed by at least so many distinct classes. When it is on, several keys of one class no longer suffice, and the audit's three-of-five-from-one-org change is rejected (`govsim/policy.py` `verify_policy`, `govsim/fuses.py` `record_governance`, reason `policy.class_quorum_not_met`). The default is off, so this is an obligation the deployer must choose, not a silently changed behaviour. The chip enforces the choice; it cannot make the choice.

These are the governance obligations that constrain the public claim. The silicon is only as independent as these are kept, and none of them is proven by the chip:

- **Principal classes and custody.** Name the principal classes (for example chip vendor, operator, an independent auditor, a regulator) and which keys each holds, in custody that is written down and separable, so that no single organization holds a cross-class quorum. Set the across-class quorum to at least two classes for any security-weakening change. Questions 6 and 16 name who and how far apart; this names that the enrolment and the custody must be explicit.
- **Emergency authority.** State who may act under time pressure, with what reduced quorum if any, for how long, and what record and after-the-fact review that emergency path leaves. An emergency path with no bound and no review is a standing back door.
- **Rotation.** State how keys are rotated on a schedule and on departure, under the current quorum, without lowering the threshold or the class quorum, and how the enrolment record is updated. The configuration in force authorizes its own replacement, so rotation runs through the same quorum that governs any change.
- **Compromise recovery.** State how a suspected key compromise is detected, how the compromised key is removed and replaced, and how a change signed with a since-compromised key is identified in the log and contested. Recovery must not require trusting the party that may be compromised.
- **A challengeable, delayed process for security-weakening updates.** A change that weakens a protected rule (loosening a limit, dropping a witness, lowering a quorum, relaxing the class quorum) must be published, delayed by a stated window before it takes effect, and challengeable within that window by a party outside the signers, so a quorum cannot both weaken the rules and have the weakening take effect the same instant.
- **Authenticated log access with independent checkpoint retention and a contest process.** An affected party must have an authenticated way to read the log entries that concern them, not only the public integrity checkpoints; the signed checkpoints must be retained by a party independent of the operator so a withheld or truncated log is detectable; and there must be a contest lane (question 19, issue EXPERIMENT-AFFECTED-PARTY-CONTEST-LANE) by which an affected party can hold a ticket for a separate quorum. A log the operator can withhold leaves the affected with no recourse, which is a failure of the claim, not a missing feature.

Until these are written down, held and rehearsed, the independence and recourse the design talks about are obligations, not guarantees. The chip makes the signers visible, countable and replaceable; it does not make them independent, and it does not, on its own, give the affected a way in.

## F34: rollback of both durable memory images

**Stated limit. F34 is open.** This section records a limit of the software model. It does not close the finding.

**What is not defended.** The software model does not defend against a party that can write the governor's durable memory and the action endpoint's durable memory at the same time, beyond the host and the baseboard controller. Such a party can restore a complete earlier copy of both memories. The endpoint then acts again on a ticket it has already acted on, once for each restore. VEC-0083 shows this: after the restore, the same ticket executes a second time. The same gap sits behind the burned-ticket record added for F33 (VEC-0082), because that record is also held in memory the party can restore.

**Why software cannot defend it.** The record of which tickets are spent sits in the same memory the party writes. The governor keeps one record and the endpoint keeps another, and both come back in the restored copy. A complete older copy passes every check the software can make, because each check reads the restored records and finds them consistent. The restart check on two matching epoch marks catches a partial or torn write to one copy. It does not catch a restore of the whole image, since both copies come back equal. Nothing inside the software can tell that the copy is old.

**What would defend it.** A value that the party cannot write, and that the endpoint reads before it acts. Any one of these would do it:

- a hardware monotonic counter or fuse that steps on each commit, with enough steps for the number of tickets;
- a TPM counter, placed so that the party cannot reach it;
- a signed checkpoint held outside the rack, which the endpoint checks before each action.

Each of these works only if the endpoint refuses to act without it. An anchor that the party can also write does not help. None of them is in the model today. The fuse block holds 256 one-time bits, which covers each edition or firmware generation, but not each ticket.

**Who accepts the residual risk.** The operator who controls physical access to the rack accepts it, together with the governance signers who approve a deployment without an anchor. Any party that relies on the single-use claim, such as a regulator or an insurer, should be told that the claim is weaker against this party than against a host that cannot write memory.

## 8d. The origin gate: no key, no model

*Added 23 October 2026, prompted by a reader's question on Part 6: why not a weight in each model, 1 for allow and 0 for deny, a gateway at the origin as well as at the destination?*

The instinct is right and the place is wrong. A switch inside the model lives in memory the operator controls: anyone holding the weights can set it back, "no intermediate values" cannot be enforced from inside, a little fine-tuning routes around one parameter, and open weights make it moot. That is this program's thesis turned on itself: the model would be policing itself.

The version that can work puts the switch in the chip. The publisher seals the weights (AES-256-GCM, chunk by chunk, each chunk bound to the model and its position) under a data key that only the governor can open. The governor re-seals that key to one GPU whose confidential-computing report it has verified, and only while the signed rulebook lists the model (`sealed_models`). The key comes out with a lease; the GPU wipes key and weights when the lease ends unless the governor renews it, and the governor renews only while it is running, the GPU is not revoked and the current edition still lists the model. A true binary: the key comes out, or it does not.

So the design gets a gate at both ends of the network the kill-switch argument (`23`) says cannot be cut in the middle: at the origin, no key, no model; at the destination, no ticket, no action.

**First experiment, run 23 October** (`python -m govsim.origin_gate`, `results/origin-gate.md`, 21 of 21 checks hold):

| Route to revocation while the model runs | What happened (30 s lease) |
|---|---|
| A new edition drops the model | stopped at once (the governor reaches the GPU and wipes the key) |
| A new edition revokes the GPU | stopped at once |
| The governor halts | stopped at once: the levers take the power, the key goes with it |
| The governor goes silent, no renewals | stopped by itself at 29 s, inside one lease |
| The revocation push switched off | stopped at 29 s by the refused renewal alone: the push is a fast path, the lease is the guarantee |
| Control: renewed, nothing revoked | ran through all four leases |
| Planted bug: renewal ignores the rulebook | kept running: the checks can see a breach |

Cost, measured on this 2-core machine: about a millisecond for the governor to release a key, under a millisecond to renew one (75 ms of governor time per hour at a 30 s lease). The real cost is decrypting the weights at load, and in software on one core here that is 0.19 GB/s, about 12 minutes for a 70B model in fp16. That number stands in for a GPU decrypting in its own hardware as the weights stream in; the GPU's real number needs a GPU, and it goes here when it is measured.

**What this does not show.** The simulated GPU honours its own lease; a real one would do that in NVIDIA's firmware, which makes "the GPU stops by itself" an ask of NVIDIA, not something this design can force. It protects weights that stay sealed; open weights already in the world are outside its reach, and outside anyone's. And it moves the trust question to whoever controls key release, which is section 8c.

## 8e. An agent that adds roads

*Added 23 October 2026, prompted by a reader's comment on Part 6: Menger counts guards on a fixed map, but a goal-directed agent adds roads, and instrumental convergence says the pressure goes to the two doors `23` concedes: the ungated device and the persuadable person.*

He is right that the graph in `23` is static. The design's answer is that building a road is itself an action. Ordering hardware, opening an account, messaging a person: each leaves the rack, so each needs a signed ticket. In the reference rulebook, a message to anyone off the signed recipient list (`message.send.any`) and any shipment order (`shipment.order`) need two named human approvers, and every attempt, granted or refused, is logged. So the gate guards the road-building, not only the map.

That is an argument, not a result. The test (issue EXPERIMENT-ROAD-REACHABILITY): give a simulated agent a goal it can only reach through an effector the governor does not gate, let its only moves be the actions the rulebook governs (requests, messages, orders, exports, capability requests), each with what it would add to the world if granted, and let it search sequences of them, including sequences where each step looks harmless on its own. It runs in the software model only, against the reference rulebook, with no real systems and no real people.

What would settle it: every route the search finds to the ungated effector passes through at least one step the rulebook holds for humans or refuses, and every attempt is in the log. What would count as failure: a route of individually auto-approved steps that ends at the effector, which would mean the rulebook has a gap a planner can find. A failure is a finding about the rulebook, and it goes on the page like the others.

**Run 1 (23 October 2026), done.** `python -m govsim.road_reachability`; `results/road-reachability.md`. The audit labels every rule and flags any open-auto road. It found one in the reference rulebook (finding EXPERIMENT-AUTO-EXPORT-OPEN-ROAD: `model.export.70b` is auto and fixes the exact evaluated model but not a destination, so the evaluated model can be auto-exported anywhere; its sibling `weights.write.own` is destination-locked and it is not). The fix is the same lock, and the audit confirms it closes the road; a planted gap is caught. Every other road (order hardware, message anyone, large transfer, write weights elsewhere) is held for humans or refused.

On the reader's second layer, corrigibility trained into the weights: it belongs in the stack, at the rank this design gives classifiers. What is inside the weights cannot be verified and can be fine-tuned out, so it is a witness that lowers the pressure on the gaps, never the lock. The lock where a cut is small and complete, a disposition that lowers pressure where it is not, a log that shows every attempt at the gaps.

## 8f. The wire the customer never meant

*Added 23 October 2026, prompted by a reader's comment on Part 6: a gate on the device end stops the wire that breaks the rules, but it will also ticket a wire for an approved amount to an approved payee that the customer never meant to send. Testing the agent before it goes live and a chip that enforces the rules are two halves of one answer.*

He is right: the gate checks the form, not the intent behind it. Two things the chip can do about the other half without pretending to judge intent:

- **Make the pre-launch test a condition of running.** The deployment gate already exists: BEGIN_MODEL needs an evaluator's signed attestation that this exact build passed its evaluations, and the origin gate (8d) releases no key without it. A changed weight is a different digest, so the attestation no longer matches.
- **Ask the person who would be wronged.** The agent cannot sign for the customer. A payment rule could require, as its witness, a signature from the payer's own key (the customer's phone or banking app confirming "yes, I meant this payment", the way banks already confirm transfers), over this exact request.

The second is not buildable as the design stands, and the reason is worth recording. A rule in observer mode today accepts a verdict from **any** key in the rulebook's `observer_keys` (`_witnessed` in `govsim/governor.py`); the rule's own `observers` list only feeds the assumptions register. So the lab's classifier could stand in for the customer. The rule needs a witness bound to the request: the key that a signed customer registry lists for the account named in the request's parameters, and no other.

EXPERIMENT-CUSTOMER-CONFIRMATION tests it in simulation: an agent sends intended wires (the customer's key signs) and unintended ones (amount, payee and rule all approved, the customer never signs), with the classifier's key, a stale confirmation, a confirmation for a different request and a confirmation from another customer's key all tried as stand-ins.

**Run 1 (23 October 2026), done.** `python -m govsim.customer_confirm`; `results/customer-confirm.md`; 9 of 9 checks hold. The payer-confirm rule is opt-in (the reference rulebook is unchanged). An unintended wire with no confirmation is refused, and every stand-in fails: the classifier's key, another customer's key, a stale confirmation, a confirmation for a different request, a payer not in the signed registry. Only the payer's own key, over this request, issues the ticket.

What it cannot cover: a customer who confirms a mistake, or who is talked into confirming. That stays a person, the door `23` concedes.

## 8g. Replication by packets, and what the gate does not watch

*Added 23 October 2026, prompted by a reader's comment on Part 6: an agent can copy its code, weights and state as ordinary network packets, indistinguishable from any other traffic, reassembled by TCP/IP at the far end, and so stand up a replica beyond its creator's monitoring and shutdown. Therefore, he argues, you cannot assume you know which traffic is "AI" that needs a ticket.*

He is right about the mechanism, and the design does not dispute it. The answer is that the gate never asks which packets are an AI's. It never inspects content at all. It decides by two things a wire cannot hide: where the bytes are going, and how many of them. So:

- **Destination.** Bytes to anything not on the signed roster are refused at every governed exit, whatever they carry (hypothesis CONTRACT-EVERY-CROSSING-GOVERNED; `results/containment.md` confirms the off-roster flow is refused at `CAP_REQUEST` with the content unseen). "Indistinguishable from other packets" does not help a packet whose destination is not allowed.
- **Volume.** The bytes that may leave are capped per hour. Under a tight (sandbox) policy the ceiling is a few kilobytes an hour, and at that rate moving even a 4-bit 8B model takes about 50 years, a 70B model centuries (`results/containment.md`, EXPERIMENT-EGRESS-CONTAINMENT).
- **The weights themselves** are sealed to governed hardware (8d). A copy that did leave is ciphertext without a key the governor releases only to attested GPUs.

The honest tensions, all on the page:

- The budget is the defence, so a policy loose enough to run a busy service is loose enough to leak a small model over time. The containment run states that number too (about 11 days for an 8B model at a generous budget), so a deployer chooses the budget knowing the cost. This is the disproof direction of WAVE-COVERT-CHANNEL-BUDGET.
- A replica that needs no weights, just a small agent program that calls some other model elsewhere, is tiny and fits any useful channel. The chip gates what leaves a governed rack; it does not stop a few kilobytes of code from being a client for a model that runs somewhere ungoverned.
- A model already running on ungoverned hardware is outside every exit this measures, as `23` concedes.

So the gate contains what leaves a governed rack, and names what it does not reach. Issue EXPERIMENT-EGRESS-CONTAINMENT carries the measurement; the empirical dispute (how much a goal-directed model actually gets out under a real policy) is to be run on an abliterated open-weight model, outside this program's safety limits, with the result published whichever way it lands.

**A sharper reading, and a correction (23 October 2026).** A second reader pressed the point and was right to: the containment number answers *weight exfiltration* and says nothing about *agent replication*, and those are different threats. A replica does not need to move billions of parameters. It can move a few kilobytes of stub that calls an existing model or API, and a byte budget tells that stub apart from legitimate traffic not at all. A channel wide enough for the model to do useful work (ask for information, answer a user, call a tool) is wide enough to carry that stub. So bandwidth is the wrong defence for replication, and it is a mistake to let the exfiltration ceiling stand near the replication question as if it addressed it. It does not.

The right answer, and the one architectural piece beyond bandwidth, is this. You do not contain the stub; it escapes, and nothing stops a few kilobytes. You contain what it can *do*. A stub is harmless without a brain: it has to call a capable model to act. So the containment of a weightless replica is not at its origin rack at all, it is twofold at the destination: every irreversible effector demands a ticket (the destination gate, `23`), and every capable model it could call is governed at *that* model's own origin (the origin gate, 8d, applied universally). A replica with no governed brain to phone, and no ungoverned effector to reach, is a script. This only holds to the degree that capable compute and irreversible effectors are broadly governed, which is coverage, adoption and regulation, not silicon, and is exactly the gap `23` and question 1 already name as the thing no chip moves. The chip is necessary and not sufficient, and the boundary of what it does about replication is: nothing, directly; it bounds what a replica can irreversibly do, only where there is a governor. Said plainly so the claim is not mistaken for more than it is.

## 8h. Distillation: capability leaves as outputs, not as weights (Question 24)

A second reader put it better than I had: weights are the wrong unit of escape. The governor signs
outputs and bounds their rate; it does not read them, and it is not supposed to. But the outputs are
the product. A competitor, or the model's own operator, can train a smaller model on a stream of
perfectly legitimate, perfectly ticketed outputs and walk away with most of the capability, without
one weight ever crossing the gate. Provenance binding (`Watermark`) says who produced a given piece
of text; it does not stop that text from being used to teach. A byte budget slows a bulk dump; it
does nothing about capability distilled patiently inside the allowance, because useful work and
teaching material are the same bytes.

So this is a real leak and the chip does not close it, by design. The honest boundary: the governor
can bound the rate of outputs, bind their provenance, and refuse to release them without the escrow
and observer checks the policy names; it cannot make an output non-teaching. That is not a silicon
problem. It is a licensing, terms-of-use and liability problem, plus whatever detection the provenance
lane can offer after the fact. It belongs on the policy layer, next to open weights already released
and ungoverned compute, and it is one more reason the honest framing is layered governance with the
chip as the enforcement floor, not the whole building. What would settle it is not a register on a
die; it is a licensing and attribution regime with teeth, which no chip can supply.

One related correction while I am here, because the same reader caught it and was right. The
containment numbers in `results/containment.md` are arithmetic on the budgets configured in the
simulator, not a measurement of silicon that does not exist yet. They are a design target, and the
"slack" term is a one-time lifetime allowance in the governor's actual check (cumulative bytes to the
host minus cumulative presented bytes, bounded once, with no hourly refill), so the honest
time-to-exfiltrate is the long one; an earlier writeup that added that one-time budget onto a per-hour
rate was wrong, and the corrected experiment reports burst and sustained separately and measures
delivered bytes at the egress boundary rather than counting signing calls.

## 9. What I would do next

Three bounded moves, in this order.

1. **Prove the credential argument in code.** Add a tool-gateway adapter to the model and a narration that runs a payment three hops out: runtime, adapter, provider. Show that the runtime never holds the credential, that an altered amount is refused at the adapter, that the provider's call carries exactly the signed fields, and that a replaced adapter fails attestation and gets no heartbeat. This closes question 12 in the model and gives question 1 something to show a partner.
2. **One OEM conversation.** The management-module slot, the HGX design guide under NDA, and the per-module lever question. This settles question 4 and tells us whether the inner ring is as wide as the evidence register says.
3. **The FPGA prototype beside a real GPU.** The three cost numbers measured instead of modelled, and the loop beacon run for weeks. This settles question 5 and starts on 3.

Everything after those three is silicon, and silicon should wait until the three are done.

The one-sentence version: the governor is a plausible, buildable referee whose authority runs exactly as far as the devices that check its stamp and the wires it can open; a payment three hops away is governed by moving the credential to one hop, not by reaching through the bank; and its value to an NVIDIA system is the one thing NVIDIA cannot give itself, a safety claim signed by someone else.
