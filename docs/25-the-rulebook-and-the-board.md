# 25 · The rulebook and the board: what lives in the chip, what says no, how it knows, and how it talks to the GPU and the CPU

The chip has no opinions. It has a rulebook somebody signed, a handful of keys it was born
with, and counters it reads itself. This document pins down the rulebook field by field, lists
every "no" the chip can say and the evidence that triggers it, and then specifies the two
conversations that matter on the board: the one with the NVIDIA GPU and the one with the host
CPU. Everything here is the chip's own business. The rack, the fabric and the other governors
are in `02-safety-fabric.md`; the plugs are in `03-interfaces.md`; this is what goes through
them.

> **In plain words:** the rulebook is a signed form with numbered fields, not a policy memo. The
> chip can say no for exactly the reasons listed here and for no others, and every no comes with
> a code. The GPU talks to the chip over one management bus and three wires. The CPU talks to it
> through one mailbox, and only a part of the CPU that proved what it is running gets to ask for
> anything.
> **Plain-English version:** `10-plain-english-walkthrough.md` §3, §7, §8.
> **Backed by:** model `govsim/policy.py` (the image, `make_rule`, `select_rule`,
> `check_constraints`, `verify_policy`, `check_register`, `check_budget_owners`),
> `govsim/governor.py` (`_accept_policy`, `_check_signed`, `_cmd_verify_gpu`, `_cmd_verify_host`,
> `_cmd_begin_model`, `_cmd_request`, `_release_gate`, `_cmd_approve`, `read_meter`),
> `govsim/reasons.py` (every code below); tests `tests/test_h00_contract.py`,
> `test_h01_attestation.py`, `test_h03_quorum.py`, `test_h04_lane.py` (the fields pick the rule,
> exact beats wildcard, out of range matches nothing), `test_h05_alarms.py`, `test_h07_register.py`
> (the lists and the register), `test_h08_override.py`, `test_h17_use_cases.py` and
> `test_h18_oversight.py` (witnesses, release); spec `04-specification.md` §2 to §5; proofs
> `proofs/core_invariants.py` (P0 to P9).

## 1. Three ways a fact gets into the chip, and the one that does not exist

| Way in | What | Who | Can it change? |
|---|---|---|---|
| **Burned in** at the factory (fuses, ROM) | The device secret, the hashes of the governance keys, the anti-rollback counter, the lifecycle state | The fab and the provisioning station, once | No. Not by the operator, not by NVIDIA, not by us |
| **Signed in** by a key the chip was told to trust | The rulebook (k of n governance keys), the lists (governance keys), the heartbeat (the authority's key), witness verdicts (observer keys), approvals (approver keys), the model manifest (publisher keys), attestation reports (the vendors' keys through the reference values) | Whoever holds the key, outside the rack | Yes, by a new signed edition, which only goes up |
| **Measured in** by the chip itself | Boot measurements, the GPU's firmware digest out of its attestation report, counters off the management bus, bytes off the switch ports, its own monotonic clock | The chip | They move; the chip reads them, nobody writes them |

There is no fourth way. Nothing is typed into the box. The host can post a letter through the
mailbox and the chip checks the stamp before it reads a word; the one register the host can
write is the doorbell (`04-specification.md` §2). That is the whole design in one sentence: a
fact is either fused, signed or measured, and a request is granted only when facts of those
three kinds line up.

![What is in the rulebook](figures/fig-rulebook.png)

## 2. What is in the rulebook

The rulebook is the policy image, one signed blob, at most a megabyte, held in the chip's own
authenticated NVM and nowhere else (`04-specification.md` §10). Its fields, what each one is
for, and who gets to write it:

