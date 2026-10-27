# Output sealed to the egress: the host must not see a response before release

Adversarial audit of 26 October 2026, catalog row 3 (CATASTROPHIC, server scale).

## The problem

The release gate holds a response at the DPU egress until the governor mints a release ticket. But the response bytes
cross the PCIe port to the untrusted host first. A compromised host with any network path of its own (its NICs, the
BMC's NIC, GB200 NVLink-C2C) sends them without a ticket. The release gate then governs only the honest path.

## What must be true

The cleartext of a response exists only inside the GPU and inside the egress, and leaves only on a release ticket. The
host carries ciphertext.

1. The GPU encrypts what it emits to a session key shared with the egress endpoint (the DPU's egress, running inside a
   trusted execution boundary), established at attestation and bound to both attestations.
2. The egress decrypts, holds, and releases only on a valid release ticket.
3. The host's own exits (its NICs, the BMC's NIC, C2C) are in the exit register, and none of them ever carries
   cleartext of model output.

## What the code does now

`govsim/gpu.py` encrypts every emitted stream with AES-GCM under `output_seal_key` when the rack sets one, which
`govsim/cluster.py` does for every node (the egress holds the same key). Test:
`tests/test_adversarial_audit_2.py::test_model_output_reaches_the_untrusted_host_only_as_ciphertext`.

## Dependencies and plan

- NVIDIA confidential computing must let the session terminate at the egress rather than at the CPU's confidential
  VM (today it terminates at the CVM). This is an NVIDIA ask.
- The egress (DPU) must run the release check inside its own trusted boundary and attest it.
- Stage: Board and Rack. The model shows the protocol; nothing here is demonstrated on hardware.
