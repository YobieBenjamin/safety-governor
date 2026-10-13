# hw · from Verilog to GDS, and into the rack

This directory holds what the physical design and the integration need: the LibreLane
configuration that hardens `governor_core` on the SkyWater sky130 open process, the pinout
of the governor module, and the rack integration reference (what wires go where on the
system board and the GPU baseboard). The plan this executes is `docs/08-silicon-plan.md`.

## The flow

```
make rtl        # Amaranth -> rtl/gen/*.v   (runs here, no tools needed)
make gds        # LibreLane (Dockerized): synthesis, floorplan, place, CTS, route, DRC, LVS, GDS
```

The flow is [LibreLane](https://librelane.readthedocs.io/), the successor to OpenLane 2 (same
authors, same configuration format, maintained under the FOSSi Foundation since Efabless
closed in 2025). `make gds` needs Python and Docker; LibreLane pulls its own tool image and
the sky130 PDK (through its `ciel` PDK manager, several GB) on first run. It runs:

```
python3 -m pip install --upgrade librelane
librelane --dockerized --pdk-root ~/.ciel hw/librelane/governor_core/config.json
```

Outputs land in `hw/librelane/governor_core/runs/<timestamp>/final/`: `gds/governor_core.gds`
(the layout the shuttle takes), `lef/`, `def/`, `nl/` (the LVS netlist), `spef/`, and the
signoff reports under `reports/` (synthesis area, STA at the three corners, Magic and KLayout
DRC, Netgen LVS, antenna, IR drop). The tape-out checklist in `docs/08-silicon-plan.md` §5
reads those reports.

What is in the core at 130 nm: the monotonic counter, two measurement registers, the epoch
register, the lifecycle controller, four capability tables, the ticket store, the heartbeat,
the safe-mode sequencer, the loop I/O, the meter, the mailbox FSM and the alarm register,
with a read-only CSR window. What is not: the crypto engines, the Ibex core, the SRAM macros
and the PHYs, which are integrated from OpenTitan and the shuttle harness as described in the
silicon plan. The point of hardening the core alone first is to prove the invariants that
matter in silicon (no write path into the epoch, the levers follow the state machine, the
loop opens when it should) before anything else is on the die.

## Pinout

`pinout/governor_module.csv` lists every pin of the governor module with its group, direction,
electrical type and default state at power-on. The defaults are the safe state: brake
asserted, reset asserted, slot power enabled only when the firmware has booted and the
policy authority has spoken.

## Rack integration

`pcb/rack-integration.md` is the wiring reference for a system integrator: the
management-module connector pins the governor uses, the per-slot signals on the GPU
baseboard, the switch management buses the governor takes over, the loop and fabric
connectors between trays, and the power-on test for loop continuity.
