"""H15: production silicon has no debug path, and a tamper event leaves nothing to steal.
Falsified if a debug access succeeds in the PRODUCTION lifecycle state, or if keys survive a
tamper event."""
import pytest

from govsim import reasons
from govsim.fuses import Fuses, PRODUCTION, TEST, DECOMMISSIONED
from govsim.governor import Governor
from govsim.clock import SimClock


def test_debug_refused_in_production_and_logged(rack1):
    g = rack1.nodes[0].governor
    ok, why = g.debug_access()
    assert not ok and why == reasons.DEBUG_REFUSED
    assert g.log.has("debug.refused")


def test_debug_allowed_only_before_production():
    f = Fuses()
    g = Governor("bench", SimClock(), fuses=f)
    assert g.debug_access()[0]
    f.advance_lifecycle(PRODUCTION)
    assert not g.debug_access()[0]


def test_lifecycle_is_monotone():
    f = Fuses()
    f.advance_lifecycle(PRODUCTION)
    with pytest.raises(ValueError):
        f.advance_lifecycle(TEST)
    f.advance_lifecycle(DECOMMISSIONED)


def test_the_secret_has_no_accessor():
    f = Fuses()
    assert not any(name in ("uds", "secret", "get_uds") for name in dir(f))
    assert f.derive(b"a") != f.derive(b"b")


def test_tamper_zeroizes_and_halts(rack1):
    node = rack1.nodes[0]
    g = node.governor
    g.tamper_event("glitch")
    assert g.state == "SAFE" and not node.gpu.pwr_en
    with pytest.raises(RuntimeError):
        g.fuses.derive(b"anything")
    r = g.command("ATTEST", {"nonce": "n"})
    assert not r["ok"] and r["why"] == reasons.TAMPER_ZEROIZED


def test_firmware_rollback_refused_at_boot():
    f = Fuses()
    Governor("a", SimClock(), fuses=f, firmware_version=5)
    with pytest.raises(ValueError):
        Governor("a", SimClock(), fuses=f, firmware_version=4)


def test_modified_firmware_changes_the_key():
    f = Fuses()
    a = Governor("a", SimClock(), fuses=f, firmware_digest="aa" * 32, firmware_version=1)
    b = Governor("b", SimClock(), fuses=f, firmware_digest="bb" * 32, firmware_version=1)
    assert a.key.public != b.key.public
    assert a.device_key.public == b.device_key.public      # the DICE device identity does not depend on the firmware
