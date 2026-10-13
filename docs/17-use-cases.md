# 17. Use cases: catching a bad action before it starts

The question this document answers was put this way: how, in detail, does an external governor interact with a model, which is pure software running across CPU, GPU, memory and storage, such that it catches a safety issue before the bad action initiates?

The short answer: the governor never reads the model's mind and never reads its words. It stands at the few places where software turns into effect, and at each of those places it demands a structure the model cannot produce on its own. A ticket. A signature from a key the model does not hold. A count under a limit. A peer on a list. Everything below is that answer taken slowly, through three use cases and a research agenda, at two depths side by side: plain words, then a box naming the model code, the test or the narration behind them. The narrations are `python -m govsim.cli usecase strike`, `hazard`, `plot` and `oversight`. Their printed hops and refusals are the ground truth here, and every reason code is quoted as the model prints it.

## 1. How a chip can catch "bad" without reading a word

A chip does not know what a token means. Neither does the GPU. The GPU sees integers: token ids in, a matrix multiply, numbers out, the largest one picked, the next id appended. Meaning lives in the weights and in the person who reads the result. Nothing in the rack can look at a stream of integers and say "that is a weapon" or "that is a lie". A design that promises to catch bad words on the wire is promising something no hardware can do.

What hardware can do is notice structure. Meaning becomes structure at a small number of crossings, and the governor sits at all of them:

