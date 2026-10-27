# Switch management lockdown: the host must not reprogram the switches

Adversarial audit of 26 October 2026, catalog rows 2 and 36 (CATASTROPHIC and CLAIM, server scale).

## The problem

The governor's port authority assumes it is the only master of the NVSwitch and PCIe switch management paths. On a
bare-metal HGX host today, root reprograms NVSwitch routing and PCIe switch ports in band
(docs/research/nvswitch-management.md). The model said "There is no host write path"; that sentence has been corrected
in `govsim/endpoints.py`.

## What the board and firmware must do

1. NVSwitch: management only out of band, from the governor (or an NVOS instance the governor measures and gates), with
   the in-band (host PCIe) configuration path disabled by strap or fuse in production.
2. PCIe switches: configuration space and the management endpoint locked against the host (configuration lockdown
   after the governor programs the ports; the switch's EEPROM image measured by the governor at boot).
3. The governor refuses to enter RUN unless it has verified both: the lockdown is set, and the measured firmware of each
   switch is on the reference list (see catalog row 16).

## What the code does now (adversarial audit 3, catalog row 5)

- Every governed switch in the model now has the host's in-band write path: `Switch.host_write` opens an entry with no
  governor capability whenever the switch is not locked (`locked` False, today's bare metal).
- The governor reads each switch's lock state and firmware digest over its own sideband (`lock_report`). It refuses
  RUN while any governed switch is unlocked, raises SWITCH_UNLOCKED (which blocks minting), and a switch that becomes
  unlocked while running stops the GPU (HALT).
- Tests: `tests/test_adversarial_audit_3.py` (`test_a_governor_will_not_run_behind_an_unlocked_switch`,
  `test_a_switch_unlocked_while_running_stops_the_gpu`, `test_a_locked_switch_refuses_host_writes`).

## Still open

- The firmware digest is reported but not yet compared with a reference list in the edition (catalog row 16 of
  audit 2). Next fix.
- Depends on NVIDIA (NVSwitch out-of-band-only mode) and on the switch vendor (Broadcom PEX lockdown). Stage: Board.
