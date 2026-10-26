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

## What is still open

- The fleet ledger in the model is one object. In a real fleet it must be a replicated service: a quorum of ledger
  replicas across regions commits each reservation before a ticket is minted, so no single ledger is a single point of
  failure or of capture, and a partitioned region stops fleet-budgeted actions instead of spending the whole cap on each
  side. Not modelled yet.
- Which limits must be fleet-wide (payments, bytes leaving the fleet, compute) is a rulebook decision; the edition marks
  them by owner.
- Latency: a fleet-budgeted action waits for a cross-region round trip. Measure it in the deployment overhead simulation.
- Stage: Fleet and mandate.
