# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""WAVE-FORMAL-PROOFS-ON-VERILOG entries for the blocks the FPGA push added (the SMBus/I2C management-bus target).

Same format as ``BLOCKS`` in ``__main__.py``: block -> (Amaranth source, class, mutants), each mutant a
one-line bug on purpose that must make ``rtl/formal/<block>.sv`` FAIL BY ASSERTION. The same mutants are
replayed as concrete bus traffic in ``rtl/tests/test_smbus.py::test_every_formal_mutant_fails_a_concrete_bus_test``,
so each catch is also a waveform that breaks the rule, not only an induction counterexample.
"""

BLOCKS_FPGA = {
    "smbus": ("smbus.py", "SMBusTarget", [
        ("the PEC byte is not checked (a corrupted write commits)",
         "with m.If(byte == self.crc):", "with m.If(1):"),
        ("the command code is not checked (a write to a read-only register is accepted)",
         "with m.If((self.cmd == DOORBELL_CMD) & (byte == 4)):", "with m.If(byte == 4):"),
        ("the byte count is not checked",
         "with m.If((self.cmd == DOORBELL_CMD) & (byte == 4)):", "with m.If(self.cmd == DOORBELL_CMD):"),
        ("the target answers any address",
         "with m.If(byte[1:] != self.address):", "with m.If(0):"),
        ("a write after a repeated start is accepted",
         "with m.If(self.sr_seen):", "with m.If(0):"),
        ("a repeated start does not disarm a pending write",
         "self.sda_oe.eq(0),\n                         self.armed.eq(0)]", "self.sda_oe.eq(0)]"),
        ("clock bits after the PEC do not disarm the write (a truncated extra byte commits)",
         "with m.If((self.step == X_EXTRA) & (self.nbit >= 1)):", "with m.If((self.step == X_EXTRA) & (self.nbit >= 8)):"),
        ("the PEC is not reset at a fresh START (it carries over from the last transaction)",
         "m.d.sync += [self.crc.eq(0), self.cmd_valid.eq(0), self.sr_seen.eq(0)]",
         "m.d.sync += [self.cmd_valid.eq(0), self.sr_seen.eq(0)]"),
        ("the doorbell value is assembled big-endian",
         "self.wbuf[8 * i: 8 * i + 8].eq(byte)", "self.wbuf[24 - 8 * i: 32 - 8 * i].eq(byte)"),
        ("the SMBus timeout never fires",
         "m.d.comb += expire.eq(hold & self.tick & (self.tcount == self.timeout_ticks - 1))",
         "m.d.comb += expire.eq(0)"),
        ("the target stretches the clock while it transmits",
         "self.scl_oe.eq(0),", "self.scl_oe.eq(self.phase == P_TX),"),
    ]),
}
