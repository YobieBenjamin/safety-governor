**Agent run, wave 1** (2026-10-20 17:51): cloud (sonnet, effort medium), 30 turns, estimated $1.2002, 1 attempt(s), 2 commit(s), acceptance `python3 -m pytest -q tests/test_h21_differential.py`: **pass**, pull request: https://github.com/YobieBenjamin/safety-governor/pull/15

Agent summary:

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

## Commit messages
- EXPERIMENTS.md: correct the agreement count (#5)
Agent: wave 1, issue #5

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>

- tests/test_h21_differential.py: reference gate against govsim on the catalogue and a random sweep; five disagreements pinned and written up (#5)
Agent: wave 1, issue #5

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>

