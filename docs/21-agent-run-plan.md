# 21. Running the program with agents: waves, budgets, and where the tokens go

The goal, in one sentence: prove or disprove the theses in software, and if the chip holds up as one layer of a multi-layer approach to AI safety, the layer paired with the GPU, carry it through design to a tape-out-ready add-on chip. This document is the execution plan for the software phase with several agents working at once, written for a budget that cannot be wasted: a monthly plan, not an open API account.

## 1. Where tokens are worth spending, and where they are not

The expensive model (the one writing this) is worth its cost for three things only: writing the briefs, reviewing a wave's pull requests against the design, and the independent audits. Everything else is build work with a clear acceptance test, and a build agent on a mid-tier model does it as well for a fraction of the allowance. Mechanical loops (compile, test, repair, re-run) should not touch the cloud at all; the `safety` repository already has the hybrid orchestrator for exactly this, routing test-and-repair to the local gpt-oss-120b on the M4 Max, which is free and fast enough (66 to 93 tokens a second).

So the rules:

1. **One brief, one agent, one branch, one pull request.** The briefs are the issue bodies in `tools/github/experiments.json`; each names the files to read first, the files it owns, the acceptance command, the disproof, and a token budget. An agent that does not finish inside its budget stops and reports; it does not keep trying.
2. **Mid-tier model for building, local model for repairing, top model for reviewing.** Build agents run on the mid-tier model (Sonnet class). Test-and-repair loops run through the local orchestrator. The top model (Fable or Opus class) reads only the diff and the test output of a finished wave, once.
3. **Tests run in CI, not in agents.** Every repository already has a CI workflow; the agent's acceptance command is what CI runs. An agent reads the CI result instead of re-running the suite in its own context.
4. **No two agents own the same file.** The waves below are arranged so that concurrent agents touch different modules. The reviewer merges in the stated order.
5. **At most two cloud agents at a time, one wave per day.** A wave fits inside one usage window with room for the review and for the day's ordinary use. If the window runs out, the launcher pauses and resumes the agents in place; nothing is lost because every agent's state is its branch and its session.
6. **No number without an artifact, no claim without a source.** The `safety` protocol applies to the whole program: a result exists when its script and output are committed.

## 2. The waves

Estimated tokens are for the build agent (input plus output), not the review. Depends-on is by issue ID.

| Wave | Issue | Repository | Builder | Est. tokens | Depends on | Owns |
|---|---|---|---|---|---|---|
| 1 | L4 trace conformance | safety-governor | cloud, mid-tier | 150k | L1, L2 (done) | `govsim/trace.py`, `proofs/replay.py`, `tests/test_h19_conformance.py` |
| 1 | L5 differential test against the reference stack | safety-governor | cloud, mid-tier | 150k | none | `tests/test_h21_differential.py`, `pyproject.toml` (one dependency) |
| 1 | H1 lanes conformance suite and the catalogue as data | safety-governor | cloud, mid-tier | 100k | none | `lanes/`, `catalogue/`, `Makefile` (one target) |
| 1 | YB-0052 observer evaluation set | safety | cloud, mid-tier, then local repair | 150k | none | `observer/bench/set.jsonl`, `observer/bench/score.py` |
| 2 | L3 widen the proofs | safety-governor | cloud, mid-tier | 120k | L4 | `proofs/budgets.py`, `approvals.py`, `buffer_classes.py`, `egress.py`, `loop.py` |
| 2 | P2 the exit register | safety-governor | cloud, mid-tier, with web | 120k | none | `docs/research/exit-register.md`, `tests/test_h20_exits.py` |
| 2 | N1 deployment overhead | safety-governor | cloud, mid-tier | 100k | none | `govsim/deploy.py`, `docs/12-deployment-overhead.md` |
| 2 | YB-0053 observer independence (code) | safety | cloud, mid-tier; run local | 80k | YB-0052 | `observer/bench/independence.py` |
| 2 | YB-0055 chip-visible vitals (code, pre-registered) | safety | cloud, mid-tier; run local | 100k | none | `algorithms/YB-0055-chip-visible-vitals/` |
| 2 | L6 mutation gate | safety-governor | local orchestrator | 60k cloud to set up | L4 | `tools/mutants/`, `results/mutants.md` |
| 2 | C3 post-quantum cost; P3 covert-channel budget | safety-governor | cloud, mid-tier (one agent, both small) | 140k | none | `govsim/bench.py` (one constant), `tests/test_h10_leakage.py` |
| 3 | YB-0054 quorum arithmetic | safety | cloud, mid-tier | 60k | YB-0052, YB-0053 | `observer/bench/quorum.py`, register rows in `safety-governor/docs/06` |
| 3 | YB-0056 verdict latency; YB-0057 use cases with the real witness | both | cloud, mid-tier, one agent with both clones | 170k | H1, YB-0052 | `observer/bench/latency.py`, `usecases.py`; `govsim/cli.py` (`--observer lanes`), `govsim/cluster.py` (effector map) |
| 3 | N2 false-halt model | safety-governor | cloud, mid-tier | 100k | none | `docs/07` section 5, `govsim/faults.py` |
| 3 | L7 formal proofs on the Verilog | safety-governor | cloud, mid-tier; solver time local | 200k | L3 | `rtl/formal/` |
| review | one review per wave, then the third audit | all | top model | about 100k per wave, 200k audit | the wave | nothing; it reads |

Total build budget for the software phase: about 1.8 million tokens on the mid-tier model, about 500 thousand on the top model for three reviews and an audit, and as much local-model time as the repair loops need, which costs electricity. Spread over three waves at one wave a day, with a day between waves for the local runs that need the recordings, the software phase is two to three weeks of calendar time, with the plan's allowance the binding constraint rather than the work.

