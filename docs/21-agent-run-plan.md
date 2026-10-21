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
bash ~/safety-governor/tools/agents/launch.sh 1                 # the whole of wave 1: CLI, environments, preflight, both repositories, detached
START_AT=23:00 bash ~/safety-governor/tools/agents/launch.sh 2  # wave 2 tonight, when the day's own use is over
tail -f ~/safety-governor/.agents/wave-1/launcher.log           # or open .agents/wave-1/STATUS.md, rewritten every ten minutes
```

`launch.sh` installs the Claude CLI if it is missing and logs it in, makes a `.venv` with each repository's test dependencies (the launcher and the agents use it), finds the local model if Ollama runs on the machine (section 3b), runs the preflight, and starts `run_wave.sh <wave> --detach` in `safety-governor` and in `safety`. The pieces, for one repository or one issue:

```bash
cd ~/safety-governor && tools/agents/run_wave.sh 1 --check      # preflight only: gh, claude, pytest, the baseline tests
cd ~/safety-governor && tools/agents/run_wave.sh 1 --only L4    # one issue, in the foreground
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

## 3b. The local model

The Mac mini has a Qwen3 model of its own, and Ollama serves it through an Anthropic-compatible API, so the same Claude CLI, the same launcher, the same worktrees, allow lists, acceptance commands and pull requests run on it; only the tokens are free (`ANTHROPIC_BASE_URL` pointed at Ollama, `--model` set to the local tag; the launcher does this itself when Ollama answers, and `launch.sh` makes a 64k-context variant of the model once, since the CLI needs that much). A local model of this size is not the cloud model: the `safety` program's own record with a local model (a hallucinated API, a stubbed function, a wrong closed form, all caught by the quality gate) is the reason for the division below, which gives it only work that a test decides.

| Backend in `experiments.json` | Who does what | Issues |
|---|---|---|
| `local` | The local model does the whole issue. Work that is mechanical and fully decided by its acceptance command. | L6 (generate mutants, run the tests, record the survivors) |
| `cloud+local` | The cloud agent builds; the launcher runs the acceptance command; if it fails, the local model gets one repair pass in the same worktree against the failing output, then acceptance again; the pull request opens either way, saying which it was. | L3, L4, L5, H1, P3, C3, N1, YB-0052 to YB-0057 |
| `cloud` | Cloud only: judgment about sources, arithmetic with a paper trail, proofs on the Verilog. | L7, P2, N2 |

Two more rules keep it honest and cheap: one local run at a time on the machine (a lock shared by the two repositories' launchers, so the model never serves two agents at once), and the local pass counts only through the same acceptance command and the same reviewer as the cloud pass. When Ollama is not running, `cloud+local` runs as `cloud` and `local` issues are skipped with a note; `LOCAL_URL=cloud` puts the cheapest cloud model in the local tier instead, which is how the repair pass was tested end to end before the launcher reached the Mac (the cloud agent wrote one word, the acceptance wanted two, the stand-in fixed it in five turns for a cent).

Where the local model earns the most over the program: the repair passes (a failing test and its output is the kind of task a 27B coder handles), L6's mutant loop (hundreds of mechanical runs), and the bulk rows of the observer evaluation set once the cloud agent has pre-registered the scorer and the first rows. Where it should not be trusted: anything that becomes a number or a claim in a document without a test behind it.

## 3c. The whole program in one command, and the gates against hallucination

```bash
bash ~/safety-governor/tools/agents/run_program.sh --detach     # waves 1, 2, 3, both repositories, gates between, backups after every step
bash ~/safety-governor/tools/agents/run_program.sh --status     # where it is
bash ~/safety-governor/tools/agents/run_program.sh --from 2     # resume; it also skips whatever is already merged
```

`run_program.sh --stop` stops every instance of the program and its agents, and leaves the backup's mirror jobs and the Ollama server running; the start refuses while any instance is alive, counting every process that names the script and not only the one in the pid file (on 21 October two instances ran side by side for five hours and reviewed and revised the same pull requests twice). `run_program.sh` runs `launch.sh prepare`, then for each wave: the agents (`run_wave.sh`, in `safety-governor` and then in `safety`); then the gate on every branch the wave produced; then the audit packet; then the backup. An issue whose dependency has no merged pull request is not started, and the issue says so. An issue that already has an open pull request gets the gate, not a new agent. Nothing merges that the gate did not pass, and nothing that the gate did not pass is lost: it stays open with its review on it, for a person.

The gate is three readers that cannot agree by accident, in order of cost:

1. **The verifier** (`tools/agents/verify_pr.py`, free, deterministic). It blocks a merge when an existing test was deleted or lost assertions, when a skip or xfail marker appears, when a file outside the issue's owned paths changed, when the CI workflow changed, when an em dash was added, when the full test suite or the acceptance command fails in a clean checkout of the branch (not the agent's own worktree, which may hold untracked files). It warns on placeholder markers in code, on a result line that names a path that does not exist, and on a number added to a document that appears in no code, test, data or result file of the same branch.
2. **The second reader** (the local model, free). With no tools and the diff on its input, it lists every claim the agent made and quotes the line of the diff that is the evidence, or writes "not found". It is wrong in both directions sometimes; it is a list of things to check, handed to the next reader.
3. **The reviewer** (one bounded cloud session, read-only, `tools/agents/review_pr.sh` with `review_prompt.md`). It answers in a fixed JSON shape: a verdict, findings each with a kind, a severity, a file and a line, and the claims with where each is made and whether it is supported. The answer is then checked before it is believed: a finding that cites a file that exists neither in the diff, the checkout nor the packet marks the review untrusted, and an untrusted review never merges. An unsupported claim that reaches a document or the code blocks; one made only in the summary or a commit message is a warning.

