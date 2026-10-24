# 06 · The assumptions register

Trusted hardware does not make a declared fact true. The governor compares a value it was
given against a protected rule, and the contract holds exactly as far as the value can be
trusted. Every deployment ships a register with one row per input any rule or any endpoint
relies on. The policy loader refuses an image whose rules name an input with no row
(requirement R-CONTRACT-ASSUMPTIONS-REGISTER-COMPLETE, `tests/test_h07_register.py`).

In plain words: the list taped to the wall of the security office. Who is allowed to tell us
this, how old can it be, what do we do when two people disagree, and what can we not check.

> **Plain-English version:** `10-plain-english-walkthrough.md` §11.
> **Backed by:** model `govsim/policy.py` (`check_register`: an image whose rules name an input
> with no row does not load); tests `tests/test_h07_register.py`.

## Columns

| Column | Meaning |
|---|---|
| Input | The value a rule or endpoint compares against |
| Authority | Who may assert it, under which signature |
| Freshness | Expiry, nonce or epoch; a stale value is a denial, never a pass |
| On conflict | The rule when sources disagree: denial, hold, or a stated precedence |
| Independence | Why the sources named in "authority" do not share a failure mode |
| Unchecked | What the hardware cannot establish about this input |

## The register the model ships with

| Input | Authority | Freshness | On conflict | Independence | Unchecked |
|---|---|---|---|---|---|
| GPU attestation report | The GPU vendor's device certificate chain, pinned in the policy's reference values signed by the governance root | Governor nonce per verification; result valid for one job or 1 hour | Any mismatch is a denial | Vendor chain and governance reference values are held by different parties | Side channels; physical extraction; a vendor key leak |
| Host enclave report | CPU vendor chain plus governance reference values | Nonce; 1 hour | Denial | As above | As above |
| Model manifest | Publisher key named in the policy image | Manifest version; revocation list in the policy | Denial | Publisher and governance root are different parties | Whether the weights do what the publisher says |
| Policy image | k-of-n governance keys whose hashes are in ROM | Version strictly increasing (anti-rollback); expiry | Denial; the governor halts at expiry if no new image arrives | k signers in separate custody | Whether the policy is a good policy |
| Heartbeat | The heartbeat key named in the policy | Validity window; sequence | Denial at expiry (safe mode) | The heartbeat key is not a governance key | Whether the authority itself has been coerced |
| Roster membership | Mutual attestation quotes from governors | Job lifetime | Absent from roster means refused | Each governor has its own DICE identity | A fab-level clone |
| Observer verdicts | Keys the policy anchors for the observer lane | Seconds; bound to one request hash | Missing or stale means denial | Observers run on isolated compute with their own measurement | Whether the observer is right |
| Provenance verdicts | The registry key in the policy | Seconds; bound to one request hash | Denial | The registry is a separate service | Whether a paraphrase defeated the watermark |
| Budget limits and rate windows | The policy image | Epoch | Old epoch is a denial | As for the policy | Whether the limit is the right limit |
| Protected-site list (strike endpoints) | The deconfliction authority's signed list, countersigned by the governance root | Per-entry expiry; stale is a denial | Any listed source saying "protected" wins | Deconfliction authority and governance root are different bodies | Whether the list is complete |
| Navigation fix at release (strike endpoints) | Two sources that agree within a bound, with a stated reason they are independent (satellite plus inertial, or terrain-matched) | Per-fix timestamp from the device clock | Disagreement is a denial | Different physics; different failure modes | Spoofing of both by a coordinated adversary |
| Recipient identity (payment endpoints) | Sanctions and beneficiary registries, signed | Registry version in the ticket epoch | New beneficiary is a hold | Registries run by different bodies | Whether a registry entry is correct |
| The monotonic counter | The governor's own fuse-backed counter | n/a | A counter that moves backwards is a halt | n/a | Drift against wall time |
| The log | The governor's own chain plus neighbor heads | Checkpoint cadence | A head that does not match a neighbor's record is an alarm | Neighbors are separate chips | Collusion of every neighbor and the transparency log |

## Rules of use

1. Agreement is not independence. A row that says "N sources agree" names why they do not
   share a failure mode, or it is not a valid row.
2. A novelty detector is a witness, never a guarantee against cases nobody listed.
3. The semantic residual (a harmful sentence over an allowed channel) is outside this
   register by construction. It belongs to narrow rulebooks, witnesses and human review.
4. Each endpoint names its safe transition. "Do nothing" is one option; for some devices it is
   the hazard.
5. A deployment may add rows; it may not remove the rows its rules depend on. The loader
   enforces that.
