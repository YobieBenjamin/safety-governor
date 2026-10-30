# The endpoint logic audit of 30 October 2026, and the review panel that followed: the response

Two rounds of independent review of the endpoint-receipts work, both answered in this branch.

**Round one.** A fresh agent audited the first endpoint-receipts commit (23a6b5a) against GOAL.md, with the host, one
governor's signing key, and the fleet ledger's reachability under the attacker's control. It wrote sixteen probes, A
to P, and every one reproduced. The second commit answered them, and its author wrote that the merge conditions were
met.

**Round two.** A four-member panel convened by Yobie Benjamin (an independent software architect, a code ninja, a
senior experience risk and business analyst, and a business analyst) reviewed the second commit without having seen
it made. Three members independently broke it under the same attacker. Their verdict was DO NOT MERGE, unanimous, with
a priority list of changes; the panel record is `design/30-review-panel-decision.md` in the project, and the round
files and probes are kept beside it. The sentence "its merge conditions are met" was wrong and is withdrawn. The third
commit answers the panel's list. Its probes are kept, inverted, as `tests/test_review_panel_30_october.py`; the round
one probes as `tests/test_audit_30_october_probes.py`.

This response is evidence for people to check, not a verdict. GOAL.md says no AI is the final judge; the person merges,
after the fresh audit the panel asks for (item 15).

The attacker model throughout: one governor's signing key extracted without tripping the tamper mesh; every field of a
ticket under the attacker's pen; captured receipts and captured commit statements reused; a host that forwards the
commit to the governor and, when the governor refuses, answers with a commit statement the attacker signs itself,
carrying every captured receipt. Experiment B's attacker (docs/29-claim-experiments-protocol.md on the experiments
branch) holds no key and its endpoint is honest, so a B result says nothing about this attacker.

Status words: **fixed** (in code, with a test that failed before and passes now), **intended** (behaviour the design
wants, recorded so it is not mistaken for a defect), **open** (a design item, not fixed here; each has a strict xfail
test so its closing is noticed).

## What the endpoint now does that it did not before

1. It recomputes the request hash from the request id and measurement in the ticket and the action and parameters it
   is handed, so every approval, verdict and receipt that names the hash is tied to those parameters.
2. It enforces the rule's mode: the edition's quorum of approver signatures over the hash and the epoch for a
   human-mode rule; an unexpired observer verdict under the rule's risk ceiling for an observer-mode rule.
3. It acts only on a commit statement from the minting governor (signed; MACed for a MACed release ticket) that names
   the ticket, the request hash, this endpoint, the ticket's budget key and reservation, with a time inside the
   ticket's life, and, when the edition owns the rule's budget as fleet, the threshold of replicas' fleet-commit
   receipts, each bound to this request, this ticket and this endpoint name. Every budget check keys off the edition's
   rule, never off a field of the ticket.
4. It keeps its own count of what it has let through under each budget key against the rule's limit and window, so a
   rack-local budget is bounded at the device with no ledger and the host forging commits.
5. It records request hashes and reservations it has acted on (one authorization, one effect), refuses receipts older
   than any ticket can live, bounds ticket life to the TTL plus the longest rule delay, refuses malformed window
   edges rather than raising, ties the signer to the governor the ticket names, refuses expired lists, and keeps the
   list version floor across a restart.

## The round one probes, A to P

