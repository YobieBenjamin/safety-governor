# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""Signed mailbox FSM. Invariant: no command is dispatched unless the sequence number is
greater than the last accepted one for that signer key, the frame's epoch matches the epoch
register or the command is epoch-exempt, the signature verified (``sig_ok`` from the
crypto core), and the command byte inside the signed payload (``signed_cmd``, read by the crypto
core from the verified bytes) is the command the frame asks for. The checks run in that order and
the first failure is what the status reports. The last check was added on 22 October 2026: without
it a frame signed for one command (a heartbeat) was dispatched as another (CLEAR).
``key_slot`` selects the per-signer-key sequence register (the firmware maps key ids to slots).

Sequence space (adversarial audit 3). The per-key sequence registers were 32 bits wide, only ever rose and were reset
only by a chip reset, so one accepted frame at ``2**32 - 1`` ended that key for the life of the chip (a host key at
1,000 commands a second gets there in 49.7 days). Now they are 64 bits wide (at a million commands a second a key
needs about 584,000 years to run out, against a 10-year product life, docs/04 section 11), and every key slot returns
to zero when the policy epoch advances (``epoch_advanced``, a strobe the core drives from the epoch register's
commit of a new epoch). A reset to zero cannot open a replay inside an epoch: it happens only when the epoch changes,
and a frame that is not epoch-exempt must carry the epoch in force (``epoch_match``), so an old frame fails the epoch
check. Inside one epoch every slot still only rises, as before.

Status codes (the ``MBOX_STATUS`` register): 0 idle, 1 busy, 2 ok, 3 bad signature,
4 bad sequence, 5 bad epoch, 6 refused (governor not running for this command class),
7 wrong command (a good signature over a different command; the sequence is not consumed).
"""
from amaranth import Array, Elaboratable, Module, Signal

S_IDLE, S_BUSY, S_OK, S_BAD_SIG, S_BAD_SEQ, S_BAD_EPOCH, S_REFUSED, S_WRONG_CMD = 0, 1, 2, 3, 4, 5, 6, 7


class Mailbox(Elaboratable):
    def __init__(self, key_slots: int = 8, seq_bits: int = 64):
        self.doorbell = Signal()
        self.frame_seq = Signal(seq_bits)
        self.key_slot = Signal(range(key_slots))
        self.cmd = Signal(8)
        self.signed_cmd = Signal(8)        # the command byte inside the verified payload (from the crypto core)
        self.epoch_match = Signal()        # frame epoch == epoch register (computed outside)
        self.epoch_exempt = Signal()       # this command class ignores the epoch
        self.needs_run = Signal()          # this command class needs state RUN
        self.running = Signal()            # from HaltSeq
        # adversarial audit 3: one-cycle strobe, the epoch register committed a new epoch; every key slot restarts at 0
        self.epoch_advanced = Signal()
        self.sig_done = Signal()           # from the crypto core
        self.sig_ok = Signal()
        self.verify_req = Signal()         # to the crypto core
        self.dispatch = Signal()           # one-cycle strobe to the firmware/dispatcher
        self.cmd_out = Signal(8)
        self.status = Signal(3)
        self.last_seq = Array(Signal(seq_bits, name=f"seq{i}") for i in range(key_slots))

    def elaborate(self, platform):
        m = Module()
        seq_ok = Signal()
        m.d.comb += seq_ok.eq(self.frame_seq > self.last_seq[self.key_slot])
        with m.FSM():
            with m.State("IDLE"):
                with m.If(self.doorbell):
                    with m.If(~seq_ok):
                        m.d.sync += self.status.eq(S_BAD_SEQ)
                    with m.Elif(~(self.epoch_match | self.epoch_exempt)):
                        m.d.sync += self.status.eq(S_BAD_EPOCH)
                    with m.Elif(self.needs_run & ~self.running):
                        m.d.sync += self.status.eq(S_REFUSED)
                    with m.Else():
                        m.d.sync += self.status.eq(S_BUSY)
                        m.next = "VERIFY"
            with m.State("VERIFY"):
                m.d.comb += self.verify_req.eq(1)
                with m.If(self.sig_done):
                    with m.If(self.sig_ok & (self.signed_cmd == self.cmd)):
                        m.d.sync += [self.last_seq[self.key_slot].eq(self.frame_seq), self.status.eq(S_OK), self.cmd_out.eq(self.cmd)]
                        m.d.comb += self.dispatch.eq(1)
                    with m.Elif(self.sig_ok):
                        m.d.sync += self.status.eq(S_WRONG_CMD)
                    with m.Else():
                        m.d.sync += self.status.eq(S_BAD_SIG)
                    m.next = "IDLE"
        # adversarial audit 3: a new epoch restarts every key slot at zero. Written after the FSM so it wins over a
        # dispatch recorded in the same cycle (the new epoch starts clean); frames of the old epoch fail epoch_match
        with m.If(self.epoch_advanced):
            for seq in self.last_seq:
                m.d.sync += seq.eq(0)
        return m
