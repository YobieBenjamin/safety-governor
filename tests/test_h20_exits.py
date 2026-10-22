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
    """For each lever row the retrofit columns must be filled and consistent: from_module is one of
    the values the brief allows, and class and undo_paths must agree. A `witness` must name what
    undoes the lever (a non-empty undo path the governor does not sit in front of); a `lock` must
    have no such undo path and a module that can actually drive it. No row is a lock today, so the
    witness branch is the one exercised; the lock branch guards a future row that claims to be a lock."""
    for r in rows():
        if r["status"] != "governed":
            continue
        assert r["from_module"] in {"yes", "no", "NDA"}, r["id"]
        assert r["class"] in {"lock", "witness"}, r["id"]
        has_undo = bool(r["undo_paths"].strip()) and r["undo_paths"] != "n/a"
        if r["class"] == "lock":
            assert r["from_module"] == "yes", f"{r['id']}: a lock needs a module that can drive it"
            assert not has_undo, f"{r['id']}: a lock must have no undo path the governor does not own"
        else:
            assert has_undo, f"{r['id']}: a witness must name what undoes the lever"


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
    """Every model exit has a register row, and the register's status is consistent with how the
    model treats the exit. A True exit must have a governed row backed by external evidence
    (VERIFIED or PARTIAL, not the governor's own design intent); the False exits are the recorded
    gaps (every row recorded-gap); the model bricks the None exits by policy, and where the register
    cannot show the brick (an NDA row) the test reports the unestablished assumption instead of
    passing it silently."""
    by_exit = {}
    for r in rows():
        by_exit.setdefault(r["model_exit"], []).append(r)
    missing = [n for n in EXITS if n not in by_exit]
    assert not missing, f"model exits with no register row: {missing}"
    unshown = []
    for name, governed in EXITS.items():
        rows_for = by_exit[name]
        statuses = [r["status"] for r in rows_for]
        if governed is True:
            gov = [r for r in rows_for if r["status"] == "governed"]
            assert gov, f"{name} is governed in the model but the register has no governed row"
            supported = [r for r in gov if "VERIFIED" in r["evidence"].upper() or "PARTIAL" in r["evidence"].upper()]
            assert supported, f"{name} is only governed by design intent: {[r['id'] for r in gov]}"
        elif governed is False:
            assert set(statuses) == {"recorded-gap"}, f"{name} rows: {statuses}"
        else:  # None: the model bricks this exit by policy
            bad = [s for s in statuses if s not in {"bricked", "unaccounted (NDA)"}]
            assert not bad, f"{name} (bricked in the model) has a forbidden status: {bad}"
            if any(s == "unaccounted (NDA)" for s in statuses):
                unshown.append(name)
    if unshown:
        warnings.warn(f"the model bricks these exits by policy but the register cannot show it: {unshown}")


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
    em_dash = chr(0x2014)
    assert em_dash not in REGISTER.read_text()
