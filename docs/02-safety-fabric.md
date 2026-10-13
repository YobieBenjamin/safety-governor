# 02 · The safety fabric

Two wires run through every governor in a cluster. They are physically separate from the
data network, the management network and the host. One is dumb and fast. One is smart and
signed. Both are fail-safe.

In plain words: a fire-alarm loop and an intercom. The loop rings every bell the instant any
station is pulled, and rings them if the wire is cut. The intercom carries the details:
who pulled it, which edition of the rulebook is in force, who is still on duty.

> **Plain-English version:** `10-plain-english-walkthrough.md` §6.
> **Backed by:** model `govsim/fabric.py` (`HaltLoop`, `MessageFabric`), `govsim/governor.py`
> (`_heartbeat`, `sense_loop`, `on_fabric`, `publish_checkpoint`), `govsim/cluster.py`
> (`change_epoch`, `exchange_checkpoints`); tests `tests/test_h11_halt_loop.py`,
> `test_h12_fabric_auth.py`, `test_h13_shared_budget.py`, `test_h14_partition.py`; hardware
> `rtl/governor_rtl/halt_loop.py`, `heartbeat.py`, `epoch_reg.py`; wiring
> `hw/pcb/rack-integration.md` §4.

## 1. The halt loop

**What it is.** A series current loop (4 to 20 mA class, like an industrial safety circuit)
threaded through every governor in a safety domain. Each governor has a loop-in and a
loop-out pin and a normally-closed switch between them. Each governor also senses loop
current.

![The halt loop as a circuit](figures/fig-halt-loop.png)

**Rules.**

- Any governor opens its switch when it enters HALT for any reason (`01-architecture.md`,
  safe-mode machine).
- Loss of loop current at any governor drives that governor's halt output within one
  sense period (target 100 µs, bound 1 ms end to end for a 72-GPU domain).
- A broken wire, a lost connector, a dead governor or a pulled board all read as "open"
  and halt the domain. Fail-safe by construction.
- The loop is closed again only when every governor has received a signed CLEAR over the
  message fabric and has logged it. A governor whose cause is not cleared keeps the loop open.
- Domains are configurable: a cluster may run several loops (one per job pod) joined by a
  supervisor governor that bridges them under policy.

**Why a wire and not a message.** A message can be dropped, delayed, replayed or filtered
by anything between sender and receiver. A current loop has no software between a pull and
a bell. Fire codes learned this a century ago.

**Timing.** Sense period 100 µs. Propagation is electrical, so the end-to-end bound is set by
the slowest sense period plus debounce: 1 ms. These are design targets, to be measured on
the bench in Phase 2; the functional model's "100 µs" is a parameter, not a result. The GPU's
power brake asserts within 1 ms of the governor's halt output; reset and power cut follow the
policy's rungs.

**Tested by.** `tests/test_h11_halt_loop.py`: any governor halting halts all; a cut wire
halts all; no governor clears on its own; propagation stays within the bound.

## 2. The message fabric

**What it is.** A private out-of-band network between governors: two SGMII-class ports per
governor forming a dual ring, or a star to a safety switch that is itself a governor. On the
board-level tier the physical layer can be 100BASE-T1 (two-wire automotive Ethernet) or
RS-485 for small clusters. Bandwidth needs are tiny: attestation quotes, rosters, epochs,
heartbeats, reservations and checkpoint heads, kilobytes per second per governor.

**Every message** carries: sender identity (DICE-derived key id), the sender's policy epoch,
a per-sender sequence number, a timestamp from the sender's monotonic counter, the message
type and body, and a signature. A receiver accepts a message only if the sender is on the
current roster (or the message is a roster-formation quote), the epoch matches, the sequence
number is greater than the last seen from that sender, and the signature verifies.

In plain words: every note on the intercom is signed, numbered and dated. A note from
someone not on the roll, an old note read out again, or a note under last year's rulebook
goes in the bin.

### Message types

| Type | From → to | Body | Purpose |
|---|---|---|---|
| `QUOTE` | governor → all | Attestation quote over a nonce; GPU fingerprint; capabilities | Roster formation |
| `ROSTER` | roster leader → members | Job id, member list with key ids, expiry, signatures | Scope every later decision |
| `HEARTBEAT` | authority → governors, relayed hop by hop | Validity window, epoch, authority signature, relay signature and hop count | Dead man's switch |
| `EPOCH_PROPOSE` | authority → governors | Policy image digest, k-of-n signatures, activation deadline | Start an epoch change |
| `EPOCH_ACK` | governor → authority | Digest, local verification result | Each member confirms |
| `EPOCH_COMMIT` | authority → governors | Digest, list of acknowledging members | Make the epoch live everywhere at once |
| `RESERVE` / `RESERVE_OK` / `RESERVE_DENY` | governor → budget owner → governor | Budget key, amount, ticket id, expiry | Shared budgets |
| `COMMIT` / `RELEASE` | governor → budget owner | Reservation id | Spend or free a reservation |
| `ALARM` | governor → all | Cause code, request hash, evidence digest | A witness any governor may raise |
| `HALT_CAUSE` | governor → all | Cause, log head | Why the loop opened |
| `CLEAR` | authority → governor | Cause id, log head acknowledged, signature | Close the loop at one governor |
| `CHECKPOINT` | governor → neighbors | Log Merkle root, size, head, signature | Cross-linked logs |

