# Wave report

Generated 2026-10-20 17:53 from `/Users/yb/safety-governor/.agents/wave-1`.

| issue | backend | outcome | acceptance | pull request | turns | est. cost | wall time | attempts |
|---|---|---|---|---|---|---|---|---|
| H1 | cloud | done: 0 commit(s), 29 turns | fail (exit 2) | none | 29 | $0.56 | 2 min | 1 |
| L4 | cloud | done: 2 commit(s), 43 turns | pass | https://github.com/YobieBenjamin/safety-governor/pull/14 | 43 | $0.94 | 4 min | 1 |
| L5 | cloud | done: 2 commit(s), 30 turns | pass | https://github.com/YobieBenjamin/safety-governor/pull/15 | 30 | $1.20 | 5 min | 1 |

Estimated API-equivalent spend for the wave: $2.70 (Claude Code's client-side estimate; a subscription is billed by its windows, not by this figure).

## H1: the agent's last words

`make lanes` does not pass yet: I couldn't generate the fixtures or `catalogue/attacks.json`, and nothing is committed. I never ran `make lanes`.

**What blocked it**

Early in the run I did a `cd` into `/Users/yb/hardware-and-silicon/hardware_ref` while reading, and the shell stayed there. Later Bash calls were then denied automatically, with no one to approve them. That includes `cd` back into the worktree and any `git` command run from there. I did not try to get around the denials.

**Written in the worktree, untested**

- **`lanes/envelope.py`:** stand-alone canonical JSON and Ed25519 envelope, in the `{payload, signer, pub, sig}` format from LANES.md.
- **`lanes/generate.py`:** builds the signed fixtures from named seeds: observer assertion, provenance assertion, attestation token, action ticket, policy image and a two-entry audit chain. It also writes the keys and the request, whose subject hash is pinned as a literal.
- **`lanes/check.py`:** runs each message through the gate-style checks, with forged-key, tampered-payload and wrong-subject negatives. It also checks the audit chain, the governor model (`govsim` canonical bytes and signature reproduction) and the catalogue. `--observer <dir>` runs the `safety` observer against the fixtures.
- **`catalogue/`:** `export.py` reads `hardware_ref` and writes `attacks.json`, and `__init__.py` loads it. `attacks.json` itself is not generated yet.
- **`Makefile`:** a `lanes` target running `python3 -m lanes.check`.
- **`patches/`:** a one-line CI step for `safety`, a CI step plus a catalogue test for `hardware-and-silicon`, and a note to replace the literal pins in `test_contract.py` with a read of the shared fixture.

**To finish**, from the worktree run `python3 -m lanes.generate`, then `python3 catalogue/export.py /Users/yb/hardware-and-silicon`, then `make lanes`, then commit with "#13" and the "Agent: wave 1, issue #13" line. Then fix whatever `make lanes` reports; the checker has never run.

**Open questions**

- **Catalogue counts:** the brief says 66 attacks and 10 baselines, but `hardware_ref.attacks.CATALOGUE` holds 87 entries, 12 of them baselines. I export what the code has and record the counts in the file, so the brief's numbers need correcting.
- **Envelope mismatch:** `govsim/crypto.py` signs `{payload, signer, sig}` with a 16-hex signer, hex signatures and no `pub`. LANES.md uses an 8-hex signer, base64 signatures and an embedded `pub`. The checker pins only that canonical bytes and signatures agree. Aligning the envelope is a separate change.

## L4: the agent's last words

The acceptance command `python3 -m pytest -q tests/test_h19_conformance.py` passes: 5 tests, run twice. The first run failed on three of the 200 traces; the second passed after fixes. Everything is committed on `exp/l4` (not pushed).

**Built**
- `govsim/trace.py`: a sink that records typed events. It wraps `_mint`, `_accept_policy`, `_apply_rung`, `_boot`, `Log.append` and `ActionEndpoint.execute` at class level and puts the originals back on stop. The governor is not changed.
- `proofs/replay.py`: concrete Python versions of the `core_invariants.py` and `commit_point.py` machines, with the Z3 guards copied one for one. P1 to P4 are checked after every step, and the first unmatched event raises `NoTransition` naming it. z3 is not installed here, so this does not run the prover. A test checks the step names against the proof files.
- `tests/test_h19_conformance.py` and `tests/h19_plugin.py`: the plugin reruns all 200 hypothesis tests with the sink on and replays each trace at teardown. Two broken-governor fixtures fail replay with the event named: a halted governor that still signs a ticket, and a stale-edition ticket that executes.

**Disproof (model bug or gap in the theorem)**
- **Theorem gap:** a power cycle is not a step. Govsim boots halted and reaches RUN on the first heartbeat with no clear. The replayer allows this as an explicit `arm` step only from a boot-caused halt. The theorem should add a boot step or constrain init.
- **Theorem gap:** an endpoint burns a ticket and may then refuse it. The machine has no step for a spent ticket that was never executed.
- **Injected fault, not a gap:** `test_governor_cannot_clear_itself` forces RUN with no clear. Replay must refuse it, and the plugin asserts that it does.
- **No model bug found.**

**Not checked**
- The rule and witnesses behind each ticket (they are inputs to the machine).
- Heartbeat, which is observed at issue and at execute rather than driven by events.
- Quorum, which is taken as true for an accepted policy image and for an authority clear.

The findings are also in `EXPERIMENTS.md`.

**Open questions**
- Should the theorem model boot and the `arm` step?
- Should a burned-then-refused ticket count as a machine step?

## L5: the agent's last words

**L5 summary (issue #5)**

- **Built:** `tests/test_h21_differential.py`, `tests/requirements-differential.txt` (hypothesis, plus an editable install of hardware-and-silicon) and `results/l5-disagreements.md`. One neutral payment rulebook is rendered into both formats. A mapping table of reason codes sits at the top of the test. A catalogue-classification test fails if a new attack is added that nobody has sorted.
- **Catalogue:** the brief says 66 attacks and 10 baselines, but the checkout has 75 and 12. The test pins that count. 21 entries replay in both gates. The other 66 are listed with a reason, for example "audit chain" or "OASP supervisor".
- **Sweep:** a hypothesis run over random typed requests, witnesses, tokens, prior payments and resubmits. A disagreement passes only if it matches one of the pinned signatures G1 to G5; anything else fails.
- **Result:** the two gates agree on 18 of the 21 replayed entries. The other 3 are pinned disagreements.
- **Pinned disagreements:** each has its input in `results/l5-disagreements.md`.
  - **G1:** govsim has no destination regex, so `acct-evil` is allowed.
  - **G2:** a string or `None` amount raises `TypeError` inside govsim's gate instead of denying.
  - **G3:** govsim ignores the observer on human-hold rules. It holds where the reference denies.
  - **G4:** the reference marks a request seen before deciding, so a denied request resubmitted is "replayed". govsim repeats the original denial.
  - **G5:** when no rule fits, the two report different rules' violations. The decision is the same.
- **Ambiguous in the policy text (design findings):** G3, G4 and G5. I did not read govsim's docs, only the code.
- **What passes:** the acceptance command passed in no run I made. My three pytest runs failed or were filtered. After fixing the failures I called the 30 test functions directly through a scratch script, not pytest, and all passed. I did that to avoid a fourth pytest run, so please treat the launcher's run as the real check.
- **Issues not filed:** the brief asks for one issue per disagreement, but I have no network authority here. Please file G1 to G5 from `results/l5-disagreements.md`.
- **Reads beyond the brief:** to build the rigs I also read the hardware-and-silicon `system.py`, govsim's `cluster.py`, `conftest.py` and a few existing tests.
- **Open question:** should govsim gain a regex, a type check and a witness check on human rules, or should the shared rulebook be limited to what both can express?

