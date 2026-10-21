**Revision 2** (2026-10-21 12:19) on sonnet: 5 turns, estimated $1.0857, acceptance `make lanes`: **pass**. The gate reviews the branch again.

Agent summary:

Revision 2 is committed on `exp/h1`, and `make lanes` passes after the last commit. I ran it once this revision and haven't pushed.

**Fixed**
- **`lanes/audit.py`:** I deleted it. Nothing imported it, and its "mirrors `hardware_ref` byte for byte" claim was unsupported. The audit chain logic now lives in `chain_ok` in `lanes/check.py`.
- **`lanes/check.py` audit tamper check:** the old edit check compared a hash that never included the previous head, so it could not fail. I replaced it with two checks that run the chain verifier on a copy with an entry edited and on a copy with an entry deleted. Both are detected.
- **govsim coverage:** all five signed fixtures (observer, provenance, attestation, ticket, policy) now go through govsim's `verify_object` via an adapter, and a tampered copy of each is rejected. The check now makes 54 `ok` lines without `--hardware`.
- **Notes:** `EXPERIMENTS.md` no longer names `tests/test_catalogue_data.py` as if it were on the branch; it says that file exists only inside the hardware patch.
- **CI step:** the safety workflow's CI step is now one `run:` line.

**Not changed**
- **Cross-repository failure:** a format change in one repository failing the other's build is still not demonstrated. It needs the patches applied and this branch merged, because the workflows clone `main`. The notes say so. `git apply --check` was not run, because shell approvals were denied.
- **Shared pin in `safety`:** the pin in `safety`'s `test_contract.py` stays a literal until `patches/safety/lanes.patch` is applied. The pin in `lanes/generate.py` stays a literal on purpose, so one canonicalisation change cannot move both sides.
- **Catalogue readers:** `govsim` has no catalogue code, and `hardware_ref` can't be edited from here, so `attacks.json` is exported from and compared against `hardware_ref`, not read by it.
- **`AuditLog.verify_export` coverage:** it runs under `make lanes`, but not under `tests/test_lanes.py`. A test that skips when the repository is missing would break the no-skipping rule.
- **govsim envelope shape:** the difference in envelope shape between govsim and the contract remains a recorded gap, not a native check.

**Open question:** on your question, should `safety-governor` get its own CI step that runs `make lanes` against both repositories? I haven't added one, because it needs sibling clones.

## Commit messages
- lanes: audit tamper checks that can fail, every signed fixture through govsim, dead audit.py removed, notes and one-line CI step corrected (#13)
Agent: wave 1, issue #13 (revision 2)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>

- Revision 1: work left uncommitted by the agent, committed by the launcher (#13)
Agent: wave 1, issue #13 (revision 1, launcher commit)

- patches: applyable git diffs for safety and hardware-and-silicon (CI workflow, shared pin, catalogue test); notes corrected (#13)
Agent: wave 1, issue #13 (revision 2)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>

- lanes: audit fixture chains from the reference genesis and is run through AuditLog.verify_export; scratch script removed; make lanes fails when a repository is missing (#13)
Agent: wave 1, issue #13 (revision 2)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>

- Revision 1: work left uncommitted by the agent, committed by the launcher (#13)
Agent: wave 1, issue #13 (revision 1, launcher commit)

- lanes: signed fixtures, conformance checker, catalogue as data, make lanes (#13)
Agent: wave 1, issue #13

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>

