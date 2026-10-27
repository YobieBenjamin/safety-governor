# Several rulebook authorities on one chip

Adversarial audit 3, catalog row 21 (SERIOUS). GOAL.md requirement 10 ("Be mandatable"): different jurisdictions can
apply different rulebooks without one weakening another's.

## The design

- A chip may hold further rulebook roots fused at manufacture (`Fuses.jurisdiction_roots`: name, key hashes,
  threshold). Each jurisdiction signs its own edition with its own quorum; another jurisdiction's keys or the main
  governance keys do not count (`Governor.install_jurisdiction`).
- A jurisdiction's edition names the actions it `governs`. For those actions a request must satisfy the main edition
  AND one rule of every jurisdiction that governs the action; the strictest requirement (auto, observer, human) applies.
  So a jurisdiction can only add restrictions: it cannot loosen the main rules or another jurisdiction's rules.
- An expired jurisdiction edition denies what it governs (fail closed). A fused jurisdiction that has not installed an
  edition has not spoken and constrains nothing.

## What the code does now

`govsim/fuses.py`, `govsim/governor.py` (`install_jurisdiction`, `_jurisdictions_allow`), `govsim/policy.py`
(`make_jurisdiction_edition`), `govsim/cluster.py` (`jurisdictions=`, `jurisdiction_edition`). Tests:
`test_a_jurisdiction_restricts_and_cannot_be_loosened_by_another`, `test_a_jurisdiction_edition_needs_its_own_roots_quorum`.

## What is still open

- Which jurisdictions apply to a given server (where it runs, whose users it serves) is a deployment and treaty
  question; the chip enforces whatever roots are fused.
- Jurisdiction editions do not yet carry signed lists of their own; they use the lists the main edition installs.