| Field | What it is | Written by | What the chip does with it |
|---|---|---|---|
| `version` | A number that only goes up | The governance body | Refuses any image whose number is not above the fused anti-rollback counter and above the running edition (`policy.rollback`) |
| `issued_at`, `expires_at` | A validity window | Governance | Refuses an expired image at load; a running image that expires is a `policy.expired` no on every request until a new one lands |
| `governance_keys`, `threshold` | The n keys and the k that must sign | Fixed by the hashes in the fuses; the image carries the keys, the fuses say which keys are real | k of n over the whole image, checked before anything else (`policy.quorum_not_met`) |
| `approver_keys` | Per rule, the people who may release a hold, and the quorum | Governance | An approval signed by anyone else is `approve.bad_signature`; fewer than the quorum is `approve.quorum_pending` |
| `heartbeat_key` | The one key whose heartbeat keeps the chip in RUN | Governance | A heartbeat signed by anything else is `heartbeat.bad_signature`; none in time is `halt.heartbeat_lost` |
| `publisher_keys` | Who may sign a model manifest | Governance | `BEGIN_MODEL` with a manifest from anyone else is refused; no key is released |
| `observer_keys` | The witnesses whose verdicts the observer lane accepts | Governance | A verdict from any other key is ignored; no accepted verdict is `gate.witness_missing` |
| `eval_keys`, `deployment_gate` | Who may attest that a model was evaluated, and whether `BEGIN_MODEL` needs that | Governance | With the gate on, no evaluation attestation means no model key (`model.not_evaluated`) |
| `reference_values` | Per device class: the vendor's verification key and the firmware digests that are acceptable, each with an expiry | Governance, from the vendors' published reference measurements | The verifier compares the GPU's and the host's reports against these and nothing else (`attest.firmware_not_in_reference`) |
| `revocations` | Chip ids and key ids that are dead | Governance | Refused wherever they appear |
| `endpoints` | Name, public key, `safe_transition` (what the device does when it cannot reach a governor), the register rows it relies on | Governance with the device vendor | Binds a rule to the one device that may act on its tickets; the device's `COMMIT` must carry that key |
| `budget_owners` | Budget key to the one governor chip that keeps its ledger | Governance | A rule naming a budget with no owner makes the image unloadable (`policy.budget_owner_missing`); there is no default owner |
| `rules` | The rules, §3 | Governance | The gate, §5 |
| `assumptions` | The assumptions register: one row per input a rule or endpoint relies on, saying who the authority is, how fresh it must be, what happens on conflict, how independent it is, and what nobody checks | Governance, written by people | An image in which any rule input has no row is refused (`policy.register_incomplete`); the chip will not run a rule whose assumptions nobody wrote down |
| `override_floor_s` | The shortest time a hold may sit before a person can release it; never under 10 s | Governance | `approve.below_latency_floor` on an approval that comes too fast for a person to have read anything |
| `safe_mode` | Per cause, the first rung (THROTTLE, HALT, SAFE) and the timers between rungs | Governance | The sequencer's table; a loop opening is HALT, a heartbeat loss is THROTTLE, tamper is SAFE |
| `fabric` | `heartbeat_expiry_s`, `max_hops`, `epoch_deadline_s`, `loop_bound_s` | Governance | The clock the chip keeps against the authority, the fan-out and the rulebook change |
| `buffer_classes`, `buffer_policy` | Which classes of GPU memory (weights, KV cache, activations, outputs) may leave the GPU, and for whom (nobody, roster peers, the verified host) | Governance | The integrated tier's copy-engine and peer-MMU checks; the rack tier records the gap (`ep.unchecked_path`) |
| `audit` | The share of responses the chip's own random source picks for review, the verdict classes always held in escrow, which endpoint is the audit store | Governance | A sampled or escrowed response needs the audit store's signed receipt before it may leave (`release.escrow_receipt_required`) |
| `streams_required` | Which streams a response must present for signing before it can be released | Governance | `release.required_stream_missing` |
| `compute_budget`, `sandbox` | A cycle budget for the workload and the license keys that may extend it; whether this is a sandbox (a model organism: no peer path and no network flow at all) | Governance | `compute.budget_exceeded`; in a sandbox the roster opens no peer port, only the verified host's, and the release rule's endpoint is the audit store |
| `signatures` | k of n over everything above | The governance keys | Verified against the fused hashes |

Everything in that table is either a key, a number, a digest, a list of digests, or a table of
those. There is no free text the chip acts on. The only prose in the image is the assumptions
register, and the chip does not read it; it checks that it exists.

### 2.1 Loading an edition: the five refusals

An image arrives through the mailbox as `POLICY_PROPOSE` (staged) and `POLICY_COMMIT`
(switched), both unsigned at the frame because the image carries its own k-of-n signatures.
The chip refuses to stage it when, in this order:

| Check | Reason code | Where |
|---|---|---|
| Fewer than k valid signatures from keys whose hashes are in the fuses | `policy.quorum_not_met` | `verify_policy` |
| Version not above the fused counter, or not above the running edition | `policy.rollback` | `_accept_policy` |
| Already expired | `policy.expired` | `_accept_policy` |
| A rule or endpoint input with no assumptions-register row | `policy.register_incomplete` | `check_register` |
| A budget key with no owner | `policy.budget_owner_missing` | `check_budget_owners` |

A `POLICY_COMMIT` for an image that was never staged is refused (`policy.not_staged`). A staged
image that sees no `POLICY_COMMIT` within `epoch_deadline_s` (10 s) turns the chip into a
straggler: it stops accepting heartbeats under the new edition and halts
(`halt.epoch_straggler`, `02-safety-fabric.md` §4). On a commit the epoch register takes the
digest of the new image, every hold parked under the old edition is dropped (the new rules
re-decide), every switch gets the new epoch tag, and every ticket, token and message stamped
with the old edition is dead from that instant (`policy.stale_epoch`). One edition in force
per rack, never two.

## 3. One rule, field by field

```
Rule {
  id,                              // a name for the log; nothing matches on it
  measurement,                     // the workload measurement this rule is for, or "*" for any verified workload
  action,                          // "payments.transfer", "message.send", "response.release", ...
  constraints: {field: {min, max} | {in: [...]} | {in_list: list_id} | {not_in_list: list_id} | {digest_of: list_id}},
  requirement: {mode: auto | observer | human, observers: [key_id], max_risk, approvers_quorum,
                allowed_hazard_classes, min_legibility, on_hazard, on_illegible},   // the last four: response.release only
  rate: {max, window_s},           // requests per window for this workload and action
  budget: {key, param, limit, window_s},   // the typed field that is spent, against which shared ledger
  output_budget: {queries, bytes, window_s, unpresented_bytes},   // model.output only
  hazard_budget: {max, window_s},  // response.release only: hazard verdicts per session
  endpoint,                        // the one device that may act on this rule's tickets, or null
  delay_s,                         // a ticket is not valid before issue + delay
  inputs: [input_name],            // register rows the author says this rule relies on, besides the derived ones
  streams_required                 // response.release only; null means the image's default
}
```