### Roster formation

1. A job scheduler (untrusted) names the GPUs it wants.
2. Each named governor broadcasts a `QUOTE` over a nonce derived from the job id and its
   monotonic counter.
3. The lowest key id among valid quotes acts as roster leader for the job; it assembles the
   `ROSTER` and signs it; each member countersigns.
4. The roster is live when every member holds the countersigned roster. It expires with the
   job or at its stated time, whichever is first.
5. The switch ports and flows opened for the job, the shared budgets and the job's output
   records all name the roster id.

A governor whose GPU fails attestation cannot produce a valid `QUOTE` and is simply absent
from the roster. Nothing it says afterwards is accepted. Analogy: no badge, no seat on the bus,
and nobody listens to you shouting from the parking lot.

### Epoch change, cluster-atomic

A policy change that reaches some GPUs and not others is a hazard: a ticket minted under the
new rules could be presented to an endpoint still on the old ones, or the reverse. So the
epoch moves in two phases, with a deadline:

1. `EPOCH_PROPOSE` carries the signed image digest and an activation deadline.
2. Every member verifies the image and the quorum itself (it does not trust the authority's
   word), and replies `EPOCH_ACK`.
3. When all members have acknowledged, the authority sends `EPOCH_COMMIT`; each governor
   switches its epoch register at the commit, and tickets, capabilities and messages from the
   old epoch die.
4. A member that has not acknowledged by the deadline is halted by its own heartbeat rule
   (the authority stops relaying heartbeats to it) and dropped from the roster. It does not
   keep running on the old rules.

Analogy: the new edition of the rulebook is handed out, everyone initials receipt, and only
then does the manager say "from now". Anyone who did not initial is sent home, not left
working from the old book.

### Heartbeat fan-out

The policy authority (a key, not a chip) signs a heartbeat with a validity window. It enters
the fabric at one or more governors and is relayed hop by hop; each relay appends its own
signature and increments the hop count. A governor accepts a heartbeat if the authority's
signature verifies, the window is current, and the hop count is under the policy limit. A
governor that receives no valid heartbeat before its timer expires enters safe mode. A
partitioned segment that is cut off from the authority halts itself at expiry; nothing in the
segment can forge the authority's signature to keep itself alive.

### Shared budgets

A budget key has exactly one owner on the roster (assigned in the roster; the leader by
default). A governor that needs to reserve against a shared key sends `RESERVE` to the owner;
the owner runs the same check-reserve-commit transaction it runs locally and answers. The
requesting governor mints the ticket only on `RESERVE_OK`. Reservations expire with the
ticket. If the owner leaves the roster, the roster is rebuilt and outstanding reservations
against that key are released and re-requested. This is the blog's rule "one ledger owns a
budget key" made concrete across a cluster. Analogy: one cashier per cash drawer; a second
cashier does not guess what is in it.

### Cross-linked logs

Every governor keeps its own hash-chained log and publishes signed checkpoints. Each
checkpoint also includes the latest checkpoint heads it has received from its fabric
neighbors. Rewriting one governor's history now requires rewriting its neighbors', and
theirs, outward through the cluster. Analogy: each security office writes the last line of
the neighbors' log books into its own.

## 3. Partitions and failure

| Event | Loop | Fabric | Outcome |
|---|---|---|---|
| One governor loses power | opens | silent | Domain halts; CLEAR after the cause is understood |
| Fabric link cut, loop intact | closed | partitioned | Segment without the authority halts at heartbeat expiry; segment with the authority continues; roster rebuilt |
| Loop cut, fabric intact | open | up | Domain halts at once; `HALT_CAUSE` says "loop break at governor N" |
| Authority key unreachable | closed, then opens | up, no heartbeats | Whole domain goes to safe mode at expiry (availability cost, by design) |
| Rogue device plugged into the fabric | closed | sees traffic | Cannot produce a valid quote; never on a roster; its messages are dropped; its presence is logged |
| Replay of an old heartbeat | closed | up | Sequence number and window fail; dropped; logged |

**Tested by.** `tests/test_h12_fabric_auth.py`, `tests/test_h13_shared_budget.py`,
`tests/test_h14_partition.py`.

## 4. What the fabric does not do

It does not carry model data. It does not carry tool-call payloads. It cannot speed up a
halt beyond the loop (it carries the reason, not the stop). It cannot make a governor trust a
GPU that failed attestation. And it is not a consensus protocol in the Paxos sense: the policy
authority is a single key with a quorum behind it, and the fabric's job is to deliver that
authority's decisions to every governor or to halt the ones it cannot reach.
