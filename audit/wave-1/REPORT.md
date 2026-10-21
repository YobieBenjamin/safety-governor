# Wave report

Generated 2026-10-20 19:09 from `/Users/yb/safety-governor/.agents/wave-1`.

| issue | backend | outcome | acceptance | pull request | turns | est. cost | wall time | attempts |
|---|---|---|---|---|---|---|---|---|
| H1 | cloud+local | done: 1 commit(s), 10 turns | pass | https://github.com/YobieBenjamin/safety-governor/pull/17 | 10 | $0.23 | 0 min | 1 |
| L4 | cloud+local | done: 2 commit(s), 3 turns | pass | https://github.com/YobieBenjamin/safety-governor/pull/14 | 3 | $0.13 | 0 min | 1 |
| L5 | cloud+local | done: 3 commit(s), 15 turns | pass | https://github.com/YobieBenjamin/safety-governor/pull/15 | 15 | $0.34 | 0 min | 1 |

Estimated API-equivalent spend for the wave: $0.69 (Claude Code's client-side estimate; a subscription is billed by its windows, not by this figure).

## H1: the agent's last words

`make lanes` passes here, on its first run. Everything is committed on `exp/h1` as 68b4742, and I haven't pushed.

- **Fixtures:** `lanes/fixtures/` holds the six signed messages (observer assertion, provenance assertion, attestation token, action ticket, audit record, policy image), the fixture keys and the pinned request. `python3 -m lanes.generate` rebuilds them. The signing is deterministic, so any drift in the committed files fails the check.
- **Checker:** `python3 -m lanes.check [--observer DIR]` runs the checks on the fixtures. Examples are forged key, tampered payload, wrong signer, stale expiry, subject mismatch, and audit chain breakage. It then runs `govsim` and, with `--observer`, the real `safety` observer.
- **Subject-hash pin:** the pin from `test_contract.py` is now a fixture, `request.json`. The literals are written out, not computed, so a change to canonicalisation can't move both sides at once.
- **Catalogue:** `catalogue/attacks.json` has 87 entries (75 attacks, 12 baselines), and `catalogue.load()` and `catalogue.names()` read it. `catalogue/export.py <hardware repo> --check` compares it with `hardware_ref.attacks`.
- **Make target and tests:** `make lanes` runs the checker with the `safety` observer, then the live catalogue comparison. `tests/test_lanes.py` is new, and I only ran that file.
- **Patches, not applied:** `patches/hardware-and-silicon/lanes-ci.patch` adds a CI step and a catalogue test to that repository. `patches/safety/ci-lanes.patch` adds the one-step CI for the `safety` observer. Both repositories were read-only for this run.
- **Still to do in `safety`:** `test_contract.py` should read `lanes/fixtures/request.json` instead of its own literals. That edit is only described in the patch note. Until it's made, "a format change in one repository fails the other's build" holds only once the CI patches are applied.
- **Known gap:** `govsim`'s envelope differs from the contract (16-hex signer, hex signature, no embedded public key). The checker pins only the canonical bytes, the digest and the deterministic signature. The gap is recorded in `EXPERIMENTS.md`.
- **Open:** `govsim` and `hardware_ref` don't read `catalogue/attacks.json` yet. Is that for a later wave? The CI patches clone `safety-governor` from GitHub, so the fixtures must be pushed before they can pass.

## L4: the agent's last words

`python3 -m pytest -q tests/test_h19_conformance.py` passes. I ran it once and have not run the full 200-test suite. All the work was already committed on `exp/l4` (#4), so I changed nothing this run.

**What exists**
- `govsim/trace.py` is a trace sink beside the existing log. It records tickets with action hash and edition, executes, refusals with reason, edition changes, halt, clear, and heartbeat events.
- `proofs/replay.py` drives the `core_invariants.py` machine and raises on the first event with no enabled transition.
- `tests/test_h19_conformance.py` reruns the H0 to H18 tests with the sink on and replays each trace.
- Two broken-governor fixtures fail replay with the event named. One is a halted governor that signs, the other a stale-edition ticket that executes. A third case injects RUN with no clear. Replay refuses it, and the plugin lists it in `FAULT_INJECTION` and asserts the refusal.

**Disproof result**
The simulation takes steps the abstract machine lacks. Both are gaps in the theorem, not model bugs:
1. **Boot is not a step.** `core_invariants.py` leaves `halted` free in the initial state. govsim boots into HALTED_INITIAL and reaches RUN on the first heartbeat with no clear. The replayer accepts this as an explicit `arm` step, only from a halt that a boot put there. The theorem should add a boot step or constrain init.
2. **Burn without execute is not a step.** An endpoint burns a ticket before the governor commit and device checks, then may refuse. The machine has no step for a used ticket that never executed. The replayer tracks it as `burned`.

**Not checked by replay**
- Refusals for expiry, wrong endpoint, parameter mismatch and bad signature replay as stutter steps of `forged execute`. The machine is looser than the system there, which is sound.
- `allows` and `witness` are inputs to the machine, so replay does not check that the rule and witnesses were right.
- Heartbeat is observed, not driven by explicit events.
- `quorum` is taken as true for an accepted policy image and for an authority clear.
- z3 is not installed, so replay runs the guards on concrete values copied from the Z3 steps. A test checks the step names against the proof files, but the prover itself does not run.

**Open questions**
- Should the theorem gain boot and burn steps, or should govsim change? I recommend the theorem.
- The L4 row in the `EXPERIMENTS.md` table still says "open"; the launcher or you may want to flip it.

Agent: wave 1, issue #4

## L5: the agent's last words

The acceptance command passes: `python3 -m pytest -q tests/test_h21_differential.py` gave 30 passed on its one run. I wrote no new test, because `tests/test_h21_differential.py` already existed from the earlier work on issue #5.

- **What the test does:** it renders one rulebook into both formats and feeds identical requests, witnesses and tokens to `hardware_ref.gate` and to govsim's governor. It compares allow, deny or hold and the reason codes through a visible mapping table. It also runs a hypothesis sweep over random typed requests.
- **Catalogue coverage:** only 21 of the 87 catalogue entries are replayed in both gates, and the two gates agree on 18 of them. The other entries are not gate decisions in govsim (silicon, audit chains, endpoints, provenance, OASP supervisor). They are listed in `NOT_COMPARED` with reasons, and a test fails if the catalogue grows an entry nobody has classified. This is narrower than the brief's "whole catalogue".
- **Disagreements:** five are pinned as G1 to G5, with their inputs, in `results/l5-disagreements.md`. A pinned gap that stops disagreeing fails the test, so a fix can't go unnoticed. G3, G4 and G5 are cases where the policy text doesn't say which gate is right, which is the design finding the disproof clause describes.
- **Issues not filed:** I did not file them as separate GitHub issues, because the sandbox denied `gh`. That step is still open.
- **My change:** I appended a dated note to `EXPERIMENTS.md` recording the pass and the unfiled issues, and committed it as 450ba92. I did not push.
- **Blocked commands:** two Bash calls were denied for brace expansion and a chained command. I fell back to the Read and Grep tools.
- **Not done:** I read govsim's `policy.py` and `reasons.py` only through the existing test and did not re-derive the mapping table. I made no patches to other repositories.

Open question: should G3 to G5 be settled in `docs/LANES.md` or in the govsim and reference-gate policy text? Both gates currently satisfy the text as written.