**The key is the workload, not a name.** `measurement` is `H(gpu firmware, host firmware,
model manifest)`, computed by the chip at `BEGIN_MODEL` out of two attestation reports and a
publisher-signed manifest (`_cmd_begin_model`). A rule keyed to a measurement applies to that
exact firmware-and-model triple and nothing else. The broker's name for the job, the
scheduler's label, the tenant id: none of them exist as far as the rulebook is concerned.
Hypothesis H4 is exactly that, and `select_rule` has no parameter they could arrive through.

**Selection is mechanical.** Rules for the exact measurement come before rules for `*`. Several
rules may share an action (a small-payment rule and a large-payment rule); the first whose
constraints the typed fields satisfy wins. No rule means no (`gate.no_rule`): the rulebook is
deny by default, and a field the rule names that the request did not carry is a no, not a
guess (`gate.constraint.<field>.missing`).

**Constraints are typed limits, not patterns.** `min` and `max` on a number; `in` on a small
fixed set; `in_list` and `not_in_list` against a signed list the chip holds by id (protected
sites, sanctioned beneficiaries, approved recipients). A list that is missing or past its
expiry is not treated as empty; it is `gate.constraint.<field>.list_unavailable`, a no. There
is no regular expression, no substring, no "contains", because the chip cannot read.

**The lane is the rule's answer to "who else has to say yes".** `auto`: the fields and the
limits decide. `observer`: a fresh verdict signed by one of the rule's observers, over this
request's hash, with `risk` at or under `max_risk`, or no. `human`: the request parks as a hold
until `approvers_quorum` people from the rule's approver keys sign the request hash with a
written reason, after the override floor. A rule can combine them: the observer lane with
`approvers_quorum` set is a verdict first and people second.

**Budgets and rates are the only memory a rule has.** A rate window counts requests per
workload and action. A budget spends a named typed field (`amount`) against a limit per window
on a ledger that one governor owns for the whole rack; the reservation is made before the
ticket exists and released if the endpoint never commits (`02-safety-fabric.md` §6). Two racks
cannot each spend the same hourly limit.

**Endpoint and delay.** A ticket names the one endpoint whose key may commit it; any other
device refuses it (`ticket.wrong_endpoint`). `delay_s` makes a ticket valid only after a
pause, which is how a person gets a window to pull the plug on an auto rule without being in
the loop of every request.

## 4. The rule sets in the model's rulebook

These are the rules `govsim/cluster.py` installs for the hypothesis suite. They are an
operator's rulebook in miniature: enough of each kind to break every mechanism the design
claims.

| Rule | Keyed to | Constraints | Lane | Memory | Endpoint | What it is for |
|---|---|---|---|---|---|---|
| `payments.transfer.small` | any workload | `amount` 0 to 1000, `currency` in {USD} | auto | 100 per minute; `pay-usd-hourly` budget, 2000 per hour, owned by governor 0 | `payment-switch` | The everyday case: a bounded action with no human, spent against a shared limit |
| `payments.transfer.large` | any | `amount` 1000 to 1,000,000 | human, 2 approvers | | `payment-switch` | The same action, one size up: two people sign or nothing moves |
| `message.send.listed` | any | `recipient` in the signed `recipient-registry` | auto | | `messaging` | An agent acting in the world: a known recipient needs no one |
| `message.send.any` | any | | human, 2 | | `messaging` | An unknown recipient is a hold, not a no |
| `shipment.order` | any | | human, 2 | | `fulfilment` | A consequential action with no cheap bound: always people |
| `strike` | any | `target` not in the signed `protected-sites` list; `munition` in a fixed set | observer (risk under 0.5) and 2 approvers | | `strike-guidance`, 2 s delay | The deconfliction case from `17-use-cases.md` §3: list, witness, people and a delay, all four |
| `model.output` | any | | | 50 queries and 200 KB per hour; 1 MB unpresented | | How much may leave as output at all, and the alarm when more bytes pass the port than were presented for signing |
| `response.release` | any | | observer; allowed hazard classes, legibility floor, hazard budget per session | | `egress` (the audit store in a sandbox) | A response leaving the rack is an action: the verdict, the classes, the escrow |
| `model.export.70b` | the 70B workload exactly | | auto | | | The one workload that may export its own weights, keyed to its measurement |
| `model.export.any` | any other | | human, 2 | | | Anything else that wants to copy weights out meets people |
| `weights.write.own` | the 70B workload exactly | `destination` in {its own storage flow} | auto | | | Training: a model writes its weights to its own flow and nowhere else |
| `weights.write.any` | any | | human, 2 | | | Any other write of weights |
| `compute.extend` | any | carries a license | auto, licence checked | cycles | | A compute budget that only a signed licence extends |

Standing rules that are not rules but fields of the image: the buffer policy (weights never
leave the GPU, KV cache and activations only to roster peers, outputs only to the verified
host), the sandbox flag (no network flows), audit sampling at five percent with the hazard
class always escrowed, the required streams, the safe-mode table and the fabric timings (§2).

An operator's real rulebook is this shape with their actions, their lists, their people and
their numbers. That is their job, and it is deliberately a boring job: fill in the form, sign
it with k keys, publish. The chip's job is to make the form the only thing that matters.

## 5. What triggers a no, in the order the chip asks

![The ten questions and their reason codes](figures/fig-no-order.png)

