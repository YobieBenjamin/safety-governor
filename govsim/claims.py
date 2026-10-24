# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F24: the three separated safety claims, as a machine-checkable statement.

The design makes three different claims. They must not be run together into one headline, and none may
borrow the standing of another. Each is scoped to its own evidence here, so a reviewer (or a test) can check
that the structural proof is not quietly stretched to cover observer accuracy or end-to-end harm.

    python3 -c "import govsim.claims as c; c.check()"
"""
from __future__ import annotations

# A claim may be relied on only at or below its own standing. Ordered weakest-known to strongest.
STANDING = ("not-established", "unquantified", "proven")

CLAIMS = {
    "structural_enforcement": {
        "standing": "proven",
        "guarantee": "enforcement-of-a-verdict",
        "not": "verdict-truth",
        "evidence": ["proofs/core_invariants.py", "docs/19 section 2"],
        "statement": (
            "Nothing executes without a rule, a stamp and a present witness. This is enforcement OF a verdict, "
            "not the TRUTH of the verdict: a structurally valid action can still be harmful when the verdict "
            "behind it is wrong."
        ),
    },
    "observer_accuracy": {
        "standing": "unquantified",
        "needs": "a frozen evaluation set with per-family error rates",
        "evidence": ["EXPERIMENTS.md YB-0052..YB-0057", "docs/19 section 6"],
        "statement": (
            "Whether the signed lists and observers tell allowed actions from harmful ones is not measured. "
            "Two honest witnesses can share a mistake, so defeating a dual-witness pair does not require "
            "compromising two keys, and a second witness is not a second independent key. Witness independence "
            "is itself an open measurement."
        ),
    },
    "harm_reduction": {
        "standing": "not-established",
        "evidence": [],
        "statement": (
            "That the whole stack reduces end-to-end harm is neither proven nor measured. Structural "
            "enforcement of a wrong verdict still permits the harm the verdict missed; the semantic residual "
            "is not a halt and not a hold."
        ),
    },
}


def check() -> bool:
    """Assert the split holds: exactly three claims, each with a known standing, only structural is proven,
    harm reduction is not established, observer accuracy is unquantified, and the structural guarantee is
    marked as enforcement-of-a-verdict rather than verdict-truth."""
    assert set(CLAIMS) == {"structural_enforcement", "observer_accuracy", "harm_reduction"}
    for name, c in CLAIMS.items():
        assert c["standing"] in STANDING, name
    s = CLAIMS["structural_enforcement"]
    assert s["standing"] == "proven"
    assert s["guarantee"] == "enforcement-of-a-verdict" and s["not"] == "verdict-truth"
    assert CLAIMS["observer_accuracy"]["standing"] == "unquantified"
    assert CLAIMS["harm_reduction"]["standing"] == "not-established"
    # Only the structural claim is proven; neither of the other two may be at that standing.
    assert [n for n, c in CLAIMS.items() if c["standing"] == "proven"] == ["structural_enforcement"]
    return True


if __name__ == "__main__":
    check()
    print("F24: the three-claim split holds.")
