"""SMBus/I2C target for the host management bus: the read-only CSR window of
``docs/04-specification.md`` section 2 plus the mailbox doorbell, and nothing else.

The protocol, as a host sees it (SMBus 3.x public behaviour, 7-bit address ``address``):

- Read a CSR word: SMBus Block Read. ``S addr+W cmd Sr addr+R`` then the target sends
  ``count=4, d0, d1, d2, d3, PEC`` (little-endian word, PEC is CRC-8, x^8+x^2+x+1, init 0, over
  every byte of the transaction including both address bytes). The command code is the CSR word
  index, ``offset >> 2``, so 0x00 is ID, 0x02 STATE, 0x41 MBOX_STATUS. The word is snapshotted
  when the read address is acknowledged, so a 32-bit counter cannot tear between bytes.
- Ring the doorbell: SMBus Block Write with PEC. ``S addr+W 0x40 count=4 d0 d1 d2 d3 PEC P``.
  The doorbell fires once, on the STOP, and only if every byte was exactly that: the right
  address, command 0x40 (MBOX_DOORBELL at 0x100), a count of 4, four data bytes and a correct PEC,
  with no repeated start and nothing after the PEC. PEC is mandatory for the write.
- Anything else that tries to write is refused on the bus and changes nothing: a write to any
  other command code is NACKed at its first data byte, a wrong count is NACKed, a bad PEC is
  NACKed, a byte after the PEC is NACKed and disarms the write, a repeated start disarms it, a
  write after a repeated start is NACKed at the address, a transfer cut short never reaches the
  STOP with a full frame. Reads of command codes with no register return 0.

Policy choices the spec leaves to the target:

- Clock stretching: never. ``scl_oe`` is constant 0, so the target's cumulative clock-low extend
  (tLOW:SEXT, at most 25 ms in SMBus) is zero by construction. The read word is ready a cycle
  after the address is decoded, far inside one SCL low phase at any SMBus speed.
- Timeout: a transaction in which SCL stays low (or the target holds SDA) for ``timeout_ticks``
  ticks of ``tick`` (1 us each, so 25 ms by default: SMBus tTIMEOUT,MIN) is abandoned. The target
  releases SDA, drops anything armed, pulses ``timeout`` and ignores the bus until the next START.
  SMBus requires the reset no later than tTIMEOUT,MAX, 35 ms.
- Glitch filter: two flip-flop synchronizer, then a level must hold ``filter`` cycles before the
  target believes it (3 cycles at 50 MHz is 60 ns, over the 50 ns spike limit).

The internal state is kept as attributes so ``rtl/formal/smbus.sv`` can relate it to its own
independent bus monitor. None of it is a write path: the only outputs toward the core are
``csr_addr`` (a read-mux select) and the ``doorbell`` strobe with its 32-bit value.
"""
from amaranth import Cat, Const, Elaboratable, Module, Mux, Signal
from amaranth.lib.cdc import FFSynchronizer

DOORBELL_CMD = 0x40            # MBOX_DOORBELL, byte offset 0x100, word index 0x40
DEFAULT_ADDRESS = 0x58         # 7-bit target address; strap-selectable on a real board

# phases
P_IDLE, P_RX, P_TX, P_WAIT = 0, 1, 2, 3
# steps of the transaction, as seen from the target
X_ADDR, X_CMD, X_COUNT, X_DATA, X_PEC, X_EXTRA, X_READ = 0, 1, 2, 3, 4, 5, 6


def crc8(data: bytes, crc: int = 0) -> int:
    """SMBus PEC: CRC-8, polynomial 0x07, init 0, no reflection, no final xor."""
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def _crc8_expr(crc, byte):
    # CRC-8 over one byte is linear in (crc ^ byte): output bit i is the XOR of the input bits j
    # whose single-bit CRC has bit i set. Written as XORs so the netlist stays small.
    v = crc ^ byte
    cols = [crc8(bytes([1 << j])) for j in range(8)]
    bits = []
    for i in range(8):
        terms = [v[j] for j in range(8) if (cols[j] >> i) & 1]
        x = terms[0]
        for t in terms[1:]:
            x = x ^ t
        bits.append(x)
    return Cat(*bits)


