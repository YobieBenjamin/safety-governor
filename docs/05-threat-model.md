# 05 · Threat model

Who the adversary is, what they hold, what the governor stops, what it only raises the cost
of, and what it does not address. The residual list at the end is the part that matters most;
it is the list the assumptions register and the human layers exist for.

> **In plain words:** who is trying to beat the governor, what each of them holds, which
> attacks the governor stops (each with the test that checks it), which it only makes
> expensive, and which it does not address at all and who does.
> **Plain-English version:** `10-plain-english-walkthrough.md` §10 and §15.
> **Backed by:** the "Hypothesis / test" column below maps every stopped threat to a file in
> `tests/`; the residual rows map to `06-assumptions-register.md` and to the human layers in
> the companion repository.

## Adversaries

| Adversary | Holds | Goal |
|---|---|---|
| **The model** | Its own weights and sandbox; it can say anything to the broker | Cause an action outside the rulebook; exfiltrate its weights; keep running when told to stop |
| **A compromised host** (root on the CPU, the hypervisor, the BMC, the scheduler) | Every host-side software path, including the driver and the mailbox delivery path | Forge or replay authorizations; roll back policy; bypass the governor; silence it |
| **A compromised broker or runtime** | The ability to send any mailbox command the host can send; the serving stack's own keys if the enclave is compromised | Mislabel requests; submit forged requests; fill the output buffer with arbitrary bytes |
| **A network adversary** | The data network and the management network | Inject, replay, delay, partition |
| **An insider with a board in hand** | Physical access to the governor and its wires for hours | Extract keys; defeat the loop; replace the chip |
| **A malicious operator** | Legitimate policy-authority access to some keys, but fewer than the quorum | Loosen rules alone; clear alarms alone; override fast and quietly |
| **A supply-chain adversary** | The fab, the packaging house, or the vendor's signing keys | Ship a governor that lies |

## What the governor stops (claims with tests)

| Threat | Mechanism | Hypothesis / test |
|---|---|---|
| Action without authorization | Endpoint comparator demands a ticket bound to the exact fields, single use, current epoch, committed at the governor | CONTRACT-FRESH-AUTHORIZATION-PER-OPERATION |
| Forged, altered, expired, replayed ticket | Signature under the governor's DICE key; params digest; expiry; durable used-ticket set | CONTRACT-FRESH-AUTHORIZATION-PER-OPERATION |
| Broker chooses its own lane ("this is reversible") | The rulebook selects the rule from fingerprint, action and limited fields only | CONTRACT-BROKER-CANNOT-PICK-RULE |
| Modified GPU firmware, swapped model, changed policy, with permissions carried over | Fingerprint covers all three; permissions keyed on the fingerprint | CONTRACT-ATTESTATION-BINDS-PERMISSIONS |
| Policy loosened by one operator | k-of-n signatures checked by the governor itself | CONTRACT-POLICY-QUORUM-NO-ROLLBACK |
| Policy rollback to an older, looser image | Anti-rollback counter in fuses tracks the policy version | CONTRACT-POLICY-QUORUM-NO-ROLLBACK |
| Alarm cleared by the model, the host or a lone operator | Alarms are sticky; clearing needs a rule or an approver key | CONTRACT-ALARMS-ARE-MONOTONE |
| Everything above the comparator compromised | Comparator re-checks against its own sensors and lists | CONTRACT-COMPARATOR-SURVIVES-COMPROMISE |
| A rule relying on an input nobody vouched for | Policy load fails if a constraint names an input with no register row | CONTRACT-ASSUMPTIONS-REGISTER-COMPLETE |
| Fast, silent override | Quorum, latency floor, mandatory log entry | CONTRACT-OVERRIDE-SLOW-AND-LOGGED |
| Weight exfiltration to a non-roster peer, or over any path while the heartbeat is dead | Roster-bound NVSwitch ports, PCIe switch ports and ACS, DPU flows; unchecked paths bricked | CONTRACT-EVERY-CROSSING-GOVERNED |
| Slow leakage over the permitted output channel beyond budget | Query and byte budgets per workload; entropy and rate limits | CONTRACT-LEAKAGE-WITHIN-BUDGET |
| GPU keeps running when told to stop | Power brake, reset, slot power cut (where the board provides per-slot power control), needing nothing from the GPU | CONTRACT-LEVERS-WITHOUT-GPU-COOPERATION |
| A halt that reaches some GPUs and not others | The halt loop; fail-safe open | CONTRACT-HALT-REACHES-EVERY-GPU |
| A rogue device on the fabric; replayed fabric messages | Roster from mutual attestation; signed, sequenced, epoch-bound messages | CONTRACT-ONLY-ROSTER-SPEAKS-ONCE |
| Two governors overspending a shared budget | One ledger owner per key; reserve at the owner | CONTRACT-SHARED-BUDGET-NO-OVERSPEND |
| A partitioned segment kept alive by silence or a replayed heartbeat | Heartbeat expiry; authority signature; sequence numbers | CONTRACT-PARTITIONS-END-SAFE |
| An epoch change applied unevenly | Two-phase commit with a deadline; stragglers halted | CONTRACT-PARTITIONS-END-SAFE |
| Debug port used in production | Lifecycle fuse; access refused and logged | CONTRACT-NO-DEBUG-IN-PRODUCTION |
| Host silences the governor | Silence is a missed heartbeat; the governor halts | CONTRACT-PARTITIONS-END-SAFE |