A `revise` verdict does not wait for a person first: the findings go back to the agent that built the branch, in its own session with its context intact, in the same worktree under the same tool rules (`tools/agents/revise_pr.sh`), with the instruction to fix each finding or refute it with a file and line; then the acceptance command, a push, a comment on the pull request, and the gate again. This happens `REVISE_ROUNDS` times (two) before the pull request is left open for a person with the last review on it; the program remembers that (a `waiting-for-a-person` marker holding the branch head) and does not review the pull request again until the branch moves, and rounds already run survive a restart. The revision round is the first tier of model work moved to the local model (`REVISE_BACKEND`, auto: the local model for the first round when it answers, the cloud for the second). Wave 1 set that split: two local rounds on L4 took three and four hours, the second hit the clock with no summary, and the gate still said revise, while a cloud round is minutes and about a dollar. The local round has its own caps (`REVISE_LOCAL_TURNS` 40, `REVISE_LOCAL_TIMEOUT_MIN` 90), and a comment on the pull request says when a round ended at the limit rather than with a summary. `REVISE_BACKEND=local` keeps both rounds local; `cloud` sends both to the cloud. If local revisions start passing the gate, the first builds of the mechanical issues are the next tier to move. Work an agent leaves uncommitted when it stops is committed by the launcher as found, with a message that says so, so the gate can judge it and a revision can continue from it; nothing an agent wrote is lost.

A branch merges when the verifier is clean, the verdict is `merge`, every citation is real, CI on GitHub is green, and every dependency has merged. The merge keeps the agent's commits and their `Agent:` trailers, so the provenance of every line survives.

The first wave showed the gate doing its job: three branches came back `revise` with specific findings (a replay that could not fail meaningfully, heartbeat events the brief asked for and the trace never recorded, 21 of 87 catalogue entries compared where the brief said all, a design-ambiguity claim made without reading the policy text it was about), and one agent noticed that the briefs themselves carried a stale number: the catalogue has 75 attacks and 12 baselines, not the 66 and 10 the blog post counted before it grew. The briefs, docs/20 and the deck were corrected from `results/report.md`.

What this does and does not buy. It cannot make a model truthful. It makes an untrue statement expensive to get past: a number needs an artifact on the branch, a "passes" needs the test that the launcher and the verifier ran themselves, a review needs citations that resolve, and three independent readers (a script, a local model, a cloud model) must all fail to notice for a false claim to reach `main`. The remaining risk is a test that passes while testing the wrong thing, which is why the reviewer's second question is whether the acceptance tests what the brief says, and why `audit/PROMPT.md` exists: after the software phase, models that wrote none of this (Codex, Gemini) are pointed at the repository with that prompt, which asks them to run the tests, reproduce every number, find a change that would make each test fail, and name what the program's own disproof conditions required and it did not test. The packets they read are under `audit/wave-N/`, written by the gate, with a manifest.

The backup. After every step, `run_program.sh` refreshes `/Volumes/External_4TB/Safety Experiments` (`BACKUP_DIR`): a full mirror of each of the five repositories, Watermark included (`mirrors/<repo>.git`, the `safety` one with its recordings; the first copy of a large one runs in the background in resumable steps, history first and then the blobs in batches of 200, each batch kept once it lands, because a plain mirror clone of `safety` ran eight hours and died a few kilobytes short when the connection blinked, twice; `BACKUP.log` says `blobs still arriving` until it is whole), a browsable clone of each at `main` (`clones/<repo>`), the agents' logs and reports (`runs/<repo>/wave-N/`), the bundles, and `BACKUP.log` with the heads at each refresh. When the drive is not mounted, the step is skipped and said so; nothing waits on it.

## 4. Stop rules

An agent stops when: its acceptance command passes; or it has spent its budget; or it has failed the same test three times; or it needs a decision the brief does not make (it files the question on the issue and stops). It never widens its scope, never edits files it does not own, and never deletes a failing test to make the build green. The reviewer treats a green build with a weakened test as a failure.

The program stops, as `docs/20` section 5 says, if any experiment disproves the chip as designed: a gate disagreement that shows the policy is ambiguous; an exit that cannot be governed or bricked and that NVIDIA will not close; no affordable observer quorum for the use cases that justify the chip; overhead a buyer will not pay. Those are results, and they are the reason to do the work in software first.

## 5. After software

Design phase, same discipline, fewer agents: L7 on the Verilog, the loop re-run against a real board's parasitics once the board exists on paper, gate-level equivalence, the pre-hardware proof plan in `docs/16`. Then the FPGA with the same catalogue, hardware in the loop, and the three numbers measured. Then, and only then, the tape-out checklist in `docs/08`.