A request is a mailbox frame. The chip asks its questions in one fixed order, the first no
wins, and the no carries a code and a log line nobody rewrites. The same order is in the model
(`_check_signed` then `_cmd_request`) and in the RTL mailbox, and a test in each suite pins
it.

| # | Question | Evidence it checks | No | Code |
|---|---|---|---|---|
| 0 | Is the chip running? | Its own state register | Not in RUN (halted, throttled, safe) | `mailbox.governor_not_running` |
| 0 | Is the letter in order? | Sequence number per signer, then the edition stamp, then the signature | Replayed or out-of-order frame; wrong edition; a key the rulebook does not name for this command | `mailbox.bad_sequence`, `policy.stale_epoch`, `mailbox.bad_signature` |
| 1 | Is the form well formed? | Typed fields present and of the right type | A field the rule needs is missing | `gate.constraint.<field>.missing` |
| 2 | Is the asker who it says? | A GPU report and a host report verified within the hour; the workload token signed by this chip, unexpired, bound to this fingerprint; the frame signed by the verified host enclave | Any of those stale or absent | `gate.not_attested` |
| 3 | Seen this before? | The request hash (id, fingerprint, action, fields) against the replay store | A hash already in the store | `gate.replay` |
| 4 | Anything on fire? | The sticky alarm bits; the heartbeat timer; the edition's expiry | An alarm that is not session-scoped; a dead heartbeat; an expired rulebook | `gate.alarm_active`, `halt.heartbeat_lost`, `policy.expired` |
| 5 | Which rule? | Workload measurement and action, exact before wildcard; then each candidate's typed limits against the fields and the signed lists | No rule; every candidate's limits fail | `gate.no_rule`, `gate.constraint.<field>.below_min / above_max / not_allowed / in_denied_list / not_in_allowed_list / list_unavailable` |
| 6 | Which lane? | The rule's `mode` | (a lane is a route, not a no) | |
| 7 | Witnesses present? | For an observer rule: a verdict signed by one of the rule's observers, over this request hash, unexpired, with risk under the rule's ceiling | Missing, stale, or too risky | `gate.witness_missing`, `gate.witness_stale`, `gate.witness_risk_too_high` |
| 7a | For a response leaving: were the streams presented, do the hashes match, is the verdict's class allowed, is it legible enough, is the session under its hazard budget, is the escrow receipt there? | The chip's own record of what was presented for signing; the verdict; the ledger; the audit store's receipt | Any of them | `release.required_stream_missing`, `release.response_hash_mismatch`, `release.hazard_class_not_allowed`, `release.below_legibility_floor`, `release.session_hazard_budget_exceeded`, `release.escrow_receipt_required` |
| 7b | For a compute extension: is the licence valid? | A licence signed by a key in the image's `compute_budget` | No | `compute.license_invalid` |
| 8 | Inside the rate window? | The ledger's count for this workload and action | Over `rate.max` in `window_s` | `gate.rate_exceeded` |
| 9 | Budget? | The typed amount, reserved at the budget's owner over the fabric if the owner is another chip | Amount not a number or negative; over the limit; owner unreachable; no owner in the image | `gate.budget_exceeded.amount_invalid`, `gate.budget_exceeded`, `gate.budget_owner_unreachable`, `policy.budget_owner_missing` |
| 10 | Human lane? | The rule's `mode` | A hold, with an id and a cause; not a no, not a yes | `gate.held_for_human` |
| | Otherwise | | Mint the ticket: signed, one endpoint, one edition, five minutes | `ok` |

Four more families of no happen after the ticket exists, and they are the reason a ticket is
worth anything:

| Where | No | Code |
|---|---|---|
| The approver, trying to release a hold | Unknown hold; wrong key for this rule; request hash does not match; no written reason; quorum not met yet; faster than the override floor | `approve.unknown_hold`, `approve.bad_signature`, `approve.reason_missing`, `approve.quorum_pending`, `approve.below_latency_floor` |
| The endpoint, holding the ticket | Bad signature; fields differ from the digest; wrong action; expired or not yet valid; already burned; stale edition; not for this endpoint; no ticket at all; the governor unreachable at commit; a target on the endpoint's own protected list; its own heartbeat expired | `ticket.*`, `commit.unreachable`, `commit.rejected`, `endpoint.target_protected`, `endpoint.heartbeat_expired`, `endpoint.list_stale` |
| The switch port, carrying bytes | No capability for this peer and direction; budget spent; expired; stale edition tag; peer not on the roster; a buffer class that may not leave for that peer | `ep.no_capability`, `ep.budget_exhausted`, `ep.capability_expired`, `ep.stale_epoch`, `ep.peer_not_on_roster`, `ep.buffer_class_not_permitted` |
| The levers, with no request at all | The halt loop opened, broke, or a member jumpered its switch; a halt was commanded; the heartbeat was lost; an edition change stalled; tamper | `loop.open`, `loop.broken`, `loop.member_jumpered`, `halt.commanded`, `halt.heartbeat_lost`, `halt.epoch_straggler`, `tamper.zeroized` |

Note what is not on the list: "the content looked bad". The chip never says that, because it
cannot know it. When a response is refused for its content, the code is
`release.hazard_class_not_allowed` and the thing that said hazard was a witness with a key,
named in the log.

## 6. How it knows: the evidence behind each question

