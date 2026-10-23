"""Differential conformance: the same mailbox frames into the RTL and into the functional model.

The RTL side is ``rtl.governor_rtl.mailbox.Mailbox`` under amaranth.sim. The model side is the real
``govsim.governor.Governor.command`` entry point (zeroized check, unknown-command check, the run-state check)
followed by the real ``_check_signed`` for the command's signer class; HEARTBEAT goes through the model's own
``_heartbeat`` path, because that is what the model does with it. Frames are real Ed25519 envelopes signed with
the rack's real keys; a "bad signature" is a real envelope with one hex digit of the signature changed.

What the firmware does between the two (and so what this harness has to assume, written down here):
  * key_slot: one slot per signer key (authority 0, host 1, endpoint 2, alarm approver 3, payments approver 4,
    heartbeat 5); the firmware maps key ids to slots.
  * epoch_exempt and needs_run come from the command class: govsim's EPOCH_EXEMPT (checked against the spec
    by test_fw_epoch_exempt_list_matches_spec) and NO_RUN_NEEDED.
  * signed_cmd: the command byte the crypto core read out of the verified payload's "type". For a HALT or
    CLEAR whose chip id or expiry is wrong, the spec puts the refusal on status 7, which the RTL can only
    report if the firmware presents a mismatching signed_cmd; the harness models it that way (opcode 0).
  * sig_ok: the crypto core's verdict on the envelope, i.e. whether the signature was left intact.

Status to reason mapping (docs/04 section 3 and the register map):
  2 ok, 3 mailbox.bad_signature | heartbeat.bad_signature, 4 mailbox.bad_sequence | heartbeat.replay,
  5 policy.stale_epoch, 6 mailbox.governor_not_running, 7 mailbox.wrong_command | mailbox.expired.
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, replace

from govsim import reasons
from govsim.cluster import build_rack
from govsim.governor import EPOCH_EXEMPT, HALTED_INITIAL as G_HALTED, MAILBOX_CODES, NO_RUN_NEEDED, RUN as G_RUN

from rtl.governor_rtl.mailbox import S_BAD_EPOCH, S_BAD_SEQ, S_BAD_SIG, S_OK, S_REFUSED, S_WRONG_CMD

from .framework import B, conformance, sim

CODE = {name: code for code, name in MAILBOX_CODES.items()}
REASON_TO_STATUS = {
    reasons.OK: S_OK, reasons.MBOX_BAD_SIGNATURE: S_BAD_SIG, reasons.HEARTBEAT_BAD_SIGNATURE: S_BAD_SIG,
    reasons.MBOX_BAD_SEQUENCE: S_BAD_SEQ, reasons.HEARTBEAT_REPLAY: S_BAD_SEQ, reasons.POLICY_STALE_EPOCH: S_BAD_EPOCH,
    reasons.MBOX_NOT_RUNNING: S_REFUSED, reasons.MBOX_WRONG_COMMAND: S_WRONG_CMD, reasons.MBOX_EXPIRED: S_WRONG_CMD,
}
STATUS_NAME = {2: "ok", 3: "bad signature", 4: "bad sequence", 5: "bad epoch", 6: "refused", 7: "wrong command"}

# command -> (signer class, rule id, key slot)
SIGNED = {
    "HALT": ("authority", None, 0), "CLEAR": ("authority", None, 0),
    "REQUEST": ("host", None, 1), "SIGN_OUTPUT": ("host", None, 1), "CAP_REQUEST": ("host", None, 1),
    "BEGIN_MODEL": ("host", None, 1), "END_MODEL": ("host", None, 1), "ROSTER_JOIN": ("host", None, 1),
    "COMMIT": ("endpoint", None, 2), "ALARM_CLEAR": ("approver", "alarms", 3),
    "APPROVE": ("approver", "payments.transfer.large", 4), "HEARTBEAT": ("heartbeat", None, 5),
}


@dataclass(frozen=True)
class Frame:
    cmd: str
    seq: int
    epoch_ok: bool = True
    sig_ok: bool = True
    type_ok: bool = True
    running: bool = True
    binding: str = "ok"          # HALT/CLEAR only: "ok", "other_chip", "expired"

    @property
    def exempt(self) -> bool:
        return self.cmd in EPOCH_EXEMPT

    @property
    def needs_run(self) -> bool:
        return self.cmd not in NO_RUN_NEEDED

    def other(self) -> str:
        return "CLEAR" if self.cmd == "HEARTBEAT" else "HEARTBEAT"


class ModelSide:
    """A one-governor rack from govsim, brought up, with every replay counter wiped."""

    def __init__(self):
        self.rack = build_rack(1, "rack")
        self.rack.bring_up()
        self.node = self.rack.nodes[0]
        self.g = self.node.governor
        r = self.rack
        self.keys = {"authority": r.authority_key, "host": self.node.host_key, "endpoint": r.endpoint_keys["payment-switch"],
                     "alarms": r.approvers["alarms"][0], "payments.transfer.large": r.approvers["payments.transfer.large"][0],
                     "heartbeat": r.heartbeat_key}
        self.g.mbox_seq, self.g.hb_last_seq = {}, -1
        # the handler for every signed command except HEARTBEAT becomes exactly the mailbox check, so the
        # model's verdict is command() (run state) + _check_signed (sequence, epoch, signature, what was signed)
        for cmd, (cls, rule, _) in SIGNED.items():
            if cmd != "HEARTBEAT":
                setattr(self.g, "_cmd_" + cmd.lower(),
                        lambda body, env, cls=cls, rule=rule, cmd=cmd: dict(zip(("ok", "why"), self.g._check_signed(env, cls, cmd, rule))))

    def key_for(self, cmd: str):
        cls, rule, _ = SIGNED[cmd]
        return self.keys[rule] if cls == "approver" else self.keys[cls]

    def env(self, f: Frame) -> dict:
        g, now = self.g, self.rack.clock.now()
        payload = {"seq": f.seq, "epoch": g.epoch if f.epoch_ok else "00" * 32,
                   "type": (f.cmd if f.type_ok else f.other()).lower()}
        if SIGNED[f.cmd][0] == "authority":
            payload["chip_id"] = g.chip_id if f.binding != "other_chip" else "some-other-chip"
            payload["expires_at"] = now + 30 if f.binding != "expired" else now - 1
        if f.cmd == "HEARTBEAT":
            payload.update(window_start=now - 1, window_end=now + 5)
        env = self.key_for(f.cmd).sign(payload)
        if not f.sig_ok:
            s = env["sig"]
            env["sig"] = ("0" if s[0] != "0" else "1") + s[1:]
        return env

    def last_seq(self, cmd: str) -> int:
        if cmd == "HEARTBEAT":
            return max(0, self.g.hb_last_seq)
        return max(0, self.g.mbox_seq.get(self.key_for(cmd).key_id, -1))

    def deliver(self, f: Frame) -> str:
        self.g.state = G_RUN if f.running else G_HALTED
        r = self.g.command(f.cmd, {}, self.env(f))
        return r["why"]


async def rtl_deliver(ctx, dut, f: Frame) -> tuple[int, int, int]:
    """Drive one frame into the Mailbox; return (status, dispatched, last_seq of its slot)."""
    slot = SIGNED[f.cmd][2]
    signed = CODE[f.cmd] if f.type_ok else CODE[f.other()]
    if f.binding != "ok":
        signed = 0                                   # assumption: the firmware folds the chip/expiry check into signed_cmd
    ctx.set(dut.frame_seq, f.seq & 0xFFFF_FFFF)
    ctx.set(dut.key_slot, slot)
    ctx.set(dut.cmd, CODE[f.cmd])
    ctx.set(dut.signed_cmd, signed)
    ctx.set(dut.epoch_match, f.epoch_ok)
    ctx.set(dut.epoch_exempt, f.exempt)
    ctx.set(dut.needs_run, f.needs_run)
    ctx.set(dut.running, f.running)
    ctx.set(dut.doorbell, 1)
    await ctx.tick()
    ctx.set(dut.doorbell, 0)
    dispatched = 0
    if ctx.get(dut.verify_req):
        ctx.set(dut.sig_done, 1)
        ctx.set(dut.sig_ok, f.sig_ok)
        dispatched = ctx.get(dut.dispatch)
        await ctx.tick()
        ctx.set(dut.sig_done, 0)
    return ctx.get(dut.status), dispatched, ctx.get(dut.last_seq[slot])


@dataclass
class Result:
    frame: Frame
    rtl_status: int
    rtl_dispatch: int
    rtl_seq: int
    model_reason: str
    model_seq: int
    rtl_seq_before: int
    model_seq_before: int

    @property
    def model_status(self) -> int | None:
        return REASON_TO_STATUS.get(self.model_reason)

    @property
    def agree(self) -> bool:
        return self.rtl_status == self.model_status and self.rtl_seq == self.model_seq

    def describe(self) -> str:
        f = self.frame
        defects = [n for n, bad in (("replayed/low seq", f.seq <= self.rtl_seq_before), ("stale epoch", not f.epoch_ok),
                                    ("bad signature", not f.sig_ok), ("signed for another command", not f.type_ok),
                                    ("not running", not f.running), (f"binding {f.binding}", f.binding != "ok")) if bad]
        return (f"{f.cmd} seq={f.seq} (last {self.rtl_seq_before}) [{', '.join(defects) or 'no defect'}]: "
                f"RTL status {self.rtl_status} ({STATUS_NAME.get(self.rtl_status, '?')}), model {self.model_reason}")


def run_frames(frames: list[Frame]) -> list[Result]:
    """Run frames through a fresh model governor and a fresh RTL mailbox, in order."""
    model = ModelSide()
    dut = B.Mailbox()
    out: list[Result] = []

    async def tb(ctx):
        for f in frames:
            mb = model.last_seq(f.cmd)
            rb = ctx.get(dut.last_seq[SIGNED[f.cmd][2]])
            why = model.deliver(f)
            status, disp, rseq = await rtl_deliver(ctx, dut, f)
            out.append(Result(f, status, disp, rseq, why, model.last_seq(f.cmd), rb, mb))
    sim(dut, tb)
    return out


def classify(r: Result) -> str | None:
    """Which recorded finding explains a disagreement (None: unexplained, which the random test refuses)."""
    f = r.frame
    seq_bad = f.seq <= r.rtl_seq_before
    if f.seq == 0 and r.rtl_seq_before == 0 and r.model_seq_before == 0:
        return "F-02"                                # the first sequence number of a key: model accepts 0, RTL refuses
    if f.cmd == "HEARTBEAT" and (not f.sig_ok or not f.type_ok):
        return "F-03"                                # the model's heartbeat path checks the signature first
    if f.needs_run and not f.running and (seq_bad or (not f.epoch_ok and not f.exempt)):
        return "F-01"                                # the model checks run state first, the RTL after epoch
    return None


def random_frames(n: int, seed: int) -> list[Frame]:
    rng = random.Random(seed)
    last = Counter()
    frames = []
    for _ in range(n):
        cmd = rng.choice(list(SIGNED))
        slot = SIGNED[cmd][2]
        x = rng.random()
        seq = (last[slot] + 1 if x < 0.5 else last[slot] if x < 0.65 else max(0, last[slot] - 1) if x < 0.75
               else last[slot] + rng.randrange(2, 1000) if x < 0.92 else 0)
        f = Frame(cmd, seq, epoch_ok=rng.random() < 0.85, sig_ok=rng.random() < 0.85, type_ok=rng.random() < 0.85,
                  running=rng.random() < 0.7,
                  binding=rng.choice(["ok"] * 8 + ["other_chip", "expired"]) if SIGNED[cmd][0] == "authority" else "ok")
        frames.append(f)
        # track what an accepting run would do, only to keep seq choices near the live counter
        if f.sig_ok and f.type_ok and f.binding == "ok" and seq > last[slot]:
            last[slot] = seq
    return frames


RANDOM_FRAMES = 4000
SEED = 20261023


@conformance("R-058", "R-054", "R-055", "R-056", "R-057", "R-061", "R-063")
def test_diff_mailbox_random_frames_only_known_disagreements():
    """4,000 random frames (12 commands, seq/epoch/run/signature/type/binding combinations) into RTL and model:
    every disagreement in status or in the stored sequence must be one of the recorded findings."""
    results = run_frames(random_frames(RANDOM_FRAMES, SEED))
    by_class: Counter = Counter()
    examples: dict[str, str] = {}
    unexplained = []
    for r in results:
        if r.agree:
            by_class["agree"] += 1
            continue
        c = classify(r)
        if c is None:
            unexplained.append(r.describe())
        else:
            by_class[c] += 1
            examples.setdefault(c, r.describe())
    assert not unexplained, f"{len(unexplained)} unexplained disagreements, first: {unexplained[:3]}"
    assert by_class["agree"] > RANDOM_FRAMES // 2
    return {"frames": len(results), "classes": dict(by_class), "examples": examples}


# ---------------------------------------------------------------- hand-written frames from the spec
def _one(setup: list[Frame], frame: Frame) -> Result:
    return run_frames(setup + [frame])[-1]


def _agree(r: Result):
    assert r.rtl_status == r.model_status, r.describe()
    assert r.rtl_seq == r.model_seq, f"stored sequence differs: RTL {r.rtl_seq}, model {r.model_seq}"


@conformance("R-058", "R-059")
def test_diff_spec_good_halt():
    """A good HALT: both accept, both store its sequence."""
    r = _one([], Frame("HALT", 1))
    _agree(r)
    assert r.rtl_status == S_OK and r.rtl_dispatch == 1


@conformance("R-058", "R-054")
def test_diff_spec_replayed_halt():
    """The same HALT twice: both say bad sequence the second time."""
    r = _one([Frame("HALT", 5)], Frame("HALT", 5))
    _agree(r)
    assert r.rtl_status == S_BAD_SEQ


@conformance("R-058", "R-055", "R-080")
def test_diff_spec_halt_with_stale_epoch_is_exempt():
    """HALT is epoch-exempt: a stale epoch is accepted by both."""
    r = _one([], Frame("HALT", 1, epoch_ok=False))
    _agree(r)
    assert r.rtl_status == S_OK


@conformance("R-058", "R-057", "R-063")
def test_diff_spec_heartbeat_presented_as_clear():
    """The 22 October case: a frame signed as a heartbeat presented as CLEAR. Both: wrong command, nothing consumed."""
    r = _one([], Frame("CLEAR", 1, type_ok=False))
    _agree(r)
    assert r.rtl_status == S_WRONG_CMD and r.rtl_seq == 0


@conformance("R-058", "R-055")
def test_diff_spec_stale_epoch_request():
    """A REQUEST under a stale epoch: both say bad epoch."""
    r = _one([], Frame("REQUEST", 1, epoch_ok=False))
    _agree(r)
    assert r.rtl_status == S_BAD_EPOCH


@conformance("R-058", "R-056")
def test_diff_spec_forged_request():
    """A REQUEST with a bad signature: both say bad signature."""
    r = _one([], Frame("REQUEST", 1, sig_ok=False))
    _agree(r)
    assert r.rtl_status == S_BAD_SIG


@conformance("R-058", "R-061", "R-092")
def test_diff_spec_request_while_not_running():
    """A good REQUEST while the governor is not in RUN: both refuse (status 6, mailbox.governor_not_running)."""
    r = _one([], Frame("REQUEST", 1, running=False))
    _agree(r)
    assert r.rtl_status == S_REFUSED


@conformance("R-058")
def test_diff_spec_replayed_and_forged():
    """Replayed and forged: the sequence check comes first in both."""
    r = _one([Frame("COMMIT", 3)], Frame("COMMIT", 3, sig_ok=False))
    _agree(r)
    assert r.rtl_status == S_BAD_SEQ


@conformance("R-058")
def test_diff_spec_stale_and_forged():
    """Stale epoch and forged: the epoch check comes before the signature in both."""
    r = _one([], Frame("COMMIT", 1, epoch_ok=False, sig_ok=False))
    _agree(r)
    assert r.rtl_status == S_BAD_EPOCH


@conformance("R-058", "R-061")
def test_diff_spec_not_running_and_forged():
    """Not running and forged: both refuse for run state; note the RTL decides it before asking for the signature."""
    r = _one([], Frame("REQUEST", 1, running=False, sig_ok=False))
    _agree(r)
    assert r.rtl_status == S_REFUSED


@conformance("R-058", "R-081", "R-063")
def test_diff_spec_clear_for_another_chip():
    """A CLEAR naming another chip: model mailbox.wrong_command, RTL status 7 (given the firmware's signed_cmd)."""
    r = _one([], Frame("CLEAR", 1, binding="other_chip"))
    _agree(r)
    assert r.rtl_status == S_WRONG_CMD


@conformance("R-058", "R-081", "R-063")
def test_diff_spec_expired_clear():
    """A CLEAR past its expiry: model mailbox.expired, RTL status 7."""
    r = _one([], Frame("CLEAR", 1, binding="expired"))
    _agree(r)
    assert r.rtl_status == S_WRONG_CMD


@conformance("R-058", "R-054")
def test_diff_spec_per_key_sequence():
    """Two signer keys keep two counters in both: a host frame with seq 1 after an authority frame with seq 50."""
    r = _one([Frame("HALT", 50)], Frame("REQUEST", 1))
    _agree(r)
    assert r.rtl_status == S_OK


@conformance("R-058", "R-056", "R-083")
def test_diff_spec_good_heartbeat():
    """A good heartbeat: both accept and store its sequence."""
    r = _one([], Frame("HEARTBEAT", 1))
    _agree(r)
    assert r.rtl_status == S_OK


@conformance("R-058", "R-061", finding="F-01")
def test_diff_finding_replayed_request_while_not_running():
    """F-01: a replayed REQUEST while not running. RTL reports bad sequence (4); the model reports not running."""
    _agree(_one([Frame("REQUEST", 2)], Frame("REQUEST", 2, running=False)))


@conformance("R-058", "R-061", finding="F-01")
def test_diff_finding_stale_request_while_not_running():
    """F-01: a stale-epoch REQUEST while not running. RTL reports bad epoch (5); the model reports not running."""
    _agree(_one([], Frame("REQUEST", 1, epoch_ok=False, running=False)))


@conformance("R-054", "R-058", finding="F-02")
def test_diff_finding_first_sequence_number_zero():
    """F-02: the first frame of a key with seq 0. The model accepts it (0 > -1); the RTL refuses it (0 > 0 is false)."""
    _agree(_one([], Frame("HALT", 0)))


@conformance("R-058", finding="F-03")
def test_diff_finding_replayed_forged_heartbeat():
    """F-03: a replayed, forged heartbeat. RTL: bad sequence (4). Model: heartbeat.bad_signature (signature first)."""
    _agree(_one([Frame("HEARTBEAT", 4)], Frame("HEARTBEAT", 4, sig_ok=False)))


@conformance("R-057", "R-058", finding="F-03")
def test_diff_finding_heartbeat_signed_as_something_else():
    """F-03: a frame signed for CLEAR presented as HEARTBEAT. RTL: wrong command (7). Model: heartbeat.bad_signature."""
    _agree(_one([], Frame("HEARTBEAT", 1, type_ok=False)))


@conformance("R-058", "R-086")
def test_model_clear_handler_reports_the_mailbox_reason():
    """The spec says the first failing check is the reason reported. The model's real CLEAR handler reports
    clear.unauthorized for every mailbox failure; that is recorded as F-04 (model only) by the next test."""
    m = ModelSide()
    g = m.g
    del g._cmd_clear                                      # the real handler, not the harness's
    g.state = G_RUN
    r = g.command("CLEAR", {}, m.env(Frame("CLEAR", 1, sig_ok=False)))
    assert not r["ok"]


@conformance("R-058", "R-086", finding="F-04")
def test_model_finding_clear_collapses_reasons():
    """F-04 (model): a replayed CLEAR should report mailbox.bad_sequence; the model's CLEAR handler says clear.unauthorized."""
    m = ModelSide()
    g = m.g
    del g._cmd_clear
    g.state = G_RUN
    g.command("CLEAR", {}, m.env(Frame("CLEAR", 7)))
    r = g.command("CLEAR", {}, m.env(Frame("CLEAR", 7)))
    assert r["why"] == reasons.MBOX_BAD_SEQUENCE, r["why"]


# ---------------------------------------------------------------- firmware-owned rules the model carries
@conformance("R-080")
def test_fw_epoch_exempt_list_matches_spec():
    """The model's epoch-exempt set (what the firmware feeds epoch_exempt from) is exactly the commands the spec lists (seven since EXCLUDE, 23 October 2026)."""
    import os
    import re
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    text = " ".join(open(os.path.join(here, "docs", "04-specification.md"), encoding="utf-8").read().split())
    m = re.search(r"except the epoch-exempt commands (.*?), which move", text)
    assert m, "the exempt list moved in docs/04"
    listed = set(re.findall(r"`([A-Z_]+)`", m.group(1)))
    assert listed == set(EPOCH_EXEMPT), (listed, EPOCH_EXEMPT)


@conformance("R-081")
def test_fw_authority_expiry_ceiling_is_60s():
    """The model refuses a HALT or CLEAR whose expiry is more than 60 s ahead (spec: no more than 60 s)."""
    from govsim.governor import AUTHORITY_TTL_S
    assert AUTHORITY_TTL_S == 60.0
    m = ModelSide()
    now = m.rack.clock.now()
    env = m.rack.authority_key.sign({"seq": 1, "epoch": m.g.epoch, "type": "halt", "chip_id": m.g.chip_id, "expires_at": now + 61})
    assert m.g._check_signed(env, "authority", "HALT") == (False, reasons.MBOX_EXPIRED)


@conformance("R-084", "R-085")
def test_fw_heartbeat_key_cannot_sign_a_halt():
    """The heartbeat key signs heartbeats and nothing else: a HALT under the heartbeat key is a bad signature in the model."""
    m = ModelSide()
    now = m.rack.clock.now()
    env = m.rack.heartbeat_key.sign({"seq": 1, "epoch": m.g.epoch, "type": "halt", "chip_id": m.g.chip_id, "expires_at": now + 30})
    assert m.g._check_signed(env, "authority", "HALT") == (False, reasons.MBOX_BAD_SIGNATURE)


@conformance("R-033", "R-083")
def test_fw_heartbeat_window_is_clamped_to_policy_expiry():
    """The model clamps a signed heartbeat window to fabric.heartbeat_expiry_s before it reloads the timer (the RTL
    takes the window as given, so this clamp is the firmware's job)."""
    m = ModelSide()
    g, now = m.g, m.rack.clock.now()
    limit = float(g.policy["fabric"].get("heartbeat_expiry_s", 5.0))
    env = m.rack.heartbeat_key.sign({"type": "heartbeat", "seq": 99, "epoch": g.epoch, "window_start": now - 1,
                                     "window_end": now + 10 * limit})
    assert g.command("HEARTBEAT", {}, env)["ok"]
    assert g.hb_expiry <= now + limit


@conformance("R-090")
def test_fw_host_peer_only_on_pcie():
    """CAP_REQUEST for the peer 'host' is refused on NVSwitch, DPU and storage and accepted on PCIe."""
    rack = build_rack(1, "rack")
    rack.bring_up()
    node = rack.nodes[0]
    g = node.governor
    for point in ("nvswitch", "dpu", "storage"):
        r = g.command("CAP_REQUEST", {}, node.host_sign({"peer": "host", "point": point, "direction": "both"}, g.epoch, "CAP_REQUEST"))
        assert not r["ok"], (point, r)
    r = g.command("CAP_REQUEST", {}, node.host_sign({"peer": "host", "point": "pcie", "direction": "both"}, g.epoch, "CAP_REQUEST"))
    assert r["ok"], r
