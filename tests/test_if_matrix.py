"""The compliance matrix (docs/interfaces/COMPLIANCE-MATRIX.md): every row sourced, every evidence
file real, the Markdown in sync with the CSV. Planted faults must each be caught."""
import copy

import pytest

from govsim.hardware_ref import matrix as M
from govsim.hardware_ref.dcscm import _read


@pytest.fixture(scope="module")
def rows():
    return _read(M.CSV)


def test_committed_matrix_passes_and_is_in_sync(rows):
    assert M.check() == []
    assert M.OUT.read_text(encoding="utf-8") == M.render()


def test_every_row_has_a_source_or_says_none(rows):
    assert all(r["source"].strip() for r in rows)
    assert {r["status"] for r in rows} <= set(M.STATUSES)


def test_nda_rows_are_never_claimed(rows):
    for r in rows:
        if r["status"] == "NDA":
            assert "Not read" in r["notes"] or "not in the PDF" in r["notes"]


def one(rows, rid, **kw):
    rows = copy.deepcopy(rows)
    next(r for r in rows if r["id"] == rid).update(kw)
    return rows


@pytest.mark.parametrize("change,needle", [
    (dict(source=""), "no source"),
    (dict(source="DSP9999 1.2"), "neither a source id"),
    (dict(evidence="tests/nope.py"), "does not exist"),
    (dict(evidence="tests/test_if_spdm.py::test_that_does_not_exist"), "not found"),
    (dict(evidence="docs/interfaces/03-spdm.md"), "not a test"),
    (dict(status="compliant"), "status"),
])
def test_planted_fault_is_caught(rows, change, needle):
    errs = M.check(rows=one(rows, "SPDM-05", **change))
    assert any(needle in e for e in errs), errs


def test_nda_row_without_an_nda_source_is_caught(rows):
    errs = M.check(rows=one(rows, "NDA-01", source="HGXOCP"))
    assert any("NDA row without an NDA source" in e for e in errs)