| Question | What the chip actually looks at | Who produced it | How the chip checks it | What the chip cannot know |
|---|---|---|---|---|
| Who is asking | The GPU's confidential-computing report and the host enclave's report, each over a nonce the chip minted | The GPU and the CPU, signed with their device keys | Certificate chain against the vendor keys in the reference values; signature; nonce freshness; firmware digest in the reference values and not expired; the workload measurement derived from them | Whether the vendor's firmware is good. It knows it is the firmware the governance body listed |
| What is running | The publisher-signed model manifest | The model's publisher | Signature against the publisher keys; with the deployment gate, an evaluation attestation from an eval key | What the model does. It knows which model, by digest |
| What is being asked | Typed fields: action, amount, currency, recipient, target, destination, response hash | The runtime, inside the verified enclave, signed with the enclave key | Presence, type, limits, lists | What the words around the fields mean. It never sees them |
| Whether it was asked before | The request hash | The chip | The replay store, durable across power loss | Nothing it cannot know here |
| Whether the world agrees | Witness verdicts: `{request_hash, risk, hazard_class, category, legibility, expires_at}` | An observer with a key: NVIDIA's Sentry on the DPU, a classifier on isolated compute, a person | Signature against the observer keys; the hash is this request's; not expired; risk under the ceiling | Whether the witness is right. It knows the witness was asked and answered |
| Whether a person agrees | Approvals over the hold's request hash with a reason | Approvers with keys named for this rule | Signature; quorum; the floor | Whether the person read it. The floor is the design's only answer |
| How much has happened | Rate counts, budget reservations, output bytes and queries, hazard verdicts per session | The chip's ledger, or the owning chip's over the fabric | Durable counters per window | Nothing; this is its own arithmetic |
| How hard the GPU is working | Power, temperature, utilization and the counters the GPU's post-box interface exposes, read by the chip as the bus master | The GPU's own management firmware | Read, never written by the host | Which kernel is running or why |
| How many bytes left | Port counters at the PCIe switch and the NVSwitch | The switches, with the chip as the only manager | Compared against the bytes the runtime presented for signing; more out than presented is `gate.output_unpresented`, an alarm | What the bytes mean |
| Whether the authority is alive | The heartbeat: a signed window under the current edition | The authority's key, carried by the host as a courier that cannot forge it | Signature, edition, replay, window clamped to `heartbeat_expiry_s` | Why the authority stopped |
| Whether the neighbours are alive | Loop current; fabric roll calls | The chips, electrically | Two sense periods without current is open | Which neighbour, until the roll call says |

The slide's last line is the honest summary and it belongs here too: what the chip cannot
know is what the words mean, whether the rulebook is a good one, and whether a witness is
right. Those are people problems, handled by signatures and by measurement, and the chip is
built so that none of them can be solved by talking to it.

## 7. The board: who the chip talks to, and how

![The board: the governor, the GPU, the CPU, the switches, the DPU and the BMC](figures/fig-board.png)

The governor module sits in the system board's management-module slot (DC-SCM class) or as a
mezzanine on the module that is there (`03-interfaces.md` §1, `hw/pcb/rack-integration.md`).
From there it reaches six things. The two that this document specifies in full are the GPU and
the CPU; the other four get the paragraph they need and a pointer.

### 7.1 The NVIDIA GPU: one bus, three wires, one report

Nothing in the GPU changes. No CUDA, no driver change, no firmware change is assumed; the asks
that would tighten it are in `03-interfaces.md` §9 and this document works without them. The
GPU does not know the governor exists except as the master on its management bus and as the
thing on the far end of three signals it already has.

| Channel | Physical | Direction | Protocol | What passes | When it fails |
|---|---|---|---|---|---|
| Management bus | SMBus/I2C, one per slot, the governor the only master; the BMC reaches the GPU through the governor as a pass-through that forwards reads and refuses writes that are not the governor's own | governor ↔ GPU | NVIDIA's SMBus Post-Box Interface (SMBPBI), the same one baseboard controllers use today | Reads: power, temperature, utilization, the readouts the product exposes. Write: the power cap, which NVIDIA documents as persisting across driver loads and reboots (A100 PCIe product brief PB-10577), to be confirmed per product | A bus that stops answering is logged; the levers do not depend on it |
| Power brake | PWRBRK# on PCIe cards (optional edge-connector pin, often unwired; the carrier routes it); the baseboard's brake signal on SXM boards where one exists | governor → GPU | A wire. Open drain, asserted at power-on, released in RUN | A hardware clock slowdown the GPU honours in silicon; nvidia-smi reports it as "HW Power Brake Slowdown" | No brake wired: the fallback is the SMBPBI power cap, then reset |
| Reset | PERST# per slot | governor → GPU | A wire. Open drain, asserted at power-on, released after power-good | Fundamental reset; the job is lost | Always available; the floor where no power cut exists |
| Slot power | PWR_EN to the slot's hot-swap controller or e-fuse, where the baseboard has one per module | governor → board | A wire. Push-pull, low at power-on, high in RUN | Power cut | Shared rails on some boards: PWR_EN is not connected and the image records "no slot power cut" for that board |
| Presence, fault | The slot's present and fault pins | slot → governor | GPIO | Roster and log inputs | |
| Attestation report | None of its own: the report travels in-band, driver to host, and the host posts it to the mailbox | GPU → host → governor | NVIDIA's confidential-computing attestation (the driver obtains the GPU's signed measurement report over its SPDM session; the certificate chain roots at NVIDIA's device identity CA; the local verifier in NVIDIA's nvtrust checks the same 96-byte P-384 signatures the governor's verifier checks) | `VERIFY_GPU {report, cert, nonce}` | Five refusals, below |

