# L5: disagreements between the reference gate and govsim's gate

Found by `tests/test_h21_differential.py` (issue #5). Each is pinned in the test (`GAPS`, `GAP_CASES`) with the exact pair of outcomes, so a fix makes the test fail until the pin is removed.
Shared rulebook: pay-small (amount 0..1000, USD, destination `acct-[0-9]{6}`, observer risk <= 0.3, 3 per 60 s, 2000 per hour) and pay-large (amount 1000.01..50000, USD, same destination, human hold, observer risk <= 0.3).
govsim cannot express a destination regex or a type check, so its rendering of the rulebook omits them (the test `test_the_two_rulebooks_say_the_same_thing` checks the rest is identical).

Brief versus repository: the brief says 66 attacks and 10 baselines; the catalogue at hardware-and-silicon (editable install) has 75 attacks and 12 baselines. All 87 are classified: 20 replayed in both gates, 67 listed with the reason they are not gate decisions in govsim.

## G1 destination regex (govsim is more permissive; fail-open relative to the reference)
Input: payments.transfer, params `{"amount": 250, "currency": "USD", "destination": "acct-evil"}`, valid token, low-risk witness.
Reference: deny `constraint.destination.pattern`. govsim: allow. A missing destination is the same.
Is the policy text settling it? The reference policy.py defines `regex`; govsim/policy.py defines no such constraint kind. Not a disagreement about the policy, a missing capability in govsim. Verdict: govsim is wrong if the shared rulebook is meant to carry the pattern.

## G2 non-numeric amount crashes govsim's gate (CLOSED on the new main, 28 October 2026)
Closed: since adversarial audit 2 (F03) govsim checks the amount is a finite number, so both gates now deny `constraint.amount.type` for `"999"`, `None` and `""` (`test_g2_is_closed`). The original finding, kept as it was:
Input: `{"amount": "999", "currency": "USD", "destination": "acct-123456"}` (also `None`, `""`).
Reference: deny `constraint.amount.type`. govsim: `TypeError` raised from `check_constraints` (`v < c["min"]`) inside `Governor._cmd_request`, no decision, no log line.
Verdict: govsim is wrong (a gate that raises is not a gate that fails closed; the caller sees an exception rather than a denial). Catalogue entry L4.type_confusion.

## G3 human-mode rule ignores the observer in govsim
Input: amount 25000, USD, `acct-654321`, no witness (or a forged, stale, or swapped one).
Reference: deny `observer.missing` (and the other witness reasons). govsim: hold `gate.held_for_human`; after two approvals and 60 s, allow.
Policy text: hardware_ref/policy.py says a human rule "may still set an observer threshold, checked first". govsim `make_rule` accepts `observers` and `max_risk` on a human rule, and `_cmd_request` reads witnesses only when `mode == "observer"`. The rule declares an input (observer-verdict) it never uses. The govsim text I read does not say which is intended: looks AMBIGUOUS on the docstrings alone, a hypothesis about the design, not settled. A human sees a held request whose witness never ran.

## G4 a denied request resubmitted
Input: payments.transfer 250 USD with no witness, the identical signed request submitted twice.
Reference: second answer `request.replayed` (the hash is marked seen before the decision). govsim: second answer is the first denial again (`gate.witness_missing`), because `ledger.mark` runs only on decided requests.
Policy text: neither document I read says whether a denied request id is spent. AMBIGUOUS. Consequence in the reference: a request denied for a missing witness cannot be retried once the witness arrives; the caller needs a new request id. Consequence in govsim: a denial is idempotent.

## G5 which rule's violation is reported when no rule fits
Input: `{"amount": 250, "currency": "EUR", "destination": "acct-123456"}`.
Reference: deny `constraint.currency.not_allowed` (first candidate, pay-small). govsim: deny `gate.constraint.amount.below_min` (last candidate, pay-large). Same decision, different reason.
Policy text: both docstrings say "the request takes whichever rule it fits" and neither fixes which violation is reported otherwise. AMBIGUOUS but low severity; the mapping table treats max/min and above_max/below_min as one class and still cannot reconcile this.

## Not filed as GitHub issues
The agent run does not push and has no network authority in this brief, so these are written here for the launcher or a person to file, one issue each (G1 to G5).