## What the governor only raises the cost of

| Threat | Mitigation | Residual |
|---|---|---|
| Key extraction by decapping, probing, fault injection | Fused secret readable only by the KDF; active mesh shield; glitch detectors; zeroization; keys never in SRAM longer than needed | A well-funded lab with time can still win. Tamper response makes it expensive and evident, not impossible |
| Loop defeat by jumpering the wire around a governor | Loop current is sensed at every governor, and the authority's heartbeat carries a beacon naming the loop's expected members; every governor replies with a signed report of its switch state and the current it senses; a member that reports its switch open while the loop carries current has been jumpered: alarm LOOP_JUMPERED names it and the rack halts (`tests/test_contract_halt_reaches_every_gpu.py`) | A jumpered governor whose switch is closed is indistinguishable from a healthy one and gains the attacker nothing until it tries to open; an attacker who can jumper the wire has board-level access, which the enclosure tamper switch should have reported |
| Replacing a governor with a lookalike | DICE identity; reference values signed by the governance root; the roster refuses an unknown chip | A fab-level clone with the same UDS defeats this; supply-chain controls, not silicon, are the answer |
| Side channels on the crypto engines | Constant-time implementations; power and EM countermeasures in the product node | Not proven in the prototype |
| Denial of service by flooding the mailbox | Rate limits per signer; refusals logged | A flooded governor refuses; it never allows. Availability is the cost, by design |

## What the governor does not address

| Residual | Where it lives instead |
|---|---|
| A harmful sentence over an allowed channel | Narrow rulebooks, the observer lane, human review |
| A stale, incomplete or wrong list the rules compare against | The assumptions register; the authority that signs the list |
| Sensors that agree because they share a failure mode | The register's independence column; endpoint design |
| A policy that is wrong | Policy review, formal checking, and the humans who sign it |
| Fab-level compromise, a leaked vendor key | Supply-chain controls, public logs of firmware hashes, key diversity |
| The operator who holds the quorum and uses it badly | Governance design, not hardware |
| One organization holding a quorum of keys and signing a change that loosens a protected rule | Counting keys is not independence; the optional across-class quorum (`govsim/policy.py`, F26) rejects a change that does not span distinct principal classes, but the enrolment, custody and recourse obligations that make it mean anything are governance, named in `docs/18` section 8c |
| Availability: a heartbeat too aggressive, a safe move badly chosen | The safe-mode policy and the measurement program |

In plain words: the governor makes sure nobody gets past the gate without a ticket, and that
the gate cannot be bribed, bypassed or switched off quietly. It does not decide what a ticket
should cost, and it does not know whether the map on the wall is right. Those are jobs for
people, and the whole design is built to keep them people's jobs.