| # | Finding (short) | Status | Test |
|---|---|---|---|
| A | A human-mode rule accepted on the governor signature alone | fixed (mode enforced at the endpoint; approvals tied to parameters by the recomputed hash, see panel item 2) | `test_A_...`, panel `test_2_...` |
| B | Receipts proved a reservation, not a commit; swallowed commits refilled the cap | fixed (signed commit statement with fleet-commit receipts; and the endpoint's own count) | `test_B_...`, panel `test_1_...` |
| C | A rack-local budget had no check at the endpoint | fixed (the endpoint's own count against the rule's limit and window) | `test_C_...`, panel `test_5_...` |
| D | Receipts not bound to the request | fixed (binding of request hash, endpoint and ticket id in every receipt; hash recomputed) | `test_D_...` |
| E | The used-reservation record is per device | fixed for a re-signed ticket (receipts name the ticket id); **open** for a verbatim ticket at two devices sharing one role name, see panel item 4b | `test_E_...`, panel `test_4b_...` (xfail) |
| F | A keyless host starves the fleet cap by reserving | open (rate limit per requester at the ledger, not designed) | `test_F_...` (xfail) |
| G | Partial reservations never released | fixed | `test_G_...` |
| H | One replica down stops fleet payments (k = n) | intended (fail closed) | `test_H_...` |
| I | A lowered threshold allows n/k times the cap | open (the bound is stated; the choice between H and I is the operator's) | `test_I_...` (xfail) |
| J | No upper bound on ticket validity | fixed (TTL plus the longest rule delay) | `test_J_...` |
| K | An expired signed list installed | fixed | `test_K_...` |
| L | List version floor lost on restart | fixed | `test_L_...` |
| M | The beneficiary registry is not an endpoint constraint | open | `test_M_...` (xfail) |
| N | Pre-tamper tickets act after the tamper | fixed for budgeted rules (no commit the endpoint will accept); **open** for an unbudgeted rule, bounded by the TTL and the rule's per-ticket maximum, see panel item 10 | `test_N_...`, panel `test_10_...` (xfail) |
| O | Signer not tied to the governor field | fixed | `test_O_...` |
| P | A refused commit burns the ticket | intended | `test_P_...` |

## The review panel's list, and what was done with each item

| # | The panel's item | Status | Test or record |
|---|---|---|---|
| 1 | Commit verification keyed off the edition's rule, never the ticket's budget field; a ticket whose budget fields differ from the rule's is refused | fixed | `test_1_dropping_the_budget_key_...`, `test_8_a_reservation_on_a_rule_without_a_budget_...` |
| 2 | One authorization, one effect: credentials tied to the parameters, request hashes recorded as spent | fixed (request id in the ticket, hash recomputed; `used_requests` in the store) | `test_2_two_honest_approvals_...` |
| 3 | Observer verdicts checked for expiry and risk; approvals for the epoch | fixed | `test_3_an_expired_or_risky_verdict_...` |
| 4 | Commit statement names the endpoint; fleet-commit receipts carry the binding; a captured statement cannot be rewrapped | fixed for a re-signed ticket; the verbatim-ticket case at a second device sharing the role name is **open** (per-device identity in the edition is a design item) | `test_4_...`, `test_4b_...` (xfail) |
| 5 | The default rack's money budget bounded without the governor | fixed (the endpoint's own count; 200 key-signed $999 tickets move at most the $2,000 cap) | `test_5_the_default_rack_...` |
| 6 | The fleet replica trusts its caller for limit, window and clock | recorded: the "second party" claim is withdrawn in the code comment and in `docs/research/fleet-ledger.md`; the code change is a named follow-up with the architect's probes P4a to P4d as its tests | `docs/research/fleet-ledger.md` |
| 7 | Partial-commit and swallowed-statement costs | recorded as accepted costs in `docs/research/fleet-ledger.md` | |
| 8 | The release path's per-response signature | fixed (a MACed release ticket gets a MACed commit statement; the bench prices commit statements: about five governed actions per second per governor chip on one signing engine, release path unchanged) | `test_9_a_release_commit_costs_no_signature` |
| 9 | docs/04 and docs/03 updated with the ticket and commit formats, sizes and verification counts | done in docs/04 section 5; the RTL plan still says nothing about carrying them: **open**, stated there | |
| 10 | docs/29 corrected | this document | |
| 11 | The regression battery's attacker writes every field and reuses captured material | fixed (`attacker_host` and `signed_with_governor_key` rewritten; the panel module's `Attacker` class) | both modules |
| 12 | `valid_from` validated like `expires_at` | fixed | `test_7_a_malformed_valid_from_is_refused` |
| 13 | Ticket life bounded to the TTL plus the longest rule delay | fixed | `test_J_...` |
| 14 | Receipts age | fixed (`at` in every receipt; refused when older than a ticket can live) | `test_6_captured_receipts_age_out` |
| 15 | A fresh audit of this branch after 1 to 14 | not yet done; the merge waits for it | |

What stays unbounded at the endpoint against the extracted key, stated plainly: an auto-mode rule with no budget and
no rate (such a rule has nothing for the endpoint to count), and the two open rows above. The remedy for the first is
in the rulebook: every rule whose action moves value or leaves the rack carries a budget or a rate.

Suites after the third commit: 607 passed, 5 xfailed (F, I, M, 4b, 10); `python -m govsim.redteam` VERDICT 1.

What this does not claim: the open rows are open; the attacker is the one the two reviews described, not every
attacker; and the hard core (RTL) carries none of the new ticket fields.
