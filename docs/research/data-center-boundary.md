# The boundary is the data center: heartbeats, HALTs and stragglers

Adversarial audit 3, catalog rows 6 (CATASTROPHIC), 9, 10 (SERIOUS) and 35 to 37 (CLAIM). GOAL.md: the chip is the
guard and the STOP for its server, its rack and the governed servers of its data center; it is not a global kill switch.

## Heartbeat signers belong to one data center (row 6)

Every governor fails closed when its heartbeat stops. Audit 3 pointed out that whoever holds the heartbeat signers
therefore holds an off switch for every governor that trusts them, and the "no kill switch" argument did not count it.

Now every edition names its `site` (the data center), every heartbeat names the site it is for, and a governor accepts
only its own site's heartbeats. Racks of one site share that site's 2-of-3 heartbeat signers; racks of another site have
their own. Silence, loss or capture of one site's signers stops that site and nothing else.
Tests: `test_one_sites_silent_heartbeat_signers_stop_only_that_site`, `test_a_heartbeat_signed_for_another_site_is_refused`.

The auditor's own test (`test_withholding_one_authoritys_heartbeat_does_not_stop_a_whole_fleet`) advances the clock
with no heartbeat delivered to any rack at all. In the model each rack already had its own signers, so that test
measures "every authority silent", and the correct behaviour then is that every governed GPU stops: fail closed inside
each site. It stays failing as written; the faithful test is the one above.

## A HALT does not depend on the target's host (row 9)

A targeted HALT used to reach its governor only through that governor's host mailbox. Now any governor that receives a
valid authority HALT for another chip (2-of-3 authority signatures, the halt type, not expired) relays it over the
fabric, and the named chip applies it with all of its own mailbox checks. Test:
`test_a_halt_the_targets_host_drops_still_reaches_it_over_the_fabric`. The auditor's test creates the signed HALT and
never sends it anywhere; no design can act on a message nobody sends, so that test stays failing as written.

## Stragglers stop at once (row 10)

A governor that missed a rule change used to keep minting under the old rules until its heartbeat expired. Now (a) a
quorum-signed heartbeat for an epoch the chip does not hold sends it straight to HALT as EPOCH_STRAGGLER, and (b) the
authority installs the committed edition on every endpoint directly, including each node's egress, so a straggler's
own endpoints refuse its old-epoch tickets. Endpoints refuse epoch statements for an older edition (row 27).
Tests: `test_a_straggler_on_old_rules_cannot_release_after_the_commit`,
`test_a_straggler_halts_at_the_first_heartbeat_of_the_new_epoch`, `test_an_endpoint_refuses_a_replayed_older_epoch`.

## In silicon

The site identifier is fused or set in the first edition and bound into the heartbeat check in the hard core. The
fabric HALT message is decoded in the hard-core path, not only in firmware (the RTL change is tracked with the other
hard-core rows).
