## Review of `exp/h1`: **revise**

Verifier: clean; model review on ?: 2 blocking, 5 warnings, 2 unsupported claim(s) of 12; estimated $0.40, 13 turns.

### Reviewer's summary

make lanes passes in a clean checkout, and the lanes/ checks look sound: the audit tamper checks can now fail, and every signed fixture goes through govsim. The brief's cross-repository acceptance is not met, and the notes say so honestly.
- Both patches under patches/ have hunk headers that don't match their bodies, so they are probably corrupt. The commit message calls them "applyable", and git apply --check was never run (Bash was denied here too).
- Neither the safety CI step nor the shared pin exists outside an unapplied patch. Nothing was shown to fail when a format changes in one repository.
- No code reads catalogue/attacks.json except lanes/check.py and tests/test_lanes.py. The brief wanted hardware_ref, govsim and the RTL harness to read it; instead it is exported from hardware_ref and compared against it.
- Question: does the fixture's use of sha256("audit-genesis") and the merkle root match what hardware_ref expects? verify_export accepts the audit fixture (acceptance.log), and the merkle code is only checked through the checkpoint.

### Verifier findings

- [warn] a result line names a path that does not exist on the branch: `EXPERIMENTS.md:35: tests/test_catalogue_data.py`

### Reviewer findings

- [block] correctness at `patches/safety/lanes.patch:5`: Hunk header says +1,8 but the new-file body (lines 6-15) has 10 lines. git apply will reject it as a corrupt patch, so the safety CI step cannot be applied as written. The commit message 'applyable git diffs' is unsupported: the summary and EXPERIMENTS.md say git apply --check was not run. Regenerate the patch with git diff, and run git apply --check against /Users/yb/safety.
- [block] correctness at `patches/hardware-and-silicon/lanes.patch:20`: Hunk header says +1,10 for tests/test_catalogue_data.py but the body (lines 21-31) has 11 lines. The patch is corrupt as written. The CI step on line 15 runs this test, so the hardware-side build check would never start.
- [warn] test_integrity at `EXPERIMENTS.md:17`: The brief's acceptance has three parts: make lanes, a one-line CI step for safety, and a format change in one repository failing the other's build. Only the first is shown. The CI step and the shared pin live in an unapplied patch, and the notes concede the third part was not demonstrated. Show it, for example by applying the patches to scratch clones and flipping a byte in a fixture.
- [warn] scope at `catalogue/__init__.py:1`: The docstring says load() is what govsim, hardware_ref and the RTL harness read. No code in this diff reads attacks.json except lanes/check.py and tests/test_lanes.py (the hardware patch's test reads it too, but only if the patch applies). The brief wanted the data to be the shared source, but hardware_ref is still the source, and attacks.json is a generated copy compared by export.py --check. Reword the docstring to say what is true.
- [warn] unsupported_claim at `lanes/generate.py:31`: The docstring says the Merkle root and chain are 'as hardware_ref.audit.merkle_root' and 'AuditLog does'. verify_export passing on the fixture (acceptance.log) supports the chain and the checkpoint. The tests do not compare the root independently, so the Merkle claim is only supported through the checkpoint check. Low risk.
- [warn] test_integrity at `lanes/check.py:171`: The observer check calls verify_object(m) with no expected key on the provenance, attestation, ticket and policy fixtures. That proves only that each envelope is self-consistent, not that it is anchored to the right key. The govsim checks do anchor to the key. Add the expected_pub_hex argument to the observer calls.
- [warn] unsupported_claim at `EXPERIMENTS.md:14`: The note says the pin in test_contract.py becomes a shared fixture via the patch. Because the patch is corrupt (see above), the brief's 'make the subject-hash pin a shared fixture' is not done in any applyable form. In safety, the pin is still a literal (observer/tests/test_contract.py:18).

### Claims

- supported (document): make lanes passes here, including a run of the safety observer and a live comparison of the catalogue (75 attacks, 12 baselines) with hardware_ref.attacks (evidence: acceptance.log and verify.json show exit 0 with the observer and catalogue lines; tests/test_lanes.py asserts 75 and 12)
- supported (summary): Every signed fixture (observer, provenance, attestation, ticket, policy) goes through govsim verify_object and a tampered copy of each is rejected (evidence: lanes/check.py govsim_model loop (diff lines 795-803) and acceptance.log govsim lines)
- supported (summary): The audit tamper checks now detect an edited and a deleted entry (evidence: lanes/check.py chain_ok chains each hash from the previous head (diff 703-713). Two tamper checks run it (diff 769-774). hardware_ref verify_export rejects an edit and a truncation (diff 830-835).)
- supported (document): The audit fixture chains from sha256('audit-genesis') and passes AuditLog.verify_export (evidence: hardware_ref/audit.py:172 and :226 use the same genesis; acceptance.log has 'ok hardware_ref: AuditLog.verify_export accepts the audit fixture')
- NOT SUPPORTED (commit): patches/safety/lanes.patch and patches/hardware-and-silicon/lanes.patch are applyable git diffs (evidence: Hunk headers do not match the bodies (safety lanes.yml +1,8 vs 10 lines; hardware test +1,10 vs 11 lines). git apply --check was not run.)
- NOT SUPPORTED (summary): A one-line CI step for safety runs the same checker against its observer (evidence: Exists only in the unapplied, malformed patches/safety/lanes.patch, line 15)
- NOT SUPPORTED (document): A format change in one repository fails the other's build (evidence: EXPERIMENTS.md:17 itself says this is not demonstrated)
- supported (summary): lanes/audit.py was deleted because nothing imported it and its 'byte for byte' claim was unsupported (evidence: The file is absent from the diff; the logic is in check.py chain_ok)
- supported (summary): EXPERIMENTS.md no longer names tests/test_catalogue_data.py as if it were on the branch (evidence: EXPERIMENTS.md:14 says it exists only inside the hardware patch; verify.json still warns on the path at line 35)
- supported (code): The pin in lanes/generate.py is a literal on purpose so one canonicalisation change cannot move both sides (evidence: lanes/generate.py:15-19 (the pin written out, not computed); check.py compares computed values to it)
- supported (document): govsim's envelope differs from the contract (16-hex signer, hex signature, no embedded pub) (evidence: The govsim_model adapter in check.py (diff 800) converts the signature to hex and swaps the signer. I did not read govsim/crypto.py.)
- NOT SUPPORTED (code): Catalogue is the data that hardware_ref, govsim and the RTL harness read (evidence: catalogue/__init__.py:1. No reader besides lanes/check.py, tests/test_lanes.py and the unapplied hardware patch test; hardware_ref remains the source.)

### suite in a clean checkout: exit 0

```
........................................................................ [ 35%]
........................................................................ [ 71%]
..........................................................               [100%]
202 passed in 3.03s

```

### acceptance in a clean checkout: exit 0

```
rify_export rejects an edited entry
ok    hardware_ref: AuditLog.verify_export rejects a truncation the checkpoint covers
ok    observer: public key derived from the fixture seed matches
ok    observer: canonical core bytes equal the pin
ok    observer: subject equals the pin
ok    observer: assertion carries the contract fields
ok    observer: its envelope verifies under the reference checker
ok    observer: the fixture envelope verifies under the observer's verifier
ok    observer: its verifier accepts provenance-assertion.json
ok    observer: its verifier accepts attestation-token.json
ok    observer: its verifier accepts action-ticket.json
ok    observer: its verifier accepts policy-image.json

lanes: all checks passed
python3 catalogue/export.py /Users/yb/hardware-and-silicon --check

```