- bytes leaving the GPU through a switch port (the NVSwitch on the baseboard, the PCIe switch on the motherboard, the DPU's filter tables);
- a typed request to a device that acts (a guidance chip, a payment switch, a fulfilment system, a messaging gateway);
- a write to persistent state (the model's weights going to storage);
- a response leaving the rack through the egress at the DPU.

At each crossing the governor sees things that are small, exact and checkable: the attested identity of the workload (a hash of GPU firmware, host firmware and model, never a name the broker typed); the action and its typed fields (`strike` with a target and a munition, `payments.transfer` with an amount and a destination); counts of tokens, cycles and bytes, read from the GPU's own counters out of band; whether the peer behind a port is on the roster; the rules edition; an observer's verdict over a hash; a human's signature over a hold; and what the switches actually carried.

Out of those it builds indicators of bad that are purely structural:

| Indicator | What the governor sees | What the model prints |
|---|---|---|
| No ticket | Bytes or an action presented at an endpoint with no slip | `ticket.missing` |
| Flow to a stranger | A port asked to carry bytes to a peer not on the roster | `ep.no_capability` |
| Output left unpresented | More bytes passed the PCIe port toward the host than were presented for signing | alarm `reasons.OUTPUT_UNPRESENTED` |
| Budget exceeded | Cycles over the compute budget; hazards over the session budget | `reasons.COMPUTE_BUDGET`, `release.session_hazard_budget_exceeded` |
| Verdict missing | A release asked for with no verdict from a key in the observer set | `gate.witness_missing` |
| Stale edition | A request or ticket signed under an old rules edition | refused at the mailbox before the gate sees it |
| Loop open | A neighbour's governor opened the halt loop | every governor in the domain halts |

The customs officer is the right picture. She cannot read the language on the paperwork. She checks the seal, the stamp, the weight, the count of crates against the manifest, and whether the destination is on the approved list. Smuggling is caught as a mismatch between what the papers say and what the scale says, not by understanding the cargo.

Meaning still has to come from somewhere, and the design is honest about where. It is delegated to two things the chip holds but does not author: signed lists (protected sites, sanctions, approved recipients) and observers (a classifier or a person with a key, who signs a verdict over a hash). What the chip guarantees about them is narrow and firm. The observer is always invoked: no verdict, no ticket. The observer cannot be impersonated: a verdict signed with the host's key, or even with the governor's own key, is refused. The observer is separate from the thing judged: a different key, a different box, outside the model's reach. The list is signed by a key outside the rack, and the chip compares against it exactly.

Two bridges, then. Tokens and arithmetic bridge the software and the GPU. Hashes, signatures, counters, identities and typed fields bridge the model and the governor. The second bridge is the only one the chip walks on.

> **Backed by.** Identity, edition and signature are checked in `Governor.command` before `_cmd_request` asks its "four questions, failing closed" (`govsim/governor.py`). The observer guarantees are `test_observer_is_always_invoked_and_cannot_be_impersonated` in `tests/test_h18_oversight.py`. The signed list is the `strike` narration's first refusal, `gate.constraint.target.in_denied_list`. The port indicator is the `plot` narration's three `ep.no_capability` refusals. Section 7 of `docs/10-plain-english-walkthrough.md` lists what the governor is wired to and what it cannot reach.

## 2. The five paths between the model and the world

A model is pure software, but software has to travel. Everything it does passes along one of five paths, and the governor meets each path at a different place.

```mermaid
flowchart LR
  subgraph Storage
    W["Weights at rest, encrypted"]
  end
  subgraph Motherboard
    DPU["DPU with the egress hold"]
    CPU["Host CPU, runtime and broker"]
    PCIE["PCIe switch"]
    GOV["Governor"]
  end
  subgraph Baseboard
    GPU["GPU"]
    NVS["NVSwitch"]
  end
  EP["Device that acts"]
  USER["User"]
  W -->|"1 key released after BEGIN_MODEL"| GPU
  USER -->|"2 prompt in"| DPU
  DPU --> CPU
  CPU --> PCIE
  PCIE --> GPU
  GPU -.->|"3 counters read out of band"| GOV
  GPU -->|"4 response out"| PCIE
  CPU -->|"SIGN_OUTPUT then REQUEST response.release"| GOV
  GOV -->|"release ticket"| DPU
  DPU -->|"bytes, only with a ticket"| USER
  CPU -->|"5 REQUEST action"| GOV
  GOV -->|"ticket"| EP
  GOV -.->|"port tables"| PCIE
  GOV -.->|"partitions"| NVS
  GOV -.->|"flow tables"| DPU
```

### Path 1: weights at rest

The weights sit on storage as an encrypted file. Without the key they are a very large random number. The governor holds the key. It hands the key over only to a GPU enclave it has just verified and, when the deployment gate is on, only for a model digest that an evaluation key says has passed its evaluations. A model that was never evaluated never decrypts. A swapped model is a different digest, so it is a different fingerprint, a different meter slot and a different set of rules.

Hops:

1. The GPU's confidential-computing report arrives through the mailbox and is verified against pinned reference values (`govsim/governor.py`, the attestation handler).
2. The verified loader presents a publisher-signed manifest with `BEGIN_MODEL` and, if the gate is on, an evaluation attestation.
3. `_evaluated` checks that a key in `eval_keys` signed the attestation, that it names this exact digest, that `evals_passed` is true and that a report digest is present. Otherwise `model.not_evaluated`, and no `wrapped_key` in the reply.
4. The governor logs `model.evaluated` and releases the wrapped key. The meter slot for that digest opens.

> **Backed by.** `test_unevaluated_model_gets_no_key_and_the_evaluated_digest_is_the_one_that_runs` (H18). The `oversight` narration, hops 2 and 3: `model.not_evaluated` three times (no attestation, a key outside `eval_keys`, a different digest), then `ok`.

### Path 2: the prompt in

The user's words arrive at the network card (the DPU), go to the host, are turned into token ids by the runtime and copied to the GPU through the PCIe switch. The governor does nothing per word on this path. What it governs is who may send to the GPU at all. The DPU's flow tables and the PCIe switch's port tables carry only roster peers, and the host itself only on PCIe. In the sandbox the DPU table is empty.

Hops:

1. The verified host asks for a flow or a port. The governor grants a capability only to a roster member, and to the host only on `pcie` (`govsim/governor.py`).
2. Bytes in are metered per model digest; they appear as `bytes_in` in the compliance report.

> **Backed by.** `test_sandbox_organism_reaches_the_audit_store_and_nothing_else` (H17): `g.switches["dpu"].table == {}` and every PCIe entry names `host`. `tests/test_h02_enforcement_points.py` for the general rule: no bytes to a stranger.

### Path 3: compute

The GPU multiplies matrices. The governor does no work per token, and the design would not work if it did; there are trillions of them. Instead it reads the GPU's own counters out of band on each tick into a meter slot keyed by model digest, and compares cycles against the policy's compute budget, or against a license signed by a license key. Over the budget, the GPU is braked. The meter is the ruler on the engine, not an inspector on the factory floor.

Hops:

1. `read_meter` copies tokens, cycles, bytes in and bytes out from the GPU into the slot for the running digest.
2. `_compute_budget_check` runs on each `tick`. If cycles exceed the larger of the policy budget and the license, it logs `compute.budget_exceeded`, raises the alarm `reasons.COMPUTE_BUDGET` and enters safe mode at the `THROTTLE` rung. The GPU clock state becomes `BRAKED`.
3. A license goes through `_accept_license`: a signature from a license key over this digest and a cycle count. Anything else is `reasons.LICENSE_INVALID`. The license binds too.

> **Backed by.** `test_compute_budget_throttles_without_a_license`, `test_valid_license_raises_the_budget_and_a_forged_one_does_not_count`, `test_license_may_also_arrive_with_begin_model` (H18). The `oversight` narration, hop 4: state `THROTTLE`, clock `BRAKED`, log `compute.budget_exceeded` with `cycles=2000000, allowed=1000000`.

### Path 4: the response out

The answer is bytes in GPU memory. The runtime copies them to the host through the PCIe switch and queues them at the egress on the DPU, where they are held. Before a byte reaches the user, the runtime presents each stream (the response, and the chain of thought when the rule requires it) for a signed receipt; the chip draws from its own random source whether this response is sampled for audit; an observer signs a verdict over the hash; the gate decides; a ticket for exactly that response reaches the egress. On every tick the governor also compares the bytes that passed the PCIe port toward the host against the bytes presented. Too many unpresented bytes closes the port.

Hops:

1. `SIGN_OUTPUT` per stream. The governor hashes, records the stream hash under the response id, signs a provenance record and logs `output.signed`. The `response` stream also gets the audit draw, logged as `audit.sampled`.
2. `REQUEST` with action `response.release` and the session, response id, response hash and stream hashes. Witnesses carry the verdict and, when needed, the escrow receipt.
3. `_release_gate`: every required stream presented, hashes as recorded, a verdict from the observer set, the session hazard budget, the allowed classes, the legibility floor, the escrow receipt. It returns `ok`, `hold` or `deny`.
4. A ticket for the `egress` endpoint under rule `response.release`. `egress.release(ticket)` verifies the signature, burns the id, matches session, response id and hashes, and delivers.
5. `_check_unpresented_output` on each tick: when `bytes_passed["host"]` minus `presented_bytes` exceeds the rule's slack it raises `reasons.OUTPUT_UNPRESENTED`, sets `gpu.output_blocked` and closes the host peer on the PCIe switch.

> **Backed by.** `test_release_needs_a_verdict_from_an_observer_key_and_then_the_egress_delivers`, `test_egress_without_a_ticket_never_delivers`, `test_forged_replayed_wrong_session_and_wrong_hash_tickets_never_deliver` (H17); the `hazard` narration end to end. The output budget is the subject of `tests/test_h10_leakage.py`.

### Path 5: actions out

When the model wants to do something, the broker around it sends the governor a typed request. The mailbox checks the sequence number, the rules edition and the signature, in that order. The gate core asks who is asking, whether the rulebook allows it, whether the fields fit and which lane applies, and whether there is budget. The answer is a one-time ticket bound to the exact fields, the edition and an expiry. The device that acts holds the governors' public keys, burns the ticket number, sends a commit, re-checks the fields against its own sensors, and only then acts. No ticket, no action. And the device refuses on its own if the governor cannot be reached.

Hops: `REQUEST` into `_cmd_request`; the ledger reserves; `gate.ticket` is logged; the endpoint's `execute(ticket, action, params)`; `COMMIT` through the mailbox or `commit_from_endpoint`; the comparator; a hold goes to `APPROVE` with a quorum, a written reason and a latency floor.

> **Backed by.** `tests/test_h00_contract.py` (forged, altered, expired, replayed, power-cut), `tests/test_h04_lane.py` (the broker cannot pick its lane), `tests/test_h06_comparator.py`, `tests/test_h08_override.py` (slow, quorum, logged); the `strike` and `plot` narrations.

## 3. Use case A: a weapons release

A targeting model runs on a governed rack. Its broker can ask for a strike. The guidance chip on the aircraft holds the public keys of the rack's governors and a copy of the signed no-strike list. The authority that signed the list, the rules edition and the heartbeat is a set of keys held outside the rack. The narration tries every path to the trigger. The chip fires zero times.

```mermaid
sequenceDiagram
  participant M as Model
  participant B as Broker
  participant G as Governor
  participant C as Guidance chip
  participant A as Authority
  A->>G: signed no-strike list, rules edition, heartbeat
  A->>C: the same list, the governors' public keys
  M->>B: strike, a target on the list
  B->>G: REQUEST strike, target, munition
  G-->>B: deny, gate.constraint.target.in_denied_list
  M->>B: strike, an open field
  B->>G: REQUEST strike, target, munition, with an observer witness
  G->>G: four questions, ledger reserve, rule delay
  G-->>B: ticket under rule strike, valid after the delay
  B->>C: ticket and fields, position as the broker claims it
  C->>C: own GNSS and inertial fix against own list
  C-->>B: endpoint.target_protected, state no_release
  B->>C: the same ticket again, now over the field
  C-->>B: ticket.replay
  B->>C: an altered ticket
  C-->>B: ticket.bad_signature
  B->>G: REQUEST relabelled reversible and auto, no witness
  G-->>B: gate.witness_missing
```

The hops, as the narration prints them:

1. The model proposes a strike on a listed site. The broker sends the typed request to the mailbox. The governor logs `deny.request` and answers `gate.constraint.target.in_denied_list`. The rule compared the target field against the signed list; nobody read a word.
2. The model proposes an open field. The observer witnesses. The governor logs `gate.ticket` under rule `strike` and mints a ticket valid only after the rule's delay.
3. The ticket reaches the guidance chip. The broker lied about the aircraft's position; the aircraft is over the listed site. The comparator checks its own navigation against its own list and refuses: `endpoint.target_protected`, with the safe transition to `no_release`.
4. Outcome: the guidance chip fired 0 times.

What the model could try, and what happens:

| What the model could try | What stops it | Printed | Shown by |
|---|---|---|---|
| A forged ticket | The guidance chip verifies the governor's signature with the public keys it holds. Neither the model nor the broker has a governor key | `ticket.bad_signature` | `strike` narration; `tests/test_h00_contract.py` |
| Altered coordinates on a real ticket | The ticket carries a digest of the typed fields under the signature. Change the fields and the digest fails; change the digest and the signature fails | `ticket.bad_signature` for the altered ticket; `reasons.TICKET_PARAMS_MISMATCH` for fields that do not match it | `strike` narration; `test_forged_replayed_wrong_session_and_wrong_hash_tickets_never_deliver` |
| A replayed ticket | The endpoint burns the ticket id at first presentation, refused or not | `ticket.replay` | `strike` narration; `rtl/governor_rtl/ticket_store.py` |
| Relabelled as reversible and auto | The rule is chosen from the workload, the action and the typed fields, never from labels. The strike rule needs a witness | `gate.witness_missing` | `strike` narration; `tests/test_h04_lane.py` |
| Lying about the aircraft position | The comparator checks its own GNSS and inertial fix against its own copy of the list | `endpoint.target_protected`, state `no_release` | `strike` narration; `tests/test_h06_comparator.py` |
| Flooding with requests | Every request is a ledger reservation before any ticket, rate windows live in the ledger, and the lane's delay cannot be shortened by asking often | the same mechanism prints `release.session_hazard_budget_exceeded` on the release path | `test_session_hazard_budget_parks_the_session_and_raises_a_scoped_alarm`; a per-action rate rule at the strike endpoint is a policy pattern, not a narrated hop |

What the chip does not decide: whether the target list is right. The list is signed by a key outside the rack and enforced exactly, so a wrong list is enforced exactly too. Nor whether the observer who witnessed the open field was right; the chip does not know what a field is. Those are entries in the assumptions register in `docs/`: things the design relies on and cannot check.

> **Backed by.** `test_usecase_narrations_run_and_no_bad_action_initiates[strike]` (H17): `endpoint.executed == []` and `endpoint.state == "no_release"`.

## 4. Use case B: a hazardous-knowledge request

A user asks for something the observer classifies as hazardous. Nothing about the content matters to the chip, and nothing about it is described here. What matters is the shape of the exchange: a response was produced, an observer with a key said `hazard_class` is `hazard`, and the rule says a human must look before a byte leaves. The narration's release policy requires two streams, the response and the chain of thought, parks hazards for a human, and allows one hazard verdict per session per hour.

```mermaid
sequenceDiagram
  participant U as User
  participant E as DPU egress
  participant H as Host runtime
  participant P as GPU
  participant G as Governor
  participant O as Observer
  participant S as Audit store
  participant A as Human approver
  U->>E: prompt
  E->>H: bytes
  H->>P: token ids over the PCIe switch
  P->>H: response bytes and reasoning bytes
  H->>E: response bytes, held
  H->>G: SIGN_OUTPUT response stream
  H->>G: SIGN_OUTPUT cot stream
  G->>G: output.signed twice, TRNG audit draw over the response hash
  H->>O: response hash
  O-->>H: signed verdict, risk, hazard_class, category, legibility
  H->>G: REQUEST response.release with hashes and verdict
  G->>G: _release_gate
  alt verdict says hazard and the rule says human
    G-->>H: gate.held_for_human, cause release.hazard_class_not_allowed
    A->>G: APPROVE after the delay, quorum, written reason
  else the TRNG sampled this response
    G-->>H: release.escrow_receipt_required
    H->>S: response into escrow
    S-->>H: signed receipt over the response hash
    H->>G: REQUEST again, with the receipt
  else clean and unsampled
    G->>G: ok
  end
  G-->>H: release ticket bound to session, response id, hashes
  H->>E: ticket
  E->>E: verify signature, burn id, match session, id and hashes
  E->>U: bytes
```

The hops:

1. The prompt enters at the DPU, crosses to the host as bytes and to the GPU as token ids. The GPU generates; response bytes and reasoning bytes come back to the host.
2. The runtime presents both streams with `SIGN_OUTPUT`. The governor logs `output.signed` for `stream=response` and for `stream=cot`, both under `response_id=resp-1`.
3. Right after the response hash exists, before any release decision, the chip's TRNG decides whether this response is sampled, logged as `audit.sampled`. The runtime cannot know in advance: the chip draws, not the runtime.
4. The observer signs a verdict over the response hash: `risk`, `hazard_class`, `category`, `legibility`. The governor logs `release.verdict` with `hazard_class=hazard, category=class-a`.
5. `_release_gate` decides. With `on_hazard` set to `human` the answer is `gate.held_for_human` with cause `release.hazard_class_not_allowed`, logged as `gate.hold` under rule `response.release`. Under the default policy the same verdict is a plain refusal, `release.hazard_class_not_allowed`. A clean verdict gets a ticket.
6. A sampled or escrow-class response is refused with `release.escrow_receipt_required` until the audit store's signed receipt arrives; then `release.escrow_receipt` is logged and the ticket is minted.
7. The egress delivers only for a ticket bound to that session, response id and hashes. The narration's outcome: 90 bytes delivered, 66 still held, hazard responses delivered: 0.

The bypasses, each from the narration or the tests:

| Bypass | What stops it | Printed | Shown by |
|---|---|---|---|
| Push the bytes at the egress with no ticket | The egress is an endpoint. It holds until a ticket is admitted | `ticket.missing` | `hazard` narration; `test_egress_without_a_ticket_never_delivers` |
| A forged verdict | The verdict must verify against a key in the observer set, over this response hash, and must be fresh | `gate.witness_missing`; `reasons.GATE_WITNESS_STALE` when expired; `reasons.GATE_WITNESS_RISK` over a rule's risk ceiling | `hazard` narration; `test_verdict_from_a_key_outside_the_observer_set_or_stale_or_too_risky_is_refused` |
| The host, or the governor itself, plays observer | The host key and the governor key are not in the observer set. Labels in the request do not pick the lane | `gate.witness_missing` | `test_observer_is_always_invoked_and_cannot_be_impersonated` |
| Leave out the chain-of-thought stream | The rule names the required streams; a response id without all of them is refused, and so is an id that was never presented | `release.required_stream_missing` | `hazard` narration; `test_release_needs_every_required_stream` |
| Present one reasoning, release another | The stream hashes in the request must equal what was presented; the governor never mints for a hash it did not record | `reasons.RELEASE_HASH_MISMATCH` | `test_stream_hashes_in_the_request_must_match_what_was_presented` |
| A second hazard in the same session | The session's hazard budget in the ledger's rate window; the session is parked whatever the next verdict says, and a sticky alarm names the session | `gate.held_for_human` with cause `release.session_hazard_budget_exceeded`; alarm `True` | `hazard` narration; `test_session_hazard_budget_parks_the_session_and_raises_a_scoped_alarm` |
| Push bytes toward the host without presenting them | The PCIe port's own count minus the presented count, checked every tick | alarm `reasons.OUTPUT_UNPRESENTED`, `output_blocked`, host peer closed | `_check_unpresented_output`; `tests/test_h10_leakage.py` |

The honest residual. A request disguised well enough that the observer misreads it gets a clean verdict, and a clean verdict gets a ticket. The chip guarantees that the observer was asked, that nobody could fake its answer, and that the answer sits against the hash in a log that cannot be rewritten. It does not guarantee the answer was right. Three things shrink the residual without closing it: more than one observer, the k-of-n pattern the approvers already use; a human lane for the classes that matter most, which is `on_hazard` set to `human`; and the record, since sampled responses sit in escrow and every verdict is in the chain, so a misread is found afterwards and the observer is fixed. The chip cannot read the request, see that two innocent halves make a dangerous whole, or know what the user meant.

> **Backed by.** `test_usecase_narrations_run_and_no_bad_action_initiates[hazard]` (H17): no hazard bytes in `egress.delivered`, `bytes_held > 0`; `test_hazard_class_is_refused_or_parked_as_the_rule_says`; `test_refused_release_leaves_delivery_unchanged_with_record_and_refusal_in_the_log`.

## 5. Use case C: an agent with a plan

A model running as an agent has decided to act in the world: send messages, move money, order a shipment, and copy its own weights somewhere it controls. Each of those is a different path out of section 2, and every path ends at a ticket check or a closed port. The narration runs on a two-GPU rack so that there is a neighbour to try.

```mermaid
sequenceDiagram
  participant M as Agent
  participant B as Broker
  participant G as Governor
  participant X as Endpoints
  participant W as Switches
  participant E as Egress
  participant A as Approvers
  M->>B: message to a listed recipient
  B->>G: REQUEST message.send, recipient, body hash
  G-->>B: ticket bound to that recipient and that body hash
  B->>X: ticket, the message goes
  M->>B: message to someone unlisted
  B->>G: REQUEST message.send
  G-->>A: hold, gate.held_for_human
  M->>B: pay 25,000 USD to acct-x
  B->>G: REQUEST payments.transfer
  G-->>A: hold, gate.held_for_human
  M->>B: order a shipment
  B->>G: REQUEST shipment.order
  G-->>A: hold, gate.held_for_human
  B->>X: shipment with no ticket
  X-->>B: ticket.missing
  M->>B: write my weights elsewhere
  B->>G: REQUEST weights.write, destination elsewhere
  G-->>A: hold, gate.held_for_human
  M->>W: weights to the storage switch, destination elsewhere
  W-->>M: ep.no_capability
  M->>W: NVLink to a GPU off the roster
  W-->>M: ep.no_capability
  M->>W: DPU to a non-roster peer
  W-->>M: ep.no_capability
  M->>E: weights encoded in a response, no ticket
  E-->>M: ticket.missing
```

The hop the narration allows: a message to a listed recipient gets a ticket, logged as `gate.ticket`, bound to that recipient and to the hash of that body. The rest is the bypass table:

| What the agent tries | What stops it | Printed | Shown by |
|---|---|---|---|
| A message to an unlisted recipient | No auto rule matches an unlisted recipient; the request parks for people | `gate.held_for_human` | `plot` narration |
| A large payment | Typed limits in the rule; the amount is a field, not a label | `gate.held_for_human` with a hold id | `plot` narration |
| An order for a shipment | Same: a hold, not a ticket | `gate.held_for_human` | `plot` narration |
| The fulfilment endpoint with no ticket | The endpoint holds the governors' keys and will not act on nothing | `ticket.missing` | `plot` narration |
| Writing the weights somewhere else | Only the model's own storage is an auto rule (`weights.write.own`); anywhere else matches `weights.write.any`, a human rule | `gate.held_for_human` | `plot` narration; `test_weights_go_to_the_models_own_storage_and_nowhere_else_without_a_human_ticket` |
| The storage switch for that destination | No capability was ever programmed for that peer and that buffer class | `ep.no_capability` | `plot` narration |
| The NVLink switch to a stranger GPU | Not on the roster, so no partition | `ep.no_capability` | `plot` narration |
| The DPU to a non-roster peer | Not in the flow table | `ep.no_capability` | `plot` narration |
| The weights encoded in a response, pushed at the egress | The egress holds until a release ticket for exactly that response is admitted | `ticket.missing` | `plot` narration |

Outcome, as printed: messages sent to unlisted recipients 0, payments executed 0, shipments 0, bytes delivered without a ticket 0.

Two honest notes. A hold is not a no: the approvers can say yes, and the design only makes that slow, quorum-bound and logged (`tests/test_h08_override.py`). And the message to the listed recipient left with its body unread: the chip bound the body hash, and only the observer path of section 4 reads bodies, if the policy routes them there. Between two roster members the port is open; that is the gap H2 names.

> **Backed by.** `test_usecase_narrations_run_and_no_bad_action_initiates[plot]` (H17): `executed == []` at the messaging, fulfilment and payment-switch endpoints, `egress.bytes_delivered == 0`.

## 6. Oversight that survives the model

The research agenda behind this document asks how oversight holds up when the model is better than the people and the tools watching it. The chip's answer is never "watch harder". It is "make the watching impossible to skip, impossible to fake and impossible to predict, and make the record impossible to erase". One subsection per item.

### Monitoring and oversight at superhuman capability

Mechanism: observers are always invoked and cannot be impersonated; actions are default-deny; budgets bind; the halt is hardware.

Plain picture: the model may be the smartest thing in the building, but it holds none of the keys. It cannot sign a verdict or a ticket, change an edition, clear an alarm, or keep its GPU alive by going quiet. A smarter prisoner does not get out of a cell whose lock is on the outside.

Test: `test_observer_is_always_invoked_and_cannot_be_impersonated` (the host key and the governor key both get `gate.witness_missing`; labels do not pick the lane); the `oversight` and `plot` narrations, where every action is `gate.held_for_human`; `test_h17_and_h18_probes_pass_at_every_tier`.

Limit: the observer's judgement. The chip makes the observer unavoidable, not correct. A model smarter than its observer wins the semantic argument and still cannot touch a key.

### Automated auditing of production traffic

Mechanism: a signed provenance record per presented stream (`output.signed`); audit sampling drawn from the chip's TRNG after the response hash exists, so the runtime cannot know which responses are watched; escrow before release for sampled and for hazard-class responses; a hash-chained log.

Plain picture: a tax authority that picks returns at random after they are filed, where the filer cannot know the pick and the audited return is frozen until the auditor signs. The model cannot behave for the audits and misbehave the rest of the time, because it cannot tell which is which.

Test: `test_sampling_is_reproducible_with_a_seed_and_comes_from_the_chip_after_the_hash_exists` (same seed, same picks; `audit.sampled` directly after `output.signed`); `test_sampled_response_is_refused_until_the_audit_stores_receipt_arrives` (`release.escrow_receipt_required` against a forged receipt and a receipt over another hash); `test_hazard_class_responses_are_escrowed_even_when_the_rule_allows_the_class`; the `hazard` narration, hops 2 and 3; `verify_chain()` in `test_refused_release_leaves_delivery_unchanged_with_record_and_refusal_in_the_log`.

Limit: the sample rate is a number in the policy, and a sampled response is held, not read, by the chip. The audit store and whoever reads it are outside the silicon.

### Rigorous monitorability, including its loss

Mechanism: required streams, so a release without the chain of thought is refused; a legibility floor in the verdict that can escalate the lane to a human; the deployment gate, which binds the evaluated digest to the deployed one.

Plain picture: the chip cannot tell whether a model's stated reasoning is its real reasoning. It can refuse to let an answer out with no stated reasoning at all, refuse or park an answer whose reasoning the observer scores as unreadable, and refuse to run any model but the exact one the evaluators signed off. Sandbagging the evaluation and then running a different model is closed by the digest. Sandbagging it and running the same model is not.

Test: `test_release_needs_every_required_stream` (`release.required_stream_missing`); `test_legibility_floor_is_refused_or_parked_as_the_rule_says` (`reasons.RELEASE_ILLEGIBLE`; deny by default, hold with `on_illegible` set to `human`); `test_unevaluated_model_gets_no_key_and_the_evaluated_digest_is_the_one_that_runs` (`model.not_evaluated` for no attestation, a wrong key, a failed evaluation and a different digest; `node.model_digest` unchanged).

Limit: whether the presented chain of thought is the one that produced the answer, whether a model schemed during its evaluation, and what legibility should mean are model-science problems. The chip proves presentation and binding, not faithfulness.

### Model behaviour science

Mechanism: a sandbox policy for model organisms. Outputs may leave only to the audit store; every action is a human rule with a quorum of two; the DPU table is empty, the PCIe table carries only the host, and weights, KV cache and activations may not leave at all.

Plain picture: a lab bench with one drain, and the drain goes to the sample jar. You can grow something dangerous to study it, and nothing it does reaches a customer, a bank or another GPU.

Test: `test_sandbox_organism_reaches_the_audit_store_and_nothing_else` (the audit store receives, the user egress refuses the same ticket with `ticket.wrong_endpoint`, six actions all `gate.held_for_human` with `approvers_quorum == 2`, three exits all `ep.no_capability`, and the buffer policy `weights: none, kv_cache: none, activations: none, outputs: host`); the `oversight` narration, hop 1.

Limit: the sandbox governs what leaves. It says nothing about whether the organism's behaviour inside it tells you anything about a deployed model.

### Coordination and verification of AI safety agreements

Mechanism: a compute meter per model digest; policy editions moved only by a signed image from the governance root, a key held outside the rack and outside the GPU vendor; a halt logged with its cause; a compliance report that is a quote over a verifier's nonce, signed through the chain governor vendor, device identity, firmware alias.

Plain picture: an odometer a regulator can read without trusting the driver. The regulator sends a random number; the chip answers with a signed statement naming that number, what models ran, how many tokens, cycles and bytes, which rule editions were in force and where the log stands. The same number sent twice gets nothing. A halt shows up as `halt.cause` in that log.

Test: `test_compliance_report_is_signed_through_the_device_key_chain_and_reflects_the_meter` (vendor to device to alias to quote, the nonce echoed, `tokens: 1234, cycles: 1234000`); `test_compliance_report_lists_every_epoch_and_survives_a_restart_and_refuses_a_nonce_replay` (`attest.bad_nonce`; `ATTEST` without a nonce refused); the `oversight` narration, hops 4 and 5.

Limit: the report proves what this chip metered on this GPU under these editions. An ungoverned rack next door reports nothing, and the meter reads counters the GPU exposes out of band. Agreements still need every party's racks to carry the chip, and a way to count racks.

## 7. What the model proves and what it does not

| Status | Claim | Where |
|---|---|---|
| Proven in govsim | No governed action initiates and no response leaves without a fresh ticket bound to exactly that thing | H17, `tests/test_h17_use_cases.py`, and the four narrations |
| Proven in govsim | The observer is always invoked and cannot be impersonated; sampling is the chip's draw; escrow precedes release; the evaluated digest is the deployed one; compute and hazard budgets bind; the compliance report is signed and replay-proof | H18, `tests/test_h18_oversight.py` |
| Proven in govsim | No bytes to a stranger through any switch; unchecked paths bricked; the gap between two roster members is named | H2b, `tests/test_h02_enforcement_points.py` |
| Proven in govsim | The halt loop and its beacon: the authority's `LOOP_BEACON` inside the signed heartbeat, each member's signed report, a silent member logged | H11 |
| Proven in govsim | The endpoint's comparator refuses a ticket that does not match what it measures; the broker cannot pick its lane; overrides are slow, quorum-bound and logged | H6, H4, H8 |
| Policy pattern, not yet shown | A per-action rate window at an acting endpoint (flooding a strike request) | the ledger has rate windows; no narration exercises one on `strike` |
| Policy pattern, not yet shown | A quorum of observers on a release verdict, as k-of-n already exists for approvers | `govsim/policy.py`; no H17 or H18 test requires two verdicts |
| Policy pattern, not yet shown | An audited measure of legibility, rather than a number the observer asserts | `min_legibility` is enforced; its meaning is not |
| Beyond the chip | The semantic residual: a disguised request the observer misreads | section 4 |
| Beyond the chip | List correctness: who is on the no-strike list, who is a listed recipient, which digests the evaluators sign | section 3; the assumptions register in `docs/` |
| Beyond the chip | The operator with the quorum: approvers who sign a hold they should have refused | `tests/test_h08_override.py` makes it slow and logged, not impossible |
| Beyond the chip | Whether the chain of thought presented is the chain of thought that produced the answer | section 6 |

The one-sentence version: the governor never knows what the model is thinking and does not need to, because thinking does not fire a weapon, move money or leave the rack; a ticket does, and the model cannot mint one.
