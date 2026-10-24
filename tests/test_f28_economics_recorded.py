# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""F28 (external audit): false-halt and review economics as an acceptance envelope.

A shared 72-GPU halt domain turns one local false alarm into 72 GPUs of downtime; lost GPU-time grows
roughly as the square of the domain for a fixed recovery; a million benign decisions a day at a 1 percent
false-hold rate is about 167 staff-hours a day. None of this is measured. docs/18 must now carry separate
acceptance budgets (false holds, false halts, legitimate denials, recovery time, lost useful work), the
smallest-safe-failure-domain and recovery obligations, the measurements that would discharge them (a rack
trial, a staffed gateway pilot), and the statement that a zero-observed result is only a Poisson upper bound.
No doc may state a false-halt or overhead figure as measured.

These checks fail on the pre-fix docs and pass after."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _d18():
    return (DOCS / "18-viability-and-open-questions.md").read_text(encoding="utf-8").lower()


def test_docs18_carries_the_acceptance_budget_table():
    d = _d18()
    assert "acceptance envelope" in d
    # the five separate budgets
    for budget in ("false hold", "false halt", "legitimate denial", "recovery time", "lost useful work"):
        assert budget in d, budget


def test_docs18_carries_the_failure_domain_and_square_law_and_review_arithmetic():
    d = _d18()
    assert "72 gpus" in d or "72-gpu" in d
    assert "square of the domain" in d
    assert "smallest safe failure domain" in d or "smallest region" in d
    assert "167 staff-hours" in d
    assert "recovery" in d


def test_docs18_names_the_measurements_and_the_poisson_caveat():
    d = _d18()
    assert "rack trial" in d
    assert "staffed gateway pilot" in d
    assert "poisson upper bound" in d or "poisson" in d
    assert "zero observed is not zero" in d or "does not establish a zero rate" in d


def test_docs18_marks_the_figures_as_not_measured():
    d = _d18()
    # the envelope must say, in its own section, that these figures are not measurements
    assert "not a measurement" in d or "none of the figures above is a measurement" in d or "not yet measured" in d


_MEASURED = re.compile(r"(false[- ]halt rate|overhead)[^.\n]{0,60}\b(is|was|are|were)\b[^.\n]{0,40}\bmeasured\b", re.I)
_HEDGE = ("not measured", "no measurement", "not yet measured", "would be measured", "model", "target",
          "upper bound", "unmeasured", "replaces", "replace", "phase 2", "estimate", "not taken")


def test_no_doc_states_a_false_halt_or_overhead_figure_as_measured():
    for md in sorted(DOCS.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        for para in re.split(r"\n\s*\n", text):
            if _MEASURED.search(para):
                low = para.lower()
                assert any(h in low for h in _HEDGE), f"{md.name}: false-halt/overhead stated as measured without a hedge:\n{para}"
