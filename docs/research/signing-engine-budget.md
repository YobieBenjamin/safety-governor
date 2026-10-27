# The signing engine's budget: MACs where only one party checks

Adversarial audit 3, catalog rows 19 and 20 (SERIOUS) and 32, 34 and 39 (CLAIM).

## The problem

Every per-response release ticket was a P-384 signature (17 ms on an OTBN-class engine). The full serving path needed
88 percent of one engine at 500-token responses and 306 percent at 100-token responses, while the sweep still reported
"the signing engine keeps up: pass". Separately, every fabric message was signed and verified by every member: with one
governor per GPU, the loop roll call alone needed 126 percent of one engine at 72 members.

## The design

- **Release tickets are MACs.** A release ticket is only ever checked by the node's own egress endpoint, so it is
  authenticated with an HMAC under a key the governor and that egress share (set up at attestation), on the hash
  engine. Action tickets, which third-party endpoints check, stay P-384 signatures. Public, durable evidence of every
  release still comes from the batched, signed provenance records.
- **Fabric traffic between roster members is MACed.** Each governor has an X25519 key derived from its unique secret
  and attested in its roster quote; members derive one pairwise key each (HKDF, bound to the roster and the pair).
  Quotes and rosters stay signed.
- **The sweep tells the truth.** CONTRACT-GOVERNOR-OVERHEAD-BOUNDED now passes only if firmware is under 1 percent of
  GPU time, the full path (records, release tickets, action tickets) is under half an engine at 100-token responses
  and in a mixed workload, and the roll call at 72 members with the fabric authentication the model actually uses is
  under half an engine.

## The numbers (govsim/bench.py)

| | before | now |
|---|---|---|
| Full path, 500-token responses | 88% | 34% |
| Full path, 100-token responses | 306% | 34% |
| Roll call, 72 members, per member | 126% | 3% |
| Signed action tickets beside 100-token serving | | about 9 a second per chip (1.2 per GPU at 8 GPUs) |

Assumptions, stated: HMAC about 2 microseconds on the hash engine; a P-384 verify costs about a sign. Phase 2
measurement on real hardware replaces both.

## What is still open

- The action-ticket rate is a real ceiling. A workload with more consequential actions needs a dedicated ECC engine.
- One chip per GPU or one per eight GPUs changes the rack cost and the roll-call size; both are priced, and the README
  says which figure assumes which.
