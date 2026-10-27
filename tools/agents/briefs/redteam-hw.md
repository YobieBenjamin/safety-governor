# Brief: hardware red team on our own governor (runs only under the Cyber Verification Program)

You are testing the Safety Governor, a hardware security chip this project designs, owns and publishes. Every
target is ours: the Amaranth RTL and generated Verilog (`rtl/`), the governor model (`govsim/`), the reference stack
(`../hardware-and-silicon/hardware_ref/`), the FPGA bench design (`hw/fpga/`). Nothing outside this repository and its
simulators is in scope: no third-party systems, no network targets, no real devices other than our own FPGA board if
one is attached.

Goal: find ways the governor's protections can be bypassed, so they can be fixed before silicon. The existing
conformance suite (`rtl/conformance`) checks the chip against its spec; your job is the adversarial complement:
assume the spec is incomplete and look for what it misses.

Areas, in priority order:
1. The mailbox and the signed-command path: ordering, replay across reset, the window between doorbell and verdict
   (open findings RTL-RESET-ZEROES-MAILBOX-SEQUENCES, RTL-MAILBOX-FRAME-NOT-HELD in `rtl/formal/FINDINGS-a.md`), command-type confusion.
2. The halt sequencer and loop: races between strobes in one cycle, reset sequencing, boot-window behaviour, EXCLUDE.
3. The origin gate (`govsim/sealing.py`, KEY_RELEASE, KEY_RENEW): lease handling, revocation, key-box binding.
4. The SMBus target and the CSR window: anything a host on the management bus can do beyond reading and the doorbell.
5. The FPGA bench: anything the firmware stand-in chain exposes that the real chip would not.

Rules (the same discipline as the rest of the program, docs/26):
- Every finding needs a reproducer that fails by assertion on the current code, in a test file under
  `tests/redteam/` or `rtl/redteam/`. A tool error is not a finding.
- Record each finding in `audit/redteam-<date>/FINDINGS.md`: what, how severe, the reproducer, the suggested fix.
  Do not fix the RTL yourself; the fix gets its own branch and regression.
- Negative results count: list what you tried that held.
- Plain English summary with an analogy per finding in `audit/redteam-<date>/PLAIN-ENGLISH.md`. No em dashes.
- Work on the branch you are given. Commit with the project's author and trailer conventions. Never push.