## 3. Launching a wave

Before the first wave, a machine with nothing on it is set up by one script: it installs `gh` if it is missing, logs in to GitHub in the browser, clones the three repositories (`safety` without its recordings: a blobless, sparse clone), applies any `<repo>-N.bundle` made in the program's container, pushes, and publishes the labels and issues:

```bash
bash ~/Downloads/setup_and_publish.sh    # tools/github/setup_and_publish.sh; bundles next to it, or a directory as the argument
```

Everything an agent needs is in its issue. The launcher reads the issue body as the brief, makes a worktree on a branch named after the issue, and starts a non-interactive agent on the mid-tier model. Nobody has to watch it:

```bash
cd ~/safety-governor && tools/agents/run_wave.sh 1 --check      # preflight only: gh, claude, pytest, the baseline tests
cd ~/safety-governor && tools/agents/run_wave.sh 1 --detach     # wave 1 here (L4, L5, H1), in the background
cd ~/safety && ~/safety-governor/tools/agents/run_wave.sh 1 --detach    # YB-0052, in the sparse clone
START_AT=23:00 tools/agents/run_wave.sh 2 --detach              # wave 2 tonight, when the day's own use is over
tail -f .agents/wave-1/launcher.log                             # or open .agents/wave-1/STATUS.md, rewritten every ten minutes
```

What "unattended" means, mechanically:

- **No prompt can stall it.** The agent runs with `--permission-mode acceptEdits`, an allow list of the commands these tasks need (python, pytest, make, pip, the read-only git commands, commit), a deny list (push, checkout, reset, rebase, web access, sub-agents, `rm -rf`, sudo), and `--permission-prompts none`, so anything outside the lists is denied and the agent is told not to retry it. A denial is recorded in the run's log; nothing waits for a human.
- **Nothing runs forever.** Each attempt has a turn cap (`MAX_TURNS`, 40), an estimated-spend cap (`BUDGET_USD`, 10), and a wall-clock watchdog (`AGENT_TIMEOUT_MIN`, 120). The acceptance command gets thirty minutes.
- **The subscription window is respected, not fought.** Every request from the Claude CLI reports the five-hour and seven-day utilisation of the plan. The launcher reads it from the logs: an agent that stops because the window is exhausted is resumed, in the same session with its context intact, two minutes after the window resets (`RETRIES`, 6); and no new agent starts while the five-hour window is above `FIVE_HOUR_CEILING` (0.70) or the seven-day window above `SEVEN_DAY_CEILING` (0.85), which keeps the rest for the day's ordinary use.
- **The Mac stays awake.** The run is wrapped in `caffeinate`; `--detach` puts it under `nohup` so the terminal can be closed.
- **The result is written where it will be read.** When an agent ends, the launcher runs the acceptance command itself (free), pushes the branch, opens the pull request with the outcome in its body, comments the outcome on the issue (turns, estimated cost, attempts, acceptance, the agent's own summary) and shows a macOS notification. `STATUS.md` is rewritten every ten minutes; `REPORT.md` closes the wave with one table. The launcher never merges.
- **Preflight before any token is spent.** It checks the GitHub account, the CLI login and version, pytest, free disk, and that the repository's own tests pass on `main`, so an agent never spends its budget on a failure that was already there.

Where the tokens go, measured rather than guessed: the smoke run of the launcher (one two-turn task) cost $0.07 of API-equivalent estimate on the mid-tier model at medium effort; the Claude CLI prints this estimate for every run and the launcher records it per agent and per wave. The subscription is not billed by that figure but by its windows; the figure is still the right thing to minimise, since both scale with the same tokens. The cheapest settings that still do the work are the defaults: mid-tier model, medium effort (`EFFORT`), two agents at a time (`PARALLEL`), and briefs that name the files to read, so the agent does not read the repository to find them. Parallelism does not change the token count of a wave; it only changes how fast the window fills, which is why two, not three, is the default on a plan that is also used during the day.

For the `safety` experiments that must run on the recordings, the cloud agent writes the pre-registered code and opens the pull request; the run itself is `./mine` with the hypothesis's status flipped from `proposed` to `open`, on the machine that holds the data, under `agr/runguard.py`.

When a wave's pull requests are in and CI is green, the reviewer (top model, one session) reads `REPORT.md` and the diffs against `docs/20`, merges in the order of the table, updates `EXPERIMENTS.md` with the result lines, and files any finding as a new issue. Then the next wave.

## 4. Stop rules

An agent stops when: its acceptance command passes; or it has spent its budget; or it has failed the same test three times; or it needs a decision the brief does not make (it files the question on the issue and stops). It never widens its scope, never edits files it does not own, and never deletes a failing test to make the build green. The reviewer treats a green build with a weakened test as a failure.

The program stops, as `docs/20` section 5 says, if any experiment disproves the chip as designed: a gate disagreement that shows the policy is ambiguous; an exit that cannot be governed or bricked and that NVIDIA will not close; no affordable observer quorum for the use cases that justify the chip; overhead a buyer will not pay. Those are results, and they are the reason to do the work in software first.

## 5. After software

Design phase, same discipline, fewer agents: L7 on the Verilog, the loop re-run against a real board's parasitics once the board exists on paper, gate-level equivalence, the pre-hardware proof plan in `docs/16`. Then the FPGA with the same catalogue, hardware in the loop, and the three numbers measured. Then, and only then, the tape-out checklist in `docs/08`.
