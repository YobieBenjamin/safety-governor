# Host-side exits: NVLink-C2C, the host NICs and the BMC NIC

Adversarial audit 3, catalog rows 3 and 4 (CATASTROPHIC) and row 33 (CLAIM). GOAL.md requirement 4, "See every action".

## The problem

The exit register (`govsim/gpu.py` `EXITS`) named the GPU's own exits but not the host's. On a GB200 tray the Grace CPU
reaches GPU memory over NVLink-C2C, and the host's NICs and the BMC's NIC reach whatever the host holds (GPUDirect RDMA
reads GPU memory straight into a NIC). No governed switch sat on those paths. Separately, the host port on the PCIe
switch was opened with a 2^40-byte capability, so one transfer moved 10 GiB to the untrusted host against a
200,000-byte hourly output budget, and the unpresented-output check ran only afterwards, at the next tick.

## The design

- The register now names `nvlink_c2c`, `host_nic` and `bmc_nic` as host-side exits. None has a switch of its own, so all
  of them, and the PCIe host port, draw on **one host allowance**: what has been presented for signing plus a small
  in-flight slack (the output rule's `unpresented_bytes`). Presented bytes are themselves held to the output budget, so
  the host can never hold more than the budget plus one slack, whichever link the bytes use. Spreading bytes across
  C2C, the NICs and the BMC does not multiply the allowance.
- Output leaves the GPU sealed to the egress endpoint (`docs/research/output-sealed-to-egress.md`): the host holds only
  ciphertext. A board that cannot seal output has no host-side exit at all.
- The host port's inbound direction stays open (prompts, weights being loaded); only the outbound direction is bounded.
- A refusal at the host port for an exhausted allowance raises OUTPUT_UNPRESENTED and blocks output at once.

## What the code does now

`govsim/gpu.py` (`EXITS`, `HOST_SIDE_EXITS`, `transfer`), `govsim/governor.py` (`_host_out_allowance`,
`_refresh_host_out`, `open_ports_for_roster`, `_check_unpresented_output`), `govsim/endpoints.py`
(`Switch.bytes_by_direction`). Tests: `tests/test_adversarial_audit_3.py` (10 GiB refused on all four host-side exits;
one shared allowance; an unsealed board has no host-side exit), `tests/test_contract_leakage_within_budget.py`.

## In silicon, and what it depends on

- A C2C governance point the governor programs (NVIDIA: a C2C firewall or a C2C traffic meter with a governor-written
  byte budget), or a confidential-computing session from the GPU that terminates at the egress endpoint so that C2C,
  the host NICs and the BMC carry only ciphertext. **Dependency: NVIDIA.**
- The PCIe switch's capability table gains a per-direction byte budget field programmed from the output allowance, and
  meters bytes itself. **Dependency: switch vendor.**
- The host NICs under a DPU governor (the DPU's flow table is already a governed point). **Dependency: OEM.**
