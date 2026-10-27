# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Yobie Benjamin. Noncommercial use only; see NOTICE and LICENSING.md.
"""A bit-banged SMBus host for amaranth.sim, wired to a target through an open-drain bus model.

The bus is wired-AND: each line is high unless the host or the target pulls it low, which is
what the pull-up resistors do on a real board. Every simulated cycle goes through ``Host.wait``,
which records anything the safety argument cares about: doorbell strobes (and their values),
the target ever pulling SCL low (clock stretching, never allowed), and the target driving SDA
outside a transaction.
"""
from __future__ import annotations

from amaranth import Elaboratable, Module, Signal

from rtl.governor_rtl.smbus import crc8


class Bus(Elaboratable):
    """Host lines plus the wired-AND to the target (``dut`` has scl_i/sda_i/scl_oe/sda_oe)."""

    def __init__(self, dut):
        self.dut = dut
        self.host_scl = Signal(init=1)
        self.host_sda = Signal(init=1)
        self.scl = Signal()
        self.sda = Signal()

    def elaborate(self, platform):
        m = Module()
        m.submodules.dut = self.dut
        m.d.comb += [
            self.scl.eq(self.host_scl & ~self.dut.scl_oe),
            self.sda.eq(self.host_sda & ~self.dut.sda_oe),
            self.dut.scl_i.eq(self.scl),
            self.dut.sda_i.eq(self.sda),
        ]
        return m


class Host:
    def __init__(self, ctx, bus: Bus, target, q: int = 12, address: int = 0x58):
        self.ctx, self.bus, self.t, self.q, self.address = ctx, bus, target, q, address
        self.doorbells: list[int] = []
        self.stretched = 0
        self.timeouts = 0
        self.cycles = 0

    async def wait(self, n: int = 1):
        for _ in range(n):
            await self.ctx.tick()
            self.cycles += 1
            if self.ctx.get(self.t.doorbell):
                self.doorbells.append(self.ctx.get(self.t.doorbell_value))
            if self.ctx.get(self.t.scl_oe):
                self.stretched += 1
            if self.ctx.get(self.t.timeout):
                self.timeouts += 1

    def set(self, scl=None, sda=None):
        if scl is not None:
            self.ctx.set(self.bus.host_scl, scl)
        if sda is not None:
            self.ctx.set(self.bus.host_sda, sda)

    # ---- conditions and bits
    async def start(self):
        self.set(sda=1)
        await self.wait(self.q)
        self.set(scl=1)
        await self.wait(2 * self.q)
        self.set(sda=0)
        await self.wait(2 * self.q)
        self.set(scl=0)
        await self.wait(self.q)

    async def stop(self):
        self.set(sda=0)
        await self.wait(self.q)
        self.set(scl=1)
        await self.wait(2 * self.q)
        self.set(sda=1)
        await self.wait(2 * self.q)

    async def write_bit(self, b: int):
        self.set(sda=b)
        await self.wait(self.q)
        self.set(scl=1)
        await self.wait(2 * self.q)
        self.set(scl=0)
        await self.wait(self.q)

    async def read_bit(self) -> int:
        self.set(sda=1)
        await self.wait(self.q)
        self.set(scl=1)
        await self.wait(self.q)
        v = self.ctx.get(self.bus.sda)
        await self.wait(self.q)
        self.set(scl=0)
        await self.wait(self.q)
        return v

    async def write_byte(self, b: int, bits: int = 8) -> bool | None:
        """Send ``bits`` bits of ``b`` MSB first, then clock the ACK. Returns True on ACK.
        With bits < 8 the byte is truncated and no ACK clock is sent (returns None)."""
        for i in range(bits):
            await self.write_bit((b >> (7 - i)) & 1)
        if bits < 8:
            return None
        return not await self.read_bit()

    async def read_byte(self, ack: bool) -> int:
        v = 0
        for _ in range(8):
            v = (v << 1) | await self.read_bit()
        await self.write_bit(0 if ack else 1)
        return v

    # ---- transactions
    async def block_read(self, cmd: int, address: int | None = None):
        """SMBus Block Read with PEC. Returns (value or None, pec_ok, acks)."""
        a = self.address if address is None else address
        await self.start()
        acks = [await self.write_byte(a << 1), await self.write_byte(cmd)]
        await self.start()                                   # repeated start
        acks.append(await self.write_byte((a << 1) | 1))
        if not all(acks):
            await self.stop()
            return None, False, acks
        data = [await self.read_byte(True) for _ in range(5)]
        pec = await self.read_byte(False)
        await self.stop()
        want = crc8(bytes([a << 1, cmd, (a << 1) | 1] + data))
        value = data[1] | data[2] << 8 | data[3] << 16 | data[4] << 24
        return value, (pec == want and data[0] == 4), acks

    async def raw_write(self, payload: list[int], address: int | None = None, stop: bool = True):
        """``S addr+W payload... [P]``. Returns the ACK list (address first)."""
        a = self.address if address is None else address
        await self.start()
        acks = [await self.write_byte(a << 1)]
        for b in payload:
            acks.append(await self.write_byte(b))
        if stop:
            await self.stop()
        return acks

    async def doorbell(self, value: int, *, cmd: int = 0x40, count: int = 4, pec_delta: int = 0,
                       address: int | None = None, stop: bool = True, data: list[int] | None = None):
        """SMBus Block Write with PEC to ``cmd``; ``pec_delta`` corrupts the PEC."""
        a = self.address if address is None else address
        body = [cmd, count] + (data if data is not None else list(value.to_bytes(4, "little")))
        pec = (crc8(bytes([a << 1] + body)) + pec_delta) & 0xFF
        return await self.raw_write(body + [pec], address=a, stop=stop)

    async def idle(self, n: int = 50):
        self.set(scl=1, sda=1)
        await self.wait(n)
