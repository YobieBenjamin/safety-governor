"""H20: the exit register has no unaccounted row. Parses docs/research/exit-register.md.
`unaccounted (NDA)` rows are reported, not failed, until the HGX design guide is in hand."""
import re
import warnings
from collections import Counter
from pathlib import Path

from govsim.gpu import EXITS

REGISTER = Path(__file__).resolve().parent.parent / "docs" / "research" / "exit-register.md"
COLUMNS = ["id", "path", "tray", "direction", "carries", "status", "lever_or_how", "model_exit",
           "class", "from_module", "undo_paths", "evidence", "source"]
STATUSES = {"governed", "bricked", "recorded-gap", "unaccounted", "unaccounted (NDA)"}


def rows():
    out = []
    for line in REGISTER.read_text().splitlines():
        if re.match(r"\| X\d+ \|", line):
            cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
            assert len(cells) == len(COLUMNS), (cells[0], len(cells))
            out.append(dict(zip(COLUMNS, cells)))
    return out


def test_every_row_has_a_known_status_and_a_source():
    rs = rows()
    assert len(rs) >= 20
    ids = [r["id"] for r in rs]
    assert len(ids) == len(set(ids))
    for r in rs:
        assert r["status"] in STATUSES, (r["id"], r["status"])
        assert r["source"] and r["evidence"] and r["lever_or_how"], r["id"]
        assert r["tray"] in {"HGX", "NVL72", "both"}, r["id"]


def test_no_row_is_unaccounted():
    bad = [r["id"] for r in rows() if r["status"] == "unaccounted"]
    assert not bad, f"unaccounted rows: {bad}"


def test_nda_rows_are_reported_not_failed():
    nda = [r["id"] for r in rows() if r["status"] == "unaccounted (NDA)"]
    if nda:
        warnings.warn(f"{len(nda)} rows wait on the HGX design guide or a board document: {nda}")


def test_every_lever_row_answers_the_retrofit_question():
    for r in rows():
        if r["status"] != "governed":
            continue
        assert r["from_module"] in {"yes", "no", "NDA"}, r["id"]
        assert r["undo_paths"] and r["undo_paths"] != "n/a", r["id"]
        assert r["class"] in {"lock", "witness"}, r["id"]
        if r["class"] == "lock":
            assert r["from_module"] == "yes", f"{r['id']}: a lock needs a module that can drive it"


def test_nda_and_gap_rows_carry_the_retrofit_columns_too():
    for r in rows():
        if r["status"] in {"unaccounted (NDA)", "recorded-gap"}:
            assert r["from_module"] in {"no", "NDA"}, r["id"]
            assert r["class"] == "witness", r["id"]


def test_bricked_rows_say_how():
    for r in rows():
        if r["status"] == "bricked":
            assert len(r["lever_or_how"]) > 20, r["id"]


def test_register_matches_the_models_enumeration():
    """Every exit the model enumerates has a row, and the status agrees with how the model treats it
    (governed at the rack tier, a recorded gap, or bricked); a model exit that the register cannot
    settle publicly may only be an NDA row, never a silent `governed`."""
    by_exit = {}
    for r in rows():
        by_exit.setdefault(r["model_exit"], []).append(r["status"])
    for name, governed in EXITS.items():
        assert name in by_exit, f"model exit {name} has no register row"
        if governed is True:
            assert "governed" in by_exit[name], name
        elif governed is False:
            assert set(by_exit[name]) == {"recorded-gap"}, name
        else:
            assert set(by_exit[name]) <= {"bricked", "unaccounted (NDA)"}, name


def test_stated_counts_match_the_table():
    c = Counter(r["status"] for r in rows())
    text = REGISTER.read_text()
    m = re.search(r"Counts at this commit: `governed` (\d+), `recorded-gap` (\d+), `bricked` (\d+), "
                  r"`unaccounted \(NDA\)` (\d+), `unaccounted` (\d+)", text)
    assert m, "counts line missing"
    got = tuple(int(x) for x in m.groups())
    want = (c["governed"], c["recorded-gap"], c["bricked"], c["unaccounted (NDA)"], c["unaccounted"])
    assert got == want, (got, want)


def test_no_em_dashes():
    assert "—" not in REGISTER.read_text()
