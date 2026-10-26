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

## Plan

- Model: add a bare-metal tier where the host can write the switch, and show that the governor refuses RUN unless the
  lockdown is attested. Not done yet; open.
- Depends on NVIDIA (NVSwitch out-of-band-only mode) and on the switch vendor (Broadcom PEX lockdown). Stage: Board.