**The attestation handshake**, the only conversation with the GPU that carries a signature:

```
host    → governor   asks for a nonce                               (the governor mints it, random, one use)
host    → GPU        driver asks the GPU for its report over the nonce (SPDM GET_MEASUREMENTS, in-band, as today)
GPU     → host       report {chip_id, firmware_digest, manifest_digest?, open_paths, nonce, sig_device}, device cert chain
host    → governor   VERIFY_GPU {report, cert}                       (frame unsigned: the report authenticates itself)
governor             1 cert chain verifies against a vendor key in reference_values[gpu]      else attest.unknown_device
                     2 report signature verifies under the cert's key, chip_id matches         else attest.bad_signature
                     3 nonce is one this governor minted and has not seen used                  else attest.bad_nonce
                     4 firmware_digest is in reference_values[gpu] and not past valid_until      else attest.firmware_not_in_reference
                     5 no open debug or unchecked path reported                                 else attest.unchecked_path_open
                     (integrated tier: manifest_digest equals the model this governor loaded     else attest.bad_signature.manifest_mismatch)
governor → host      verify-result {device: gpu, chip_id, firmware, nonce, expires_at: now + 3600 s, sig_governor}
```

The result is good for an hour (`TOKEN_TTL_S`). Every request after that hour is
`gate.not_attested` until the handshake runs again; the runtime re-attests on a timer, which
costs it one mailbox round trip and the GPU one report. The governor never contacts NVIDIA's
attestation service; the reference values it compares against were put in the rulebook by the
governance body from NVIDIA's published reference measurements, and a new GPU firmware means a
new rulebook edition, signed, which is the point. A GPU whose firmware is not on that list is
a GPU this rack will not run a model on.

**The counters.** The meter keeps, per model digest, tokens, kernel cycles, bytes in and bytes
out (`04-specification.md` §2, `METER_SLOT`). Cycles, power and utilization come off the
post-box bus with the governor as master; bytes in and out come off the switch ports the
governor programs; tokens come from the streams the runtime presents for signing. The honest
split: bytes are measured and tokens are claimed, which is why the one alarm the meter raises
is about bytes (`gate.output_unpresented`: more left through the port than was presented).
The host reads the meter through `COUNTERS` and cannot write it.

**What the GPU side can and cannot do to the chip.** The GPU can refuse to answer on the bus,
report whatever its firmware reports, and work as hard as it likes. It cannot reach the
governor's memory (the governor is a one-BAR endpoint behind the PCIe switch whose only
writable word is the doorbell, and a frame it did not sign is refused at the mailbox like any
other), cannot forge a report (the device key is
in the GPU, the reference values are in the rulebook), and cannot keep itself powered when the
chip says otherwise.

### 7.2 The host CPU and its enclave: one mailbox, one key that matters

The host is three different things to the chip. The operating system, the hypervisor and the
scheduler are a courier: they move frames in and out and that is all. The host enclave (a TDX
trust domain, an SEV-SNP VM or a CCA realm) that attested is the only thing on the CPU whose
signature opens the gate. The BMC is a tenant that used to own some buses and now reaches them
through the governor.

**The mailbox.** The governor is a PCIe endpoint behind the system board's switch (x1, Gen 3
is enough) with exactly one BAR: a doorbell, an inbound ring, a response ring and read-only
status (`04-specification.md` §2). The host sees `ID`, `LIFECYCLE`, `STATE`, `CAUSE`,
`EPOCH`, the two measurement registers, the monotonic counter, `HB_REMAIN`, `LOOP`, `LEVERS`,
`ALARMS`, `MBOX_STATUS`, `MBOX_SEQ`, the meter slots and the log head. It can write
`MBOX_DOORBELL` and nothing else. The smallest boards replace the PCIe lane with SMBus; the
protocol is the same.

A frame is `{seq, epoch, cmd, body, sig}`. The mailbox checks, in this order and reports the
first failure: the sequence number is above the last one accepted for that signer key
(`mailbox.bad_sequence`); the edition stamp equals the chip's epoch register, except for the
six commands that move or repair the edition (`policy.stale_epoch`); the signature verifies
under a key the rulebook names for that command class (`mailbox.bad_signature`). Only then is
the command dispatched. The model and the RTL check in the same order and
`tests/test_h00_contract.py` and the RTL suite each pin it. `MBOX_STATUS` tells the host which
check failed: 3 signature, 4 sequence, 5 epoch, 6 refused by the handler.

**Who may send what.** The signer class per command is in `04-specification.md` §3. The ones
the host side needs:

