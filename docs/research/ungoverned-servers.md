# Finding servers sold without a governor

Adversarial audit 3, catalog row 22 (SERIOUS). GOAL.md requirement 10 ("Be mandatable").

## The problem

Endpoints refuse unticketed actions, so a governed endpoint cannot be driven by an ungoverned server. But nothing finds
the ungoverned server itself: a server sold or built without a governor, or with the governor removed, can still run
models and act through endpoints that are not governed.

## What the chip can and cannot do

The chip can prove its own presence (attested quotes, lever self-test in the quote, compliance reports). It cannot
prove another machine's absence. Detection is a registry and audit protocol outside the chip:

- Every governed endpoint class (payment switches, strike guidance, messaging gateways, egress at data-center borders)
  accepts only tickets from governors whose device certificates chain to an enrolled vendor and whose quotes are
  current. An ungoverned server can reach only ungoverned endpoints.
- Vendors report every AI accelerator shipped; operators report every server installed with its governor's device
  certificate; a regulator reconciles the two and audits the difference. The governor's periodic signed compliance
  report is the "present and working" half of that reconciliation.

## Status

Design obligation on the regulator and on vendors. No chip or model change closes it; it is recorded here so that no
claim says otherwise.
