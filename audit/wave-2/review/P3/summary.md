**Revision 2** (2026-10-22 12:11) on sonnet: 8 turns, estimated $0.6718, acceptance `python3 -m pytest -q tests/test_covert_budget.py`: **pass**. The gate reviews the branch again.

Agent summary:

Revision 2 is committed as 134c4f0. `tests/test_covert_budget.py` now has 10 tests and passes, and I ran the acceptance command once. I also ran `tests/test_h10_leakage.py` and the full suite was not run.

**What changed**
- **Em dashes:** I removed all six, in `docs/05-threat-model.md` and `tests/test_covert_budget.py`.
- **Disproof claim:** `docs/05-threat-model.md` no longer says the disproof condition is "not met". It now says it is not shown to be unmet. The 208,078 B/h figure is labelled as the bound for the modelled channels only. The doc names the unbounded channels in the default image: the `message.send.listed` body (auto-mode, no length limit, no rate), recipient choice, and a payment's amount and destination. It says the design cannot yet claim budgets alone defend against exfiltration in practical time. The new `test_unmodelled_channels_are_still_open` fails when any of these gains a limit.
- **Tightest policy:** I dropped the claim that 208,078 upper-bounds the tightest serviceable bound. The doc now says the model does not search for a tighter image.
- **Practical time:** one year is now stated as an explicit assumption with no external source, fixed before the rate was computed.
- **Policy-change test:** `test_every_budget_term_a_policy_change_can_raise_raises_the_figure` loosens the payments rate and the output window and checks the figure rises. It also checks that the unpresented slack changes the reported burst but not the hourly figure.
- **Burst claim:** `test_burst_before_the_alarm_is_one_time` now runs a further tick and a full 3,601 s window with a heartbeat. The alarm and the output block both persist. The doc says this holds unless a rule or approver key clears the alarm.
- **`tests/test_h10_leakage.py`:** it does exist, and my earlier summary was wrong to say it didn't. I added one test pinning that its 50 queries, 200,000 bytes and 3,600 s window are the budget the covert model reads.

**Not changed**
- **Channels:** I did not bound the message-body, recipient-choice, amount or destination channels. They need endpoint-schema limits that belong to another brief, so they stay as a documented open gap pinned by a test.
- **Tighter image:** I did not search for a tighter serviceable image, so the figure stays the default image's.
- **Payments peer term:** I kept the "no peer term for payments" statement. Payments go to the `payment-switch` endpoint (`govsim/cluster.py:136`), not to a rack peer.

## Commit messages
- P3 (#9): reword the disproof as not shown (open channels pinned), widen the policy-change and burst tests, extend test_h10, remove em dashes
Agent: wave 2, issue #9 (revision 2)

- P3 (#9) rev 1: pin every figure, drop the spurious peer term, result-independent practical-time horizon
- Drop the "choice among peers" channel: payments go to the payment-switch
  endpoint, not a rack peer, so peer_bits had no peer-addressed traffic. The
  total falls from 209,266 to 208,078 B/h; pin moves to 208,100.
- Practical time is now a fixed one-year horizon (PRACTICAL_HOURS), stated as a
  threat property and not derived from the rate; the disproof test asserts the
  weights take longer than it (77 y / 545,000 y), so the threshold cannot be
  tuned to the number. The 10x/"one year" disagreement is gone.
- Ground "serviceable" with test_default_image_serves_a_response; the doc no
  longer claims the default is the tightest serviceable image, only that its
  bound upper-bounds it.
- "leaves in days" replaced with sizes and the division: a 100 MB delta in ~20
  days, a 1 GB student in ~200 days, both pinned.
- Pin every component figure (content 200,000; timing 63,743 + 875 bits; length
  654; the 50/200,000/100-per-60s/amount-cap policy values) so a component can
  not drift without failing.
- The 1 MiB burst is read as the policy's unpresented_bytes slack and the doc
  says "the excess tolerated" rather than "the burst is 1 MiB".
- Name the unmodelled channels (message body, payment amount/destination) that
  could dominate the figure, as the brief asks.

Co-Authored-By: Claude Code <noreply@anthropic.com>
Agent: wave 2, issue #9 (revision 1)

- P3 (#9): covert-channel budget model, pinned at 209,300 B/h, stated in the threat model
Agent: wave 2, issue #9