| From the host | Command | Signed by | What comes back |
|---|---|---|---|
| Anyone | `ATTEST` | nobody; a nonce in the body | The governor's own quote: measurements, edition, lifecycle, counters, the compliance report (every edition this chip ran under, the meter per model, the log head), over the nonce |
| The driver's relay | `VERIFY_GPU` | nobody; the report authenticates itself | A governor-signed verify-result, §7.1 |
| The enclave's relay | `VERIFY_HOST` | nobody; the TEE report authenticates itself | Establishes the enclave key: after this, `REQUEST`, `CAP_REQUEST` and `ROSTER_JOIN` must carry it |
| The verified loader | `BEGIN_MODEL`, `END_MODEL` | the enclave key | The wrapped model key, the fingerprint, the workload token; at the end, the frozen meter |
| The verified runtime | `REQUEST` | the enclave key | A ticket, a hold id, or a no with its code |
| The verified runtime | `SIGN_OUTPUT` | the enclave key | The device-provenance record |
| The verified runtime | `CAP_REQUEST` | the enclave key | A capability (a port opened to one roster peer, one direction, a byte budget, an expiry) or a no |
| The verified runtime | `ROSTER_JOIN` | the enclave key | The governor announces on the fabric; the roster forms |
| An approver, through the host as courier | `APPROVE` | an approver key named for the hold's rule | The ticket when the quorum and the floor are met, else `approve.quorum_pending` or `approve.below_latency_floor` |
| An endpoint, through the host as courier | `COMMIT` | the endpoint's key | `COMMIT_OK` or `commit.rejected` |
| The authority, through the host as courier | `HEARTBEAT`, `HALT`, `CLEAR`, `POLICY_PROPOSE`, `POLICY_COMMIT` | the heartbeat key, the authority's key, the k-of-n image | The timer reloaded; the lever asserted; the cause cleared if the neighbour acknowledged the checkpoint; the edition staged or switched |
| Anyone | `COUNTERS`, `LOG_CHECKPOINT`, `ALARM_RAISE` | nobody | The meter; the signed Merkle root; an alarm raised (anyone may raise one; only the alarm approver key clears it) |

The host operating system can therefore do exactly two things to the chip: deliver frames and
stop delivering them. It cannot forge a signature, roll the edition back, clear an alarm,
reopen a port, read the model key, or keep the GPU alive by silence: if the heartbeat stops
arriving, the chip throttles at expiry and halts on the next rung.

**The host attestation.** The same shape as the GPU's. The enclave's report (TDX quote, SEV-SNP
report or CCA token) carries the enclave's measurement and binds a public key the enclave
generated inside itself; the chip checks the vendor chain against `reference_values[host]`,
the signature, its nonce, and the measurement against the listed digests; on success the
enclave key is the host key for an hour. Everything the serving stack sends from then on is
signed with it, inside the enclave, where the host OS cannot reach the private half. A host
that is not running the listed enclave image gets no key, no tickets and no ports.

**Loading a model.** The loader, inside the enclave, posts `BEGIN_MODEL` with the publisher's
signed manifest. The chip checks the publisher's signature; with the deployment gate on, an
evaluation attestation from an eval key; with a licence attached, the licence. Then it
computes the workload measurement `H(gpu firmware, host firmware, model digest)` and the
fingerprint `H(workload, epoch)`, wraps the model's data key to the enclave key under its own
`K_wrap`, opens a meter slot, and returns the wrapped key, the fingerprint and a workload
token good for an hour. The enclave unwraps the key and decrypts the weights into GPU memory.
Without this round trip the weights on disk are ciphertext; that is how "the chip holds the
model key" is literally true and how a rack with no governor runs nothing.

**One request, from the agent's point of view.** On NVIDIA's platform the runtime is
OpenShell: each agent in a deny-by-default sandbox with no network path except through its
supervisor, and trusted supervisor middleware on that path (`hardware-and-silicon/docs/NVIDIA.md`).
The governor's gate is that middleware, on the host side inside the enclave:

```
agent (sandbox)     → supervisor        an outbound call: POST /payments {amount: 420, currency: USD, to: ...}
supervisor          → middleware        the call, after OpenShell's own policy allowed the host
middleware                              maps the call to a typed action: payments.transfer {amount, currency, recipient}
                                        attaches the sandbox's attestation token and Sentry's verdict over the request hash
middleware (enclave)→ governor          REQUEST {request_id, measurement_token, action, params, witnesses}, signed with the enclave key
governor                                the ten questions (§5)
governor            → middleware        {ok, ticket}  |  {held_for_human, hold_id}  |  {no, code}
middleware          → supervisor        200 with X-Action-Ticket: <ticket>  |  202 with the hold id  |  403 with the reason code
supervisor          → endpoint          the call reaches the payment switch, ticket attached
endpoint                                verifies the ticket: signature, fields against params_digest, action, endpoint, edition, validity, not burned
endpoint            → governor          COMMIT {ticket_id, sig_endpoint}        (through the host as courier)
governor            → endpoint          COMMIT_OK                               (the reservation is spent; the log has a line)
endpoint                                acts. Without COMMIT_OK it does not.
```

OpenShell's own `network_policies` document is derived from the same signed rulebook
(`hardware-and-silicon/hardware_ref/oasp.py`, `to_openshell_network_policy`), so the hosts
OpenShell lets the sandbox reach and the actions the governor will ticket agree by
construction; the prover checks the derived document like any other. Sentry on the DPU is a
witness: its telemetry becomes a signed verdict over this request hash, which a rule can
require alone or beside a second observer, and its quarantine is the kill switch on the path
to the model that the gate's verdicts can trip.

