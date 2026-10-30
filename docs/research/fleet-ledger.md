# Fleet-wide limits: one ledger for the whole fleet

Adversarial audit of 26 October 2026, catalog row 6 (CATASTROPHIC, fleet scale).

## The problem

Budgets were counted per rack. One action split across N racks got N times the cap: five racks moved 10,000 USD
against a 2,000 USD per hour cap, and at 100,000 racks the cap means nothing.

## The design

A budget whose owner in the edition is `fleet` is counted once for the whole fleet. Every governor in every rack
reserves and commits it at the fleet ledger. A governor that cannot reach the fleet ledger refuses the request; it never
falls back to a rack-local count. A reservation can be committed or released only by the governor that made it.

## What the code does now

`govsim/fleet.py`: `FleetLedger` and `build_fleet`. `govsim/governor.py` `_reserve` and `commit_from_endpoint` route
`fleet`-owned keys there. Tests: `test_a_fleet_wide_payment_cap_holds_across_racks` (five racks, 2,000 USD) and
`test_a_rack_cut_off_from_the_fleet_ledger_refuses_fleet_budgeted_actions`.

## Authenticated replicas (adversarial audit 3, catalog row 8)

Audit 3 found the governor trusted the ledger's answer with no signature, while in silicon it can reach a ledger only
through the untrusted host or network: a host answering "reserved" lifted a 2,000 USD cap to 9,000. Now:

- The ledger is `n` replicas, each with its own count and key; the edition names the replica keys and the threshold
  (`fleet_ledger`: {"keys", "threshold"}). The model requires all of them: with independent counters a majority rule
  lets concurrent requests land on different pairs and spend up to n/k times the cap, while with every replica
  required a lying replica can only refuse (fail closed).
- Every answer is a receipt signed by a replica over the budget key, the amount, the reserving governor and a fresh
  nonce the governor chose. The governor needs the threshold of distinct replicas before it mints, and again (with a new
  nonce) before it commits. Forged answers, replayed receipts and lying replicas cannot lift a cap.
- Tests: `tests/test_adversarial_audit_3.py` (`test_forged_fleet_ledger_answers_are_refused`,
  `test_one_captured_fleet_ledger_replica_cannot_lift_the_fleet_cap`).

Per GOAL.md the chip's boundary is the data center. A ledger's scope is set by the edition: normally one data center's
governors share it; a budget spanning data centers is a policy choice, and a site cut off from its ledger quorum refuses
the budgeted actions (fail closed) without affecting any other site.

## The replica's trust boundary (review panel, 30 October 2026)

What the replica checks for itself: that the reservation it is asked to commit or release was made by the governor
named as reserver, and its own count. What it takes from the caller: the budget limit, the window, the time (`now`) and
the TTL (`fleet.py`, `reserve`). In the model the only caller is a governor object in the same process, so this is
sound there; in silicon the governor reaches the replica over an untrusted path, and a caller that can set the limit or
the clock can lift or erase the count. So the receipts prove that a replica counted, not that it counted against the
edition's limit on the edition's clock. The claim that the fleet cap is "checked by a second party that does not trust
this governor" is withdrawn until the replica authenticates its caller and holds the limit, window and clock itself,
from the edition it is given. That change is a named follow-up with the architect's probes P4a to P4d
(`design/30-review-panel-decision.md`) as its tests.

Costs the design accepts, stated: a reservation that reaches the threshold at reserve but not at commit leaves the
committed amount counted at the replicas that did commit until the window passes; and a host that forwards the commit
and then drops the statement spends an hour of cap for no effect. Both are starvation, not theft; both are bounded by
the window; neither is fixed here.

## What is still open

- The replicas in the model count independently in one process. Requiring all of them costs availability: one
  unreachable replica stops fleet-budgeted actions. A consensus protocol among replicas in separate failure domains
  would let a majority decide on one shared count; it is not modelled.
- Which limits must be fleet-wide (payments, bytes leaving the fleet, compute) is a rulebook decision; the edition marks
  them by owner.
- Latency: a fleet-budgeted action waits for a cross-region round trip. Measure it in the deployment overhead simulation.
- Stage: Fleet and mandate.
