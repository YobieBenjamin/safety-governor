# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F24 (external audit): separate the structural, observer-accuracy and harm-reduction claims.

A structurally valid action can still be harmful, and two honest witnesses can share a mistake. Claims that
defeating dual witnesses requires compromising both keys, or that failures appear only as holds and halts
rather than misses, overstate what the structure guarantees. The docs and EXPERIMENTS.md must now state three
claims, each scoped to its own evidence: structural enforcement (proven, enforcement of a verdict not verdict
truth), observer accuracy (unquantified, needs a frozen evaluation), and end-to-end harm reduction (not
established); and a machine-checkable copy must exist. These checks fail on the pre-fix docs and pass after."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_machine_checkable_three_claim_split_exists_and_holds():
    import govsim.claims as claims
    assert claims.check()
    assert set(claims.CLAIMS) == {"structural_enforcement", "observer_accuracy", "harm_reduction"}
    assert claims.CLAIMS["structural_enforcement"]["standing"] == "proven"
    assert claims.CLAIMS["structural_enforcement"]["guarantee"] == "enforcement-of-a-verdict"
    assert claims.CLAIMS["structural_enforcement"]["not"] == "verdict-truth"
    assert claims.CLAIMS["observer_accuracy"]["standing"] == "unquantified"
    assert claims.CLAIMS["harm_reduction"]["standing"] == "not-established"


def test_docs19_carries_the_three_separated_claims():
    d = _read("docs/19-how-solid-is-the-theory.md").lower()
    # the three claims, each named with its own standing
    assert "structural enforcement" in d and "proven" in d
    assert "observer accuracy" in d and ("not quantified" in d or "unquantified" in d)
    assert "harm reduction" in d and ("not established" in d or "not established." in d)
    # structural guarantee marked as enforcement of a verdict, not verdict truth
    assert "enforcement *of* a verdict" in d or "enforcement of a verdict" in d
    assert "not the *truth* of the verdict" in d or "not the truth of the verdict" in d
    # it must point to the machine-checkable copy
    assert "govsim/claims.py" in d


def test_experiments_md_carries_the_split():
    e = _read("EXPERIMENTS.md").lower()
    assert "three claims, kept apart" in e
    assert "structural enforcement" in e and "observer accuracy" in e and "harm reduction" in e
    assert "govsim/claims.py" in e


def _paragraphs(text):
    return re.split(r"\n\s*\n", text)


HARM_CAVEAT = ("harmful", "harm", "verdict", "semantic residual", "verdict-truth", "verdict was wrong", "verdict behind it is wrong")


def _has_caveat(para):
    p = para.lower()
    return any(w in p for w in HARM_CAVEAT)


def test_holds_not_misses_claim_always_carries_the_harm_residual_caveat():
    # Any paragraph (in any doc) asserting the chip's failures are halts and holds "not misses" must carry a
    # harm-residual caveat in the same paragraph. docs/24 is the known site.
    pat = re.compile(r"(halts and holds.*not misses|not misses|holds,? not misses)", re.I | re.S)
    found = False
    for md in sorted((ROOT / "docs").glob("*.md")):
        for para in _paragraphs(md.read_text(encoding="utf-8")):
            if pat.search(para):
                found = True
                assert _has_caveat(para), f"{md.name}: 'not misses' claim without a harm-residual caveat nearby:\n{para}"
    assert found, "expected the halts-and-holds-not-misses prediction to appear in docs/24"


def test_dual_witness_claim_never_requires_compromising_both_keys_without_caveat():
    # If any paragraph ties defeating two/dual witnesses to compromising both keys, it must be stated as the
    # correlated-miss residual (a harm caveat), never as a hardness result.
    pat = re.compile(r"(dual[- ]witness|two witnesses|second witness|both witnesses).{0,200}(key|keys)", re.I | re.S)
    for md in sorted((ROOT / "docs").glob("*.md")):
        for para in _paragraphs(md.read_text(encoding="utf-8")):
            if pat.search(para):
                assert _has_caveat(para), f"{md.name}: dual-witness/keys claim without a harm-residual caveat nearby:\n{para}"