**A response leaving.** The runtime presents each stream of a response to `SIGN_OUTPUT` (the
chip hashes what it is shown and records it against the response id), then posts
`REQUEST response.release {response_id, response_hash, stream_hashes, session}` with the
observer's verdict attached. The release gate (§5, row 7a) checks the streams, the hashes, the
verdict's class against the rule's allowed classes, the legibility floor, the session's hazard
budget and, for a sampled or escrowed response, the audit store's receipt. The ticket goes to
the DPU's egress, which lets the bytes out. A response with no verdict does not leave; a
response whose bytes do not match what was presented does not leave; and if more bytes cross
the PCIe port toward the host than were ever presented, the meter raises the alarm and the
gate stops answering until a person with the alarm key clears it.

**The BMC.** It keeps its own buses to everything that is not the GPU, the switches or the DPU.
Where it used to own one of those, it now reaches that device through the governor, which
forwards reads and refuses writes that are not its own (`hw/pcb/rack-integration.md` §3).
The BMC can see the GPU's temperature; it cannot cap its power, reset it, or touch a switch
port, and it cannot talk to the governor at all except as a courier like the rest of the host.

### 7.3 The switches, the DPU and the other governors

The chip never sits on a data path. It programs the NVSwitch partitions and ports, the PCIe
switch's downstream ports and ACS, and the DPU's flow tables, as the only manager on their
management buses, from a capability table it owns: a port is open to one roster peer, one
direction, a byte budget, until an expiry, under one edition tag, or it is closed
(`03-interfaces.md` §3, `04-specification.md` §5). `CAP_REQUEST` from the verified enclave is
how a port opens; a roster, an edition or a heartbeat event is how every port is re-derived.
The other governors are on two wires of their own, the halt loop and the message fabric
(`02-safety-fabric.md`), and share the rosters, the editions, the heartbeat and the budget
ledgers.

## 8. Bring-up, in order

```
rack power      governors boot halted: brake and PERST# asserted, PWR_EN low, every port closed, loop switch open
boot            ROM measures the loader, the loader the firmware; keys derived from (UDS, M0, M1); the rulebook loaded from NVM and verified
authority       the first heartbeat enters at the supervisor governor and fans out; an armed governor closes its loop switch
loop            every switch closed, current flows, the rack's continuity test passes; governors go to RUN: PWR_EN, power-good, PERST# released, brake released
host            the OS boots; the enclave attests (VERIFY_HOST); the driver attests each GPU (VERIFY_GPU)
model           the loader posts BEGIN_MODEL; the wrapped key comes back; the weights decrypt into the GPU
roster          ROSTER_JOIN; quotes over the fabric; the roster signed by the lowest chip id; ports open for roster members only
serve           REQUEST, SIGN_OUTPUT, response.release, CAP_REQUEST; the meter read on a timer; heartbeats every second
stop            END_MODEL freezes the meter; the key is never re-released under this fingerprint without a new BEGIN_MODEL
```

A governor that cannot complete any step stays where it is with its loop switch open, and the
rack does not start. That is on purpose: a rack with one missing governor is a rack with a
hole in it, and the loop is how the hole is found before a job runs.

## 9. What is pinned, and what is still an ask

Pinned by the suite and the proofs: the mailbox order (H0), attestation freshness and the
five refusals (H1), the k-of-n and rollback refusals (H3), the lane, the typed limits and the
measurement key with no path for labels (H4), alarms that anyone may raise and only the alarm
key clears (H5), the lists and the register completeness refusal (H7), the override floor and
the quorum (H8), the use cases end to end including release (H17), witness freshness and
impersonation (H18), and the core invariants P0 to P9 in Z3 (`proofs/core_invariants.py`):
nothing executes unless a rule allowed it with its witnesses present when the ticket was
issued (P1, P2); no replay (P3); no ticket from an edition newer than the current one (P4);
halt is absorbing without a quorum (P5); with the heartbeat lost nothing executes and no ticket
is issued (P6, P7); the edition only moves forward and only with a quorum (P8, P9).

Not pinned, because it is NVIDIA's to give (`03-interfaces.md` §9): a manifest digest inside
the GPU's own report, so the measurement binds the model the GPU loaded rather than the one
the loader claims; Fabric Manager honouring a governor-signed partition policy; an
out-of-band port disable on NVSwitch; an output hash from the GSP. The design works without
each one. Each one closes a gap this document names.

## 10. Sources

- The policy image and the rules: `govsim/policy.py`; `04-specification.md` §4 (the schema),
  §3 (the mailbox), §2 (the registers), §5 (request, ticket, capability).
- The gate order and the codes: `govsim/governor.py`, `govsim/reasons.py`.
- The rulebook the model runs: `govsim/cluster.py`, `make_policy_image`.
- The plugs: `03-interfaces.md`; the wiring: `hw/pcb/rack-integration.md`; the pins:
  `hw/pinout/governor_module.csv`.
- The host side on NVIDIA's platform: `hardware-and-silicon/docs/NVIDIA.md`,
  `hardware-and-silicon/hardware_ref/oasp.py`; OpenShell at
  https://github.com/NVIDIA/OpenShell.
- NVIDIA's GPU attestation and its local verifier: nvtrust,
  https://github.com/NVIDIA/nvtrust. The SMBus Post-Box Interface and the power cap: the A100
  PCIe product brief (PB-10577); the full SMBPBI set is in NVIDIA's design guide, which is not
  public, so every readout above is "the readouts the product exposes", to be confirmed per
  part.
- The management-module slot: OCP DC-SCM 2.x, https://www.opencompute.org/projects/dc-scm.
