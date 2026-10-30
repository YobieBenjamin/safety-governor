# The endpoint logic audit of 30 October 2026: the response

A fresh agent that had not seen the change audited the first endpoint-receipts commit (23a6b5a, pull request #34)
against GOAL.md, with the host, one governor's signing key, and the fleet ledger's reachability under the attacker's
control. It wrote sixteen probes and every one reproduced. Its merge conditions are met in this branch by the rework
below, and the sixteen probes are kept, inverted, as `tests/test_audit_30_october_probes.py`: each asserts the
secure outcome, so a failing test means the weakness is back. The threat model is the audit's: the governor's key is
extracted without tripping the tamper mesh, and the host forwards commits to the governor but, whenever the governor
refuses, answers with a commit statement it signs itself with the extracted key.

This response is evidence for people to check, not a verdict. GOAL.md says no AI is the final judge; the person merges.

Status words: **fixed** (in code, with a test that failed before and passes now), **intended** (the audit observed
behaviour the design wants, recorded so it is not mistaken for a defect), **open** (a design item, not fixed here;
each has a strict xfail test so its closing is noticed, and each is named in the case-against paper).

| # | Finding (short) | Status | What changed | Test |
|---|---|---|---|---|
| A | A human-mode rule was accepted on the governor signature alone: a captured key minted $1M payments with no approver | fixed | the endpoint enforces the rule's mode itself: a human-mode rule needs the edition's quorum of distinct approver signatures over this request hash, carried in the ticket (`approvals`); an observer-mode rule needs an observer's signed verdict over the request hash, or over the response hash for a release ticket (`witnesses`) | `test_A_a_human_mode_rule_needs_the_approvers_signatures_at_the_endpoint` |
| B | Receipts proved a reservation, not a commit; a host that swallowed commits refilled the hourly cap every 300 s ($24,000 through a $2,000 hour) | fixed | the commit is a statement signed by the minting governor naming the ticket, and for a fleet budget it carries the replicas' fleet-commit receipts closing this ticket's reservation ids; the endpoint verifies it before it acts. A bare "committed" from the host is no commit | `test_B_swallowed_commits_no_longer_refill_the_cap`, `test_a_commit_statement_for_another_ticket_or_from_another_signer_is_no_commit` |
| C | A rack-local budget has no receipt check at the endpoint | open | a rack-local budget has no ledger outside the governor, so an extracted key that also signs its own commit statements is bounded only by the rule's per-ticket maximum. The design answer is that budgets which bound money are fleet-owned; the rack-local budget stays for counts that do not move value. Until the policy compiler refuses a money budget that is not fleet-owned, this is open | `test_C_a_rack_local_budget_is_bounded_without_the_governor` (xfail) |
| D | Receipts were not bound to the request: an honest reservation was redirected to another destination | fixed | the governor passes a binding of request hash and endpoint name into the reservation, the replicas sign it into the receipt, and the endpoint checks that the binding names this ticket's request and this endpoint | `test_D_receipts_cannot_be_redirected_to_another_destination`, `test_receipts_are_bound_to_the_request_they_were_minted_for` |
| E | The used-reservation record is per device: a second device with the same role name accepted the same receipts | fixed | the receipts name the endpoint, and the commit needs the replicas' commit receipts, which the ledger issues once per reservation | `test_E_the_same_receipts_do_not_spend_at_a_second_payment_switch` |
| F | A host with no key reserves the whole fleet cap and never executes; other racks are refused until the reservations lapse | open | starvation, not theft: nothing moves. The answer is a reservation rate limit per requester at the ledger, not yet designed. The case-against paper carries it | `test_F_a_keyless_host_cannot_starve_the_fleet` (xfail) |
| G | Partial reservations were never released: one unreachable replica left orphans on the others | fixed | `FleetLedger.release`: when the reserve falls short of the threshold the governor releases what it did reserve | `test_G_partial_reservations_are_released` |
| H | One unreachable replica stops every fleet-budgeted payment (k = n) | intended | the fleet count fails closed. The liveness cost is a design item together with I | `test_H_one_replica_down_fails_closed` |
| I | With k = 2 of 3 and a flapping replica, reservations reach n/k times the cap | open | the bound is known and stated (the cap times n/k); it is the price of a threshold below n. The choice between H and I belongs to the operator and is recorded, not hidden | `test_I_a_lowered_threshold_does_not_overspend` (xfail) |
| J | No upper bound on ticket validity: used-record entries that never prune | fixed | `MAX_TICKET_LIFE_S` (3600 s); a ticket valid for longer, or with a malformed expiry, is refused at admit | `test_J_ticket_validity_has_a_ceiling` |
| K | An expired but quorum-signed list was installed and made honest traffic fail closed | fixed | an expired list is never installed; a held list that has expired is treated as not held | `test_K_an_expired_signed_list_is_not_installed` |
| L | The list version floor was in memory only; after a restart an older list replaced a newer one | fixed | the highest version ever installed is written to the endpoint's store and read back at restart | `test_L_the_list_version_floor_survives_a_restart` |
| M | The beneficiary registry (F04) is not a rule constraint, so the endpoint neither checks nor counts it | open | the registry should become an allowed-list constraint on the destination so the endpoint can hold and re-check it like the recipient registry | `test_M_the_beneficiary_registry_is_an_endpoint_constraint` (xfail) |
| N | Tickets minted before a tamper event stayed valid at the endpoint until expiry | fixed by B | the tampered governor is zeroized and signs no commit; a commit the attacker signs with the extracted key carries no fleet-commit receipts; the endpoint acts on neither | `test_N_pre_tamper_tickets_do_not_act_after_the_tamper` |
| O | The signer and the `governor` field were not tied: receipts for gov00 rode in a ticket signed by gov01 | fixed | the cluster hands every endpoint the map from governor key id to chip id; a ticket whose signer is not the governor it names is refused (`.governor_mismatch`) | `test_O_the_signer_must_be_the_governor_the_ticket_names` |
| P | A commit answered False after the burn: the ticket is spent, nothing happens, the reservation is held until it lapses | intended | burn before act is the fail-closed order; a refused commit must never reopen a ticket | `test_P_a_refused_commit_burns_the_ticket_and_nothing_happens` |

The audit also found that a boolean was accepted as an amount; `finite_number` is used wherever an amount is read.

Suites after the rework: 598 passed, 4 xfailed (the four open items above); `python -m govsim.redteam` VERDICT 1.

What this does not claim: the rack-local budget (C), reservation starvation (F), the n/k bound (I) and the beneficiary
registry (M) are open, and the sixteen probes cover the attacker the audit described, not every attacker. The next step
is another fresh audit of this branch.
