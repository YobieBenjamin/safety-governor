# Fail-safe board interlock: a dead governor must stop its own GPU

Adversarial audit of 26 October 2026, catalog row 1 (CATASTROPHIC, server scale).

## The problem

When a governor dies, loses power or loses its LTPI link, the halt loop opens and the rest of the domain halts. But the
dead governor's own GPU keeps running: LTPI holds a dead governor's lever outputs at their last released value
(docs/interfaces/01-dcscm-dcsci-ltpi.md), and nothing else drives that slot's PERST#, PWRBRK# or PWR_EN. A chip that
must stop the process cannot rely on itself being alive to do it.

## What the board must do

The slot's power enable is held on only while the governor keeps renewing a keep-alive. The requirement:

1. A watchdog in the HPM CPLD (or the slot's power controller) holds PWR_EN for each governed slot. Its default, at
   power-up and on any fault, is off.
2. Only the governor renews the watchdog, over a dedicated sideband line the governor drives directly (not through
   LTPI, the BMC or the host). A missed renewal for longer than the watchdog period drops PWR_EN.
3. LTPI, the BMC and the host cannot override the watchdog or hold PWR_EN on.
4. Each switch port the governor opened for that GPU is closed by the switch itself when the GPU loses power (the link
   goes down), so no byte path outlives the GPU.

## What the code does now

`govsim/gpu.py` models the interlock: `board_watchdog_s` (5 s), `keepalive()` renewed by a live governor on every tick
and mailbox command, and `_board_failsafe()` that drops PWR_EN when the keep-alive lapses. Test:
`tests/test_adversarial_audit_2.py::test_a_dead_governor_leaves_its_gpu_stopped_and_its_ports_closed`. A board
without the interlock is modelled with `board_watchdog_s=None`.

## Silicon and board plan

- RTL: a keep-alive output pin on the hard core, toggled by the halt sequencer while it is in RUN or THROTTLE, and never by
  firmware alone. Add a formal property: the keep-alive stops within one period of any rung at or above HALT, and of
  loss of the core's clock.
- Board (DC-SCM / HPM): the CPLD watchdog above, specified in the governor's board requirements and in the OCP
  submission. Depends on an OEM; this is open until a board implements it.
- Stage: Board (PROBLEM-TO-SILICON-PIPELINE.md). Until then the claim is: the domain halts; the dead governor's own GPU
  stops only on a board with the interlock.