class SMBusTarget(Elaboratable):
    def __init__(self, address: int = DEFAULT_ADDRESS, filter: int = 3, timeout_ticks: int = 25_000):
        assert 0 < address < 0x80 and filter >= 1 and timeout_ticks >= 2
        self.address, self.filter, self.timeout_ticks = address, filter, timeout_ticks
        # pads (open drain: *_oe = 1 pulls the line low)
        self.scl_i = Signal(init=1)
        self.sda_i = Signal(init=1)
        self.scl_oe = Signal()
        self.sda_oe = Signal()
        self.tick = Signal()                 # 1 us strobe
        # toward the core
        self.csr_addr = Signal(12)
        self.csr_rdata = Signal(32)
        self.doorbell = Signal()             # one-cycle strobe on a committed doorbell write
        self.doorbell_value = Signal(32)     # the frame length the host wrote
        # diagnostics (strobes)
        self.timeout = Signal()
        self.pec_error = Signal()
        self.refused_write = Signal()
        # internal state, exposed for the formal harness
        self.scl_f = Signal(init=1)          # filtered lines
        self.sda_f = Signal(init=1)
        self.scl_p = Signal(init=1)          # previous filtered lines (edge detection)
        self.sda_p = Signal(init=1)
        self.phase = Signal(2)
        self.step = Signal(3)
        self.nbit = Signal(4)                # SCL rising edges in the current byte frame, 0..9
        self.shift = Signal(8)
        self.ack = Signal()                  # the ACK/NACK decided for the byte just received
        self.sr_seen = Signal()              # a repeated start happened in this transaction
        self.cmd = Signal(8)
        self.cmd_valid = Signal()
        self.dcount = Signal(2)
        self.wbuf = Signal(32)
        self.crc = Signal(8)
        self.armed = Signal()                # a complete, PEC-checked doorbell write waits for STOP
        self.snap = Signal(32)
        self.txidx = Signal(3)
        self.txsh = Signal(8)
        self.host_ack = Signal()
        self.tcount = Signal(range(timeout_ticks))

    def elaborate(self, platform):
        m = Module()
        # ---- synchronize and filter
        scl_s, sda_s = Signal(init=1), Signal(init=1)
        m.submodules.scl_sync = FFSynchronizer(self.scl_i, scl_s, init=1)
        m.submodules.sda_sync = FFSynchronizer(self.sda_i, sda_s, init=1)
        for raw, filt, name in ((scl_s, self.scl_f, "scl"), (sda_s, self.sda_f, "sda")):
            if self.filter == 1:
                m.d.sync += filt.eq(raw)
            else:
                cnt = Signal(range(self.filter), name=f"{name}_fcnt")
                with m.If(raw != filt):
                    with m.If(cnt == self.filter - 1):
                        m.d.sync += [filt.eq(raw), cnt.eq(0)]
                    with m.Else():
                        m.d.sync += cnt.eq(cnt + 1)
                with m.Else():
                    m.d.sync += cnt.eq(0)
        m.d.sync += [self.scl_p.eq(self.scl_f), self.sda_p.eq(self.sda_f)]

        start = Signal()
        stop = Signal()
        rise = Signal()
        fall = Signal()
        m.d.comb += [
            start.eq(self.scl_f & self.scl_p & self.sda_p & ~self.sda_f),
            stop.eq(self.scl_f & self.scl_p & ~self.sda_p & self.sda_f),
            rise.eq(self.scl_f & ~self.scl_p),
            fall.eq(~self.scl_f & self.scl_p),
            self.scl_oe.eq(0),                                     # never stretch the clock
            self.csr_addr.eq(Cat(Const(0, 2), self.cmd)),          # word index -> byte offset
        ]

        byte = Signal(8)
        m.d.comb += byte.eq(Cat(self.sda_f, self.shift[:7]))       # the 8th bit completes it, MSB first
        crc_next = Signal(8)
        m.d.comb += crc_next.eq(_crc8_expr(self.crc, byte))

        tx_byte = Signal(8)                                         # the byte to send at index txidx
        with m.Switch(self.txidx):
            with m.Case(0):
                m.d.comb += tx_byte.eq(4)
            with m.Case(1):
                m.d.comb += tx_byte.eq(self.snap[0:8])
            with m.Case(2):
                m.d.comb += tx_byte.eq(self.snap[8:16])
            with m.Case(3):
                m.d.comb += tx_byte.eq(self.snap[16:24])
            with m.Case(4):
                m.d.comb += tx_byte.eq(self.snap[24:32])
            with m.Case(5):
                m.d.comb += tx_byte.eq(self.crc)
            with m.Default():
                m.d.comb += tx_byte.eq(0xFF)

        def load_tx():
            # start a TX frame: drive bit 7 now, fold the byte into the PEC
            return [self.txsh.eq(tx_byte), self.sda_oe.eq(~tx_byte[7]), self.crc.eq(_crc8_expr(self.crc, tx_byte)),
                    self.txidx.eq(Mux(self.txidx == 7, 7, self.txidx + 1)), self.phase.eq(P_TX)]

        m.d.sync += [self.doorbell.eq(0), self.timeout.eq(0), self.pec_error.eq(0), self.refused_write.eq(0)]

        # ---- timeout: SCL low, or our own SDA held, inside a transaction
        in_xfer = self.phase != P_IDLE
        hold = in_xfer & (~self.scl_f | self.sda_oe)
        expire = Signal()
        m.d.comb += expire.eq(hold & self.tick & (self.tcount == self.timeout_ticks - 1))
        with m.If(~hold):
            m.d.sync += self.tcount.eq(0)
        with m.Elif(self.tick & ~expire):
            m.d.sync += self.tcount.eq(self.tcount + 1)

        with m.If(expire):
            m.d.sync += [self.phase.eq(P_IDLE), self.sda_oe.eq(0), self.armed.eq(0), self.cmd_valid.eq(0),
                         self.tcount.eq(0), self.timeout.eq(1)]
        with m.Elif(stop):
            with m.If(self.armed & (self.phase != P_IDLE)):
                m.d.sync += [self.doorbell.eq(1), self.doorbell_value.eq(self.wbuf)]
            m.d.sync += [self.phase.eq(P_IDLE), self.sda_oe.eq(0), self.armed.eq(0), self.cmd_valid.eq(0)]
        with m.Elif(start):
            with m.If(self.phase == P_IDLE):                       # a fresh START
                m.d.sync += [self.crc.eq(0), self.cmd_valid.eq(0), self.sr_seen.eq(0)]
            with m.Else():                                          # a repeated start
                m.d.sync += self.sr_seen.eq(1)
            m.d.sync += [self.phase.eq(P_RX), self.step.eq(X_ADDR), self.nbit.eq(0), self.sda_oe.eq(0),
                         self.armed.eq(0)]
        with m.Elif(rise & ((self.phase == P_RX) | (self.phase == P_TX))):
            m.d.sync += self.nbit.eq(Mux(self.nbit == 9, 9, self.nbit + 1))
            with m.If((self.step == X_EXTRA) & (self.nbit >= 1)):
                m.d.sync += self.armed.eq(0)                        # anything after the PEC but the STOP
            with m.If(self.phase == P_RX):
                with m.If(self.nbit < 7):
                    m.d.sync += self.shift.eq(Cat(self.sda_f, self.shift[:7]))
                with m.Elif(self.nbit == 7):
                    # a byte is complete: decide ACK and its meaning now, drive the ACK at the next fall
                    m.d.sync += self.shift.eq(byte)
                    with m.Switch(self.step):
                        with m.Case(X_ADDR):
                            with m.If(byte[1:] != self.address):
                                m.d.sync += self.ack.eq(0)
                            with m.Elif(~byte[0]):                  # write
                                with m.If(self.sr_seen):
                                    m.d.sync += [self.ack.eq(0), self.refused_write.eq(1)]
                                with m.Else():
                                    m.d.sync += [self.ack.eq(1), self.crc.eq(crc_next), self.step.eq(X_CMD)]
                            with m.Elif(self.cmd_valid):            # read with a command code set
                                m.d.sync += [self.ack.eq(1), self.crc.eq(crc_next), self.step.eq(X_READ),
                                             self.snap.eq(self.csr_rdata), self.txidx.eq(0)]
                            with m.Else():
                                m.d.sync += self.ack.eq(0)
                        with m.Case(X_CMD):
                            m.d.sync += [self.ack.eq(1), self.crc.eq(crc_next), self.cmd.eq(byte),
                                         self.cmd_valid.eq(1), self.step.eq(X_COUNT)]
                        with m.Case(X_COUNT):
                            with m.If((self.cmd == DOORBELL_CMD) & (byte == 4)):
                                m.d.sync += [self.ack.eq(1), self.crc.eq(crc_next), self.step.eq(X_DATA),
                                             self.dcount.eq(0)]
                            with m.Else():
                                m.d.sync += [self.ack.eq(0), self.refused_write.eq(1)]
                        with m.Case(X_DATA):
                            m.d.sync += [self.ack.eq(1), self.crc.eq(crc_next), self.dcount.eq(self.dcount + 1)]
                            with m.Switch(self.dcount):
                                for i in range(4):
                                    with m.Case(i):
                                        m.d.sync += self.wbuf[8 * i: 8 * i + 8].eq(byte)
                            with m.If(self.dcount == 3):
                                m.d.sync += self.step.eq(X_PEC)
                        with m.Case(X_PEC):
                            with m.If(byte == self.crc):
                                m.d.sync += [self.ack.eq(1), self.step.eq(X_EXTRA)]
                            with m.Else():
                                m.d.sync += [self.ack.eq(0), self.pec_error.eq(1)]
                        with m.Default():                           # X_EXTRA: no byte belongs after the PEC
                            m.d.sync += [self.ack.eq(0), self.armed.eq(0)]
            with m.Elif(self.nbit == 8):                            # TX: the host's ACK bit
                m.d.sync += self.host_ack.eq(~self.sda_f)
        with m.Elif(fall & ((self.phase == P_RX) | (self.phase == P_TX))):
            with m.If(self.phase == P_RX):
                with m.If(self.nbit == 8):
                    m.d.sync += self.sda_oe.eq(self.ack)            # ACK is SDA low for the 9th clock
                with m.Elif(self.nbit == 9):                        # end of the frame
                    m.d.sync += [self.nbit.eq(0), self.sda_oe.eq(0)]
                    with m.If(~self.ack):
                        m.d.sync += self.phase.eq(P_WAIT)
                    with m.Elif(self.step == X_READ):
                        m.d.sync += load_tx()
                    with m.Elif(self.step == X_EXTRA):
                        m.d.sync += self.armed.eq(1)                # complete and PEC-checked: commit on STOP
            with m.Else():                                          # P_TX
                with m.If((self.nbit >= 1) & (self.nbit <= 7)):
                    m.d.sync += [self.txsh.eq(Cat(Const(0, 1), self.txsh[:7])), self.sda_oe.eq(~self.txsh[6])]
                with m.Elif(self.nbit == 8):
                    m.d.sync += self.sda_oe.eq(0)                   # release for the host's ACK
                with m.Elif(self.nbit == 9):
                    m.d.sync += self.nbit.eq(0)
                    with m.If(self.host_ack):
                        m.d.sync += load_tx()
                    with m.Else():
                        m.d.sync += [self.phase.eq(P_WAIT), self.sda_oe.eq(0)]
        return m
