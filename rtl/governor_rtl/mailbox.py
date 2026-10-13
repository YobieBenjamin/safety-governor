"""Signed mailbox FSM. Invariant: no command is dispatched unless the sequence number is
greater than the last accepted one for that signer class, the signature verified
(``sig_ok`` from the crypto core), and the frame's epoch matches the epoch register or the
command is epoch-exempt.

Status codes (the ``MBOX_STATUS`` register): 0 idle, 1 busy, 2 ok, 3 bad signature,
4 bad sequence, 5 bad epoch, 6 refused (governor not running for this command class).
"""
from amaranth import Array, Elaboratable, Module, Signal

S_IDLE, S_BUSY, S_OK, S_BAD_SIG, S_BAD_SEQ, S_BAD_EPOCH, S_REFUSED = 0, 1, 2, 3, 4, 5, 6


class Mailbox(Elaboratable):
    def __init__(self, signer_classes: int = 8, seq_bits: int = 32):
        self.doorbell = Signal()
        self.frame_seq = Signal(seq_bits)
        self.signer_class = Signal(range(signer_classes))
        self.cmd = Signal(8)
        self.epoch_match = Signal()        # frame epoch == epoch register (computed outside)
        self.epoch_exempt = Signal()       # this command class ignores the epoch
        self.needs_run = Signal()          # this command class needs state RUN
        self.running = Signal()            # from HaltSeq
        self.sig_done = Signal()           # from the crypto core
        self.sig_ok = Signal()
        self.verify_req = Signal()         # to the crypto core
        self.dispatch = Signal()           # one-cycle strobe to the firmware/dispatcher
        self.cmd_out = Signal(8)
        self.status = Signal(3)
        self.last_seq = Array(Signal(seq_bits, name=f"seq{i}") for i in range(signer_classes))

    def elaborate(self, platform):
        m = Module()
        seq_ok = Signal()
        m.d.comb += seq_ok.eq(self.frame_seq > self.last_seq[self.signer_class])
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
                    with m.If(self.sig_ok):
                        m.d.sync += [self.last_seq[self.signer_class].eq(self.frame_seq), self.status.eq(S_OK), self.cmd_out.eq(self.cmd)]
                        m.d.comb += self.dispatch.eq(1)
                    with m.Else():
                        m.d.sync += self.status.eq(S_BAD_SIG)
                    m.next = "IDLE"
        return m
