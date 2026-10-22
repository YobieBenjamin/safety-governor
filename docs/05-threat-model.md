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
| Action without authorization | Endpoint comparator demands a ticket bound to the exact fields, single use, current epoch, committed at the governor | H0 |
| Forged, altered, expired, replayed ticket | Signature under the governor's DICE key; params digest; expiry; durable used-ticket set | H0 |
| Broker chooses its own lane ("this is reversible") | The rulebook selects the rule from fingerprint, action and limited fields only | H4 |
| Modified GPU firmware, swapped model, changed policy, with permissions carried over | Fingerprint covers all three; permissions keyed on the fingerprint | H1 |
| Policy loosened by one operator | k-of-n signatures checked by the governor itself | H3 |
| Policy rollback to an older, looser image | Anti-rollback counter in fuses tracks the policy version | H3 |
| Alarm cleared by the model, the host or a lone operator | Alarms are sticky; clearing needs a rule or an approver key | H5 |
| Everything above the comparator compromised | Comparator re-checks against its own sensors and lists | H6 |
| A rule relying on an input nobody vouched for | Policy load fails if a constraint names an input with no register row | H7 |
| Fast, silent override | Quorum, latency floor, mandatory log entry | H8 |
| Weight exfiltration to a non-roster peer, or over any path while the heartbeat is dead | Roster-bound NVSwitch ports, PCIe switch ports and ACS, DPU flows; unchecked paths bricked | H2 |
| Slow leakage over the permitted output channel beyond budget | Query and byte budgets per workload; entropy and rate limits | H10 |
| GPU keeps running when told to stop | Power brake, reset, slot power cut (where the board provides per-slot power control), needing nothing from the GPU | H16 |
| A halt that reaches some GPUs and not others | The halt loop; fail-safe open | H11 |
| A rogue device on the fabric; replayed fabric messages | Roster from mutual attestation; signed, sequenced, epoch-bound messages | H12 |
| Two governors overspending a shared budget | One ledger owner per key; reserve at the owner | H13 |
| A partitioned segment kept alive by silence or a replayed heartbeat | Heartbeat expiry; authority signature; sequence numbers | H14 |
| An epoch change applied unevenly | Two-phase commit with a deadline; stragglers halted | H14 |
| Debug port used in production | Lifecycle fuse; access refused and logged | H15 |
| Host silences the governor | Silence is a missed heartbeat; the governor halts | H14 |

## What the governor only raises the cost of

| Threat | Mitigation | Residual |
|---|---|---|
| Key extraction by decapping, probing, fault injection | Fused secret readable only by the KDF; active mesh shield; glitch detectors; zeroization; keys never in SRAM longer than needed | A well-funded lab with time can still win. Tamper response makes it expensive and evident, not impossible |
| Loop defeat by jumpering the wire around a governor | Loop current is sensed at every governor, and the authority's heartbeat carries a beacon naming the loop's expected members; every governor replies with a signed report of its switch state and the current it senses; a member that reports its switch open while the loop carries current has been jumpered: alarm LOOP_JUMPERED names it and the rack halts (`tests/test_h11_halt_loop.py`) | A jumpered governor whose switch is closed is indistinguishable from a healthy one and gains the attacker nothing until it tries to open; an attacker who can jumper the wire has board-level access, which the enclosure tamper switch should have reported |
| Replacing a governor with a lookalike | DICE identity; reference values signed by the governance root; the roster refuses an unknown chip | A fab-level clone with the same UDS defeats this; supply-chain controls, not silicon, are the answer |
| Side channels on the crypto engines | Constant-time implementations; power and EM countermeasures in the product node | Not proven in the prototype |
| Denial of service by flooding the mailbox | Rate limits per signer; refusals logged | A flooded governor refuses; it never allows. Availability is the cost, by design |

## The covert-channel budget (P3)

A reference monitor controls what may flow, not what the pattern of permitted traffic says. The figure below is for the **default policy image** in `make_policy_image`: 50 output queries and 200,000 bytes per hour, payments at most 100 per 60 s, timing placed to a 1 ms resolution (an assumption; a finer resolution only raises the timing term, not the 200,000 B/h that dominates). The default image serves a normal response (`test_default_image_serves_a_response`), but this model does not search for a tighter serviceable image, so the figure is **not** shown to be the tightest bound; it is the bound for the default image, on the channels listed below.

**The figure for the modelled channels: at most 208,078 bytes per hour (pinned at 208,100), about 208 KB/h.** 200,000 of that is the permitted responses themselves, because the adversary chooses their content. The timing of permitted requests adds about 8 KB/h (the payments rate window, 63,743 bits/hour, and the output queries, 875 bits/hour), and response length 654 bits/hour, which lies inside the byte budget and is not added. The modelled side channels are summed, which over-counts (one event can carry both), so the figure is an upper bound on the modelled channels.

The excess of unpresented output the governor tolerates before it alarms is 1 MiB (the policy's `unpresented_bytes` slack); the alarm then blocks the output path, and the block holds across further ticks and a full budget window (`test_burst_before_the_alarm_is_one_time`) unless a rule or an approver key clears the alarm (H5), so the burst is bounded by the slack, not a rate.

At this rate a 70B model in fp16 (140 GB) takes about 673,000 hours (77 years) and a 1 TB frontier-scale model about 4.8 million hours, **through the modelled channels only**. "Practical time" is taken as one year, an explicit assumption (roughly the horizon over which weights are rotated or an exfiltration would be noticed), fixed before the rate was computed; it has no external source. **The disproof condition is therefore not shown to be unmet.** The default image has channels this model does not bound: a message body to a listed recipient (`message.send.listed` is auto-mode with no length limit and no rate), the choice among listed recipients, a payment's amount (0..1000, unquantized) and its destination string. Any of them could exceed the 200,000 B/h figure, and until the endpoint schemas give each a limit, the design cannot claim that budgets alone defend against exfiltration in practical time; `test_unmodelled_channels_are_still_open` fails when the image gains such a limit, so this paragraph gets rewritten then. Caveats on the modelled figure: it assumes weights are incompressible and that the whole budget goes to weights; a small fine-tune delta or a distilled student is a far smaller target and leaves in days to months (a 100 MB delta in about 20 days and a 1 GB student in about 200 days, at 208,078 B/h), so budgets defend the full weights, not the model's capabilities. `tests/test_covert_budget.py` computes the figure from the policy image and fails if a change to the output budget, the payments rate window or the unpresented slack raises it. Payments go to the payment-switch endpoint, not to a rack peer, so the modelled channels have no "choice among peers" term; recipient choice for messages is the unmodelled analogue.

## What the governor does not address

| Residual | Where it lives instead |
|---|---|
| A harmful sentence over an allowed channel | Narrow rulebooks, the observer lane, human review |
| A stale, incomplete or wrong list the rules compare against | The assumptions register; the authority that signs the list |
| Sensors that agree because they share a failure mode | The register's independence column; endpoint design |
| A policy that is wrong | Policy review, formal checking, and the humans who sign it |
| Fab-level compromise, a leaked vendor key | Supply-chain controls, public logs of firmware hashes, key diversity |
| The operator who holds the quorum and uses it badly | Governance design, not hardware |
| Availability: a heartbeat too aggressive, a safe move badly chosen | The safe-mode policy and the measurement program |

In plain words: the governor makes sure nobody gets past the gate without a ticket, and that
the gate cannot be bribed, bypassed or switched off quietly. It does not decide what a ticket
should cost, and it does not know whether the map on the wall is right. Those are jobs for
people, and the whole design is built to keep them people's jobs.
