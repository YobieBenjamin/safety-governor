"""OCP DC-SCM 2.x, DC-SCI and LTPI (docs/interfaces/01-dcscm-dcsci-ltpi.md).

The mapping checker must pass on the committed CSV, and each planted fault must trip exactly the
rule it breaks (by its code), so a pass is not a checker that says yes to everything.
"""
import copy

import pytest

from govsim.hardware_ref import dcscm as D


@pytest.fixture(scope="module")
def base():
    return D._read(D.MAPPING)


def codes(mapping):
    return {e.code for e in D.check_mapping(mapping=mapping)}


def test_committed_mapping_passes(base):
    errs = D.check_mapping()
    assert errs == [], [str(e) for e in errs]


def test_every_governor_pin_has_a_row(base):
    gov = D.expand_governor_signals(D._read(D.GOV_PINOUT))
    mapped = {(r["governor_signal"], r["instance"]) for r in base}
    assert gov <= mapped and len(gov) == 85


def test_no_public_home_is_flagged_not_hidden(base):
    homeless = set(D.no_public_home(base))
    assert homeless == {"PEX_MDIO", "PEX_MDC", "DPU_OOB_TX", "DPU_OOB_RX"}


def edit(rows, sig, inst="", **kw):
    rows = copy.deepcopy(rows)
    for r in rows:
        if r["governor_signal"] == sig and r["instance"] == inst:
            r.update(kw)
            return rows
    raise KeyError(sig)


@pytest.mark.parametrize("mutate,code", [
    (lambda b: edit(b, "SMB_HOST_SDA", dcsci_pin="A17", dcsci_function="I2C_3V3_1_SCL"), "PIN_REUSED"),
    (lambda b: edit(b, "NVSW_SMB_SCL", translator=""), "VOLTAGE"),
    (lambda b: edit(b, "TAMPER_IN", gov_dir="out"), "DIRECTION"),
    (lambda b: edit(b, "SMB_HOST_SCL", dcsci_function="I2C_3V3_2_SCL"), "FUNC_NOT_ON_PIN"),
    (lambda b: edit(b, "SMB_HOST_SCL", dcsci_pin="A99"), "PIN_NOT_PUBLIC"),
    (lambda b: [r for r in b if not (r["governor_signal"] == "PERST_N" and r["instance"] == "slot3")], "LEVER_MISSING"),
    (lambda b: [r for r in b if not (r["governor_signal"] == "PERST_N" and r["instance"] == "slot3")], "UNMAPPED"),
    (lambda b: edit(b, "PWR_EN", "slot2", fail_safe=""), "LEVER_NO_FAILSAFE"),
    (lambda b: edit(b, "PWR_EN", "slot2", fail_safe="REQ-NOT-WRITTEN-DOWN"), "LEVER_NO_FAILSAFE"),
    (lambda b: edit(b, "PWRBRK_N", "slot1", ltpi_channel="LTPI2:NL_GPIO_SCM_HPM[12]"), "LTPI_LATENCY"),
    (lambda b: edit(b, "PERST_N", "slot1", ltpi_channel="LTPI2:LL_GPIO_SCM_HPM[0]"), "LTPI_REUSED"),
    (lambda b: edit(b, "PERST_N", "slot1", ltpi_channel="LTPI2:LL_GPIO_SCM_HPM[16]"), "LTPI_FRAME"),
    (lambda b: edit(b, "PERST_N", "slot1", ltpi_channel="LTPI2:LL_GPIO_HPM_SCM[9]"), "DIRECTION"),
    (lambda b: edit(b, "PEX_MDIO", status="designed"), "NO_HOME_UNFLAGGED"),
    (lambda b: edit(b, "SMB_HOST_SCL", spec_ref="DC-SCM somewhere"), "NO_SOURCE"),
    (lambda b: edit(b, "SMB_HOST_SCL", spec_ref=""), "NO_SOURCE"),
    (lambda b: b + [dict(b[0], governor_signal="GPU_MAGIC_WIRE")], "UNKNOWN_SIGNAL"),
    (lambda b: b + [dict(b[-1])], "DUP_SIGNAL"),
])
def test_planted_fault_is_caught(base, mutate, code):
    assert code in codes(mutate(base))


def test_halt_bound_with_ltpi_hop():
    assert D.LOOP_WORST_US + D.LTPI_LL_WORST_US <= D.HALT_BOUND_US


# ------------------------------------------------------------------ LTPI link loss
LEVERS = {"PWRBRK_N[0]": 0, "PERST_N[0]": 0, "PWR_EN[0]": 0}       # 0 = asserted (brake on, reset on, power off)
RUNNING = {"PWRBRK_N[0]": 1, "PERST_N[0]": 1, "PWR_EN[0]": 1}


def test_finding_ltpi_as_written_holds_released_levers_on_link_loss():
    """LTPI 1.2 section 2.5.2: 'LTPI shall maintain the state of the GPIOs'. A governor whose link
    dies while its GPU runs leaves the GPU running. This is why REQ-LTPI-FS-1 exists."""
    link = D.LtpiLink(mode="spec")
    link.train()
    link.send(RUNNING)
    link.link_lost()
    link.send(LEVERS)                                    # the governor's HALT never arrives
    assert link.hpm_out == RUNNING


def test_failsafe_endpoint_asserts_levers_on_link_loss_and_before_training():
    link = D.LtpiLink(mode="failsafe", safe_values=dict(LEVERS))
    assert link.hpm_out == LEVERS                        # before the first Operational state
    link.send(RUNNING)
    assert link.hpm_out == LEVERS                        # frames before training are not delivered
    link.train()
    link.send(RUNNING)
    assert link.hpm_out == RUNNING
    link.link_lost()
    assert link.hpm_out == LEVERS
