# External audit of the experiment program: the prompt for a model that did not write any of it

This file is for a model other than the ones that did the work (Codex, Gemini, or any other), pointed at a checkout of this repository. The packets under `audit/wave-N/` hold, for every experiment of a wave: the brief the agent ran under (`*.brief.md`), what the agent said it did (`*.comment.md`), the acceptance command's output (`*.accept.log`), the deterministic verifier's result and the model review with its claims list (`review/<id>/`), and the wave's report, with a `MANIFEST.sha256` over all of it. The code and tests the packets describe are on `main`, merged through the gate described in `docs/21-agent-run-plan.md`.

Paste the text below the line into the auditing model, with this repository as its working directory.

---

You are auditing a research program that tries to prove or disprove, in software, that a separate chip beside an AI GPU can govern the actions the AI attempts. The people running it assume that every model that worked on it, including the ones that reviewed it, may have asserted things that are not shown. Your job is to find those things. You did not write any of this; do not defer to it.

Read, in this order: `docs/19-how-solid-is-the-theory.md` (what the program claims and what kind of evidence each claim needs), `docs/20-experiment-program.md` (the experiments and what would disprove each), `EXPERIMENTS.md` (the ledger of results), then `audit/wave-*/REPORT.md` and the packets.

For each experiment that the ledger marks as done or that has a merged pull request, answer with evidence from the repository, citing file and line:

1. Does the test that was accepted test what the experiment says it tests? Name the assertion that carries the claim. If the claim is "all 200 traces replay", find the loop and the count; if it is "the two gates agree on the catalogue", find the catalogue size and the assertion over it.
2. Can the test fail? Find one change to the code under test that would make it fail, or report that you could not.
3. Is every number in the ledger and in the documents computed by committed code from committed data, and does re-running that code produce it? Run it. Report the number you got.
4. Does the proof prove what the document says it proves? For each Z3 file, list the transitions modelled and the ones the design has that the model leaves out, and whether the document says so.
5. Where the review marked a claim supported, do you agree? Where it marked one unsupported, has it since been shown?
6. What did the program not test that its own disproof conditions require (docs/20 section 5)?

Rules: cite file and line for every statement; "not found" is an acceptable answer and "incorrect" is not unless you show why; run the commands rather than reading about them; do not propose fixes, only findings; end with the three findings that would most change the program's conclusion if true.
