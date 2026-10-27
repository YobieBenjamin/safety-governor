# Lever loopback sense: proving the levers reach the GPU

Adversarial audit 3, catalog row 13 (SERIOUS). GOAL.md requirements 6 ("Stop the process") and 10 ("Be mandatable").

## The problem

A governor whose PWRBRK#, PERST# and PWR_EN traces were cut on the board attested exactly like a wired one, and its GPU
ignored HALT. A regulator could not tell a bypassed governor from a working one.

## The design

The governor proves its levers before it releases the GPU and keeps proving them while it runs:

- **PWRBRK#** is pulsed (microseconds) and the GPU's own report of its hardware power brake is read back over the
  governor's private sideband (SMBPBI). A cut trace means the GPU never reports the brake.
- **PERST#** and **PWR_EN** cannot be pulsed on a running GPU, so each net loops back from the GPU connector to a sense
  input on the governor (a board requirement), and the slot's power-good is read.
- The result is in every quote (`wired.levers`), signed, so a regulator sees it remotely.
- The brake and reset levers must both be proven for RUN. A board without a slot power cut is a stated limitation that
  the quote shows; it is not a reason to refuse RUN.
- A lever that fails while running raises LEVER_UNWIRED, which blocks minting.

## What the code does now

`govsim/gpu.py` (`sense_brake`, `sense_lever_net`), `govsim/governor.py` (`lever_selftest`, `_levers_can_stop`, the RUN
gate in `_try_run`, the quote, the per-tick check). Tests: `tests/test_adversarial_audit_3.py`
(`test_cut_levers_show_in_the_quote_and_stop_minting`, `test_a_governor_with_cut_levers_never_releases_its_gpu`).

## Dependencies

- **NVIDIA:** the GPU's hardware power-brake status readable over SMBPBI by the governor's sideband (the status exists
  in NVML today; its availability on the governor's own bus is to be confirmed).
- **OEM:** loopback sense lines for PERST# and PWR_EN at the GPU connector, and the slot power-good, routed to the
  governor and not to the host.
- A cut that keeps the loopback intact but severs the GPU side (a trace cut between the sense tap and the GPU pin) is
  defeated only if the tap is at the GPU pin itself; the board specification must say so.
