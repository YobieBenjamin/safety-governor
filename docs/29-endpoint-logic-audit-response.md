# The endpoint logic audit of 30 October 2026, the review panel, and the fresh audit that followed: the response

Three rounds of independent review of the endpoint-receipts work, all answered in this branch.

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

**Round three.** After the third commit, a fresh auditor that had seen none of the earlier reviews audited the branch as
pushed (294f331) against the same attacker. Verdict: DOES NOT HOLD, with two catastrophic, five serious and four
moderate findings, eleven losses reproduced by probe. Five of the eleven were rulebook shapes that enforced nothing (a
release rule whose risk ceiling was 1.0, a messaging rule with no budget and no rate and no list at its device, rules
that named no endpoint, a rack-local money budget, an audit store with no governance anchors); the rest were code.
The fourth commit answers all fourteen, adds a shape check that refuses such editions at signing time, and keeps the
auditor's probes, inverted, as `tests/test_fresh_audit_30_october.py`. The lesson, in Yobie Benjamin's words from two
days earlier: a rulebook error is an enforcement error; the compiler now catches the class, not the instance.

This response is evidence for people to check, not a verdict. GOAL.md says no AI is the final judge; the person merges,
after three further fresh audits: one on the default rulebook, two on rulebooks with different values (the profiles in
`govsim/profiles.py`), so a result that depends on the numbers the authors chose shows up.

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
5. It records request hashes and reservations it has acted on (one authorization, one effect) and keeps those
   records for as long as any credential naming them can still be presented; refuses receipts and approvals older
   than any ticket can live; bounds ticket life to the TTL plus the longest rule delay; refuses malformed window
   edges and malformed lists rather than raising; ties the signer to the governor the ticket names; refuses expired
   lists; keeps the list version floor across a restart.
6. Since the fourth commit: it binds an observer verdict by the response hash only for a release, and for a release
   re-checks hazard class, legibility and escrow; it counts the rule's rate as it counts its budget; it takes the
   edition's expiry from the edition alone; it refuses a rule that names no endpoint; it holds a device key the
   edition lists under its role, installs no edition otherwise, and shares a rule's limit with the other listed
   devices of its role; it honours a governor's signed revocation statement (the governor's last act before its
   tamper response wipes the key) and keeps it across a restart; an egress that shares a MAC key with its governor
   takes only MACed release tickets and MACed commit statements.

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

## The fresh audit's findings, and what was done with each

| # | Finding (short) | Status | Test |
|---|---|---|---|
| 1 | CATASTROPHIC: a captured release verdict on a clean chat reply fired a strike through a response_hash parameter | fixed (response-hash binding only for a release rule) | `test_1_...` |
| 2 | CATASTROPHIC: the egress released a response the observer called hazardous; the release risk ceiling was 1.0; a signed release ticket bypassed the MAC path | fixed (hazard class, legibility and escrow re-checked at the egress; default ceiling 0.5 and the shape check refuses 1.0; release tickets and commit statements must be MACed at an egress holding the key) | `test_2_...` |
| 3 | SERIOUS: real approvals paid again once the used-record store cycled | fixed (approvals carry the time given and age like receipts; records kept past expiry for the longest rule delay) | `test_3_...` |
| 4 | SERIOUS: rates counted nowhere at the endpoint | fixed (`_rate_room`) | `test_4_...` |
| 5 | SERIOUS: a governor-signed epoch statement erased the edition expiry | fixed (the expiry comes from the edition alone; a statement naming another epoch is refused) | `test_5_...` |
| 6 | SERIOUS: per-device budget count; money scaled with devices sharing a role name | fixed for an unlisted device (no device key the edition lists, no edition, no action); listed devices share the limit; **open** for a clone with the listed device's key | `test_8_...`, `test_8b_...` (xfail) |
| 7 | SERIOUS: a tamper did not reach a rack-local budget | fixed (the governor's signed revocation statement, delivered to every endpoint before the key is wiped, kept in the store) | `test_10_...` |
| 8 | MODERATE: the audit store checked no edition | fixed (built with the governance anchors like every endpoint) | `test_6_...` |
| 9 | MODERATE: a rule with no endpoint accepted everywhere | fixed (refused at every device; the shape check refuses the edition) | `test_7_...`, `test_12_...` |
| 10 | MODERATE: one fleet reservation spent twice between the ticket's expiry and its receipts' ageing | fixed (records kept for the grace the receipts can live) | `test_9_...` |
| 11 | MODERATE: the default messaging exit unbounded | fixed (a rate by default; the device holds the recipient list; the shape check refuses an outward rule with neither budget nor rate) | `test_11_...` |
| 12 | NOTE: things that held | kept as tests | `test_held_*` |
| 13 | NOTE: `install_list` raised on malformed fields | fixed | `test_13_...` |
| 14 | NOTE: the commit `at` check and the MAC commit path were untested | tested | `test_14_...` |

The auditor's mutation table (seven regression tests that passed for incidental reasons) was answered test by test:
the receipt age, the reservation record, the statement fields for a rack-local budget and the amount comparison each
now have a test that fails when its check is removed.

What stays unbounded at the endpoint against the extracted key, stated plainly: a clone of a listed device that holds the device's
own key (design item: per-device attestation of the devices themselves); the open rows F, I and M; and an edition
whose shape the check does not cover. An auto-mode rule with no budget and no rate can no longer be signed for an
outward action (`policy.shape_problems`).

Suites after the fourth commit: 644 passed, 6 xfailed (F, I, M, 4b, 10, 8b); `python -m govsim.redteam` VERDICT 1;
`python -m govsim.bench` about five governed actions a second per governor chip. The third commit's count of 607 was
the author's machine; the auditor measured 602 on a fresh clone, and the count here is from a fresh clone.

What this does not claim: the open rows are open; the attacker is the one the two reviews described, not every
attacker; and the hard core (RTL) carries none of the new ticket fields.
