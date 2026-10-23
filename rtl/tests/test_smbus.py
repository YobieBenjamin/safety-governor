"""The SMBus/I2C target, driven by a bit-banged SMBus host in amaranth.sim (rtl/tests/smbus_host.py).

Two layers:
- the bare target with a fixed CSR word, for the protocol rules and the malformed traffic, and a replay of
  every formal mutant in rtl/formal/blocks_fpga.py as concrete bus traffic (each must fail a rule here);
- the target in front of the real governor_core (GovernorSMBus), for the end-to-end claims: the CSR window
  reads back through the bus, the doorbell reaches the mailbox, and malformed traffic changes no register.
"""
import importlib.util
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest  # noqa: E402
from amaranth import Signal  # noqa: E402
from amaranth.sim import Simulator  # noqa: E402

from rtl.formal.blocks_fpga import BLOCKS_FPGA  # noqa: E402
from rtl.governor_rtl import GovernorSMBus, SMBusTarget  # noqa: E402
from rtl.governor_rtl.smbus import DOORBELL_CMD, crc8  # noqa: E402
from rtl.tests.smbus_host import Bus, Host  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
ADDR = 0x58
WORD = 0xA1B2C3D4
TIMEOUT = 600                 # ticks; the tests tick every cycle, the chip ticks every microsecond (25,000)


def simulate(top, target, body, q=10):
    sim = Simulator(top)
    sim.add_clock(1e-6)
    result = {}

    async def tb(ctx):
        h = Host(ctx, top, target, q=q)
        result["host"] = h
        await body(ctx, h)

    sim.add_testbench(tb)
    sim.run()
    return result["host"]


def bare(cls=SMBusTarget, **kw):
    t = cls(address=ADDR, timeout_ticks=TIMEOUT, **kw)
    return Bus(t), t


def test_pec_is_smbus_crc8():
    assert crc8(b"123456789") == 0xF4                     # the CRC-8/SMBUS check value
    assert crc8(b"") == 0 and crc8(b"\x00") == 0


# ---- the protocol battery: every rule the target must keep, on the bare block

async def battery(ctx, h):
    t = h.t
    ctx.set(t.csr_rdata, WORD)
    ctx.set(t.tick, 1)
    await h.idle()
    sda_driven_outside = 0

    async def quiet(n=40):
        nonlocal sda_driven_outside
        for _ in range(n):
            await h.wait()
            if ctx.get(t.sda_oe) and ctx.get(t.phase) == 0:
                sda_driven_outside += 1

    # R1 a block read returns the word with a correct PEC (and primes the PEC register for R2)
    v, pec_ok, acks = await h.block_read(0x00)
    assert acks == [True, True, True] and v == WORD and pec_ok, "block read"
    await quiet()
    # R2 a good doorbell write commits exactly once, with the bytes little-endian
    acks = await h.doorbell(0x11223344)
    await quiet()
    assert all(acks) and h.doorbells == [0x11223344], f"good doorbell write: {acks} {h.doorbells}"
    # R3 a bad PEC is NACKed and never commits
    acks = await h.doorbell(0x55, pec_delta=1)
    await quiet()
    assert acks[-1] is False and len(h.doorbells) == 1, "bad PEC"
    # R4 a write to a read-only register (STATE, word 0x02) with a correct PEC is NACKed and never commits
    acks = await h.doorbell(0x55, cmd=0x02)
    await quiet()
    assert acks[2] is False and len(h.doorbells) == 1, "write to a read-only register"
    # R5 a block write that claims 5 bytes but carries 4 (PEC correct over what was sent) never commits
    acks = await h.doorbell(0x66, count=5)
    await quiet()
    assert len(h.doorbells) == 1, "wrong byte count"
    # R6 another address is ignored: NACK, no commit
    acks = await h.doorbell(0x77, address=ADDR + 1)
    await quiet()
    assert acks[0] is False and len(h.doorbells) == 1, "wrong address"
    # R7 a complete write followed by a repeated start (then a read) never commits
    await h.doorbell(0x88, stop=False)
    v, pec_ok, _ = await h.block_read(0x00)
    await quiet()
    assert len(h.doorbells) == 1, "repeated start after the PEC"
    # R8 a write after a repeated start is refused, even with a PEC over every byte
    a = ADDR << 1
    await h.start()
    await h.write_byte(a)
    await h.write_byte(0x00)
    await h.start()
    body = [a, DOORBELL_CMD, 4, 1, 2, 3, 4]
    pec = crc8(bytes([a, 0x00] + body))
    acks = [await h.write_byte(b) for b in body + [pec]]
    await h.stop()
    await quiet()
    assert acks[0] is False and len(h.doorbells) == 1, "write after a repeated start"
    # R9 four stray clock bits after the PEC, then STOP: never commits
    await h.doorbell(0x99, stop=False)
    await h.write_byte(0xFF, bits=4)
    await h.stop()
    await quiet()
    assert len(h.doorbells) == 1, "stray bits after the PEC"
    # R10 the SMBus timeout: SCL held low mid-write past the limit kills the transaction
    await h.start()
    for b in [a, DOORBELL_CMD, 4, 0xDE, 0xAD]:
        await h.write_byte(b)
    before = h.timeouts
    await h.wait(TIMEOUT + 50)                            # SCL is low here
    assert h.timeouts == before + 1 and not ctx.get(t.sda_oe), "timeout fires and releases SDA"
    for b in [0xBE, 0xEF, crc8(bytes([a, DOORBELL_CMD, 4, 0xDE, 0xAD, 0xBE, 0xEF]))]:
        await h.write_byte(b)
    await h.stop()
    await quiet()
    assert len(h.doorbells) == 1, "a timed-out write never commits"
    # R11 the bus still works after all of that, and the target never stretched the clock
    v, pec_ok, _ = await h.block_read(0x41)
    assert v == WORD and pec_ok and ctx.get(t.csr_addr) == 0x104, "read after recovery"
    acks = await h.doorbell(0x0BADF00D)
    await quiet()
    assert h.doorbells == [0x11223344, 0x0BADF00D], "second good write"
    assert h.stretched == 0, "the target pulled SCL low"
    assert sda_driven_outside == 0, "the target drove SDA outside a transaction"


def test_protocol_battery_on_the_real_block():
    bus, t = bare()
    simulate(bus, t, battery)


def mutant_class(src_file, cls, old, new):
    src = open(os.path.join(ROOT, "rtl", "governor_rtl", src_file), encoding="utf-8").read()
    assert src.count(old) == 1, f"mutant text moved: {old!r}"
    ns = {"__name__": "mutant"}
    exec(compile(src.replace(old, new), src_file + " (mutant)", "exec"), ns)
    return ns[cls]


MUTANTS = [(d, o, n) for (src, cls, ms) in BLOCKS_FPGA.values() for (d, o, n) in ms]


@pytest.mark.parametrize("desc,old,new", MUTANTS, ids=[m[0][:40] for m in MUTANTS])
def test_every_formal_mutant_fails_a_concrete_bus_test(desc, old, new):
    src, cls, _ = BLOCKS_FPGA["smbus"]
    bus, t = bare(mutant_class(src, cls, old, new))
    with pytest.raises(AssertionError):
        simulate(bus, t, battery)


def test_random_line_noise_never_rings_the_doorbell_and_the_bus_recovers():
    bus, t = bare()

    async def body(ctx, h):
        ctx.set(t.csr_rdata, WORD)
        ctx.set(t.tick, 1)
        rng = random.Random(20261023)
        for _ in range(4000):                              # random SCL/SDA wiggles, held 1 to 20 cycles
            h.set(scl=rng.getrandbits(1), sda=rng.getrandbits(1))
            await h.wait(rng.randint(1, 20))
        await h.idle(TIMEOUT + 100)                        # whatever state it was left in times out or idles
        await h.stop()
        assert h.doorbells == [] and h.stretched == 0
        v, pec_ok, _ = await h.block_read(0x00)
        assert v == WORD and pec_ok

    simulate(bus, t, body)


def test_host_nack_ends_a_read_early_and_the_next_read_works():
    bus, t = bare()

    async def body(ctx, h):
        ctx.set(t.csr_rdata, WORD)
        ctx.set(t.tick, 1)
        await h.idle()
        a = ADDR << 1
        await h.start()
        await h.write_byte(a)
        await h.write_byte(0x00)
        await h.start()
        await h.write_byte(a | 1)
        count = await h.read_byte(True)
        lo = await h.read_byte(False)                      # NACK: the host wants no more
        await h.stop()
        assert (count, lo) == (4, WORD & 0xFF) and not ctx.get(t.sda_oe)
        v, pec_ok, _ = await h.block_read(0x00)
        assert v == WORD and pec_ok

    simulate(bus, t, body)


# ---- the target in front of the real governor core

def core_bus():
    g = GovernorSMBus(tick_div=1, timeout_ticks=TIMEOUT, cap_entries=2, ticket_entries=2)
    return Bus(g), g


def core_state(ctx, g):
    c = g.core
    return {"halt": ctx.get(c.halt.state), "cause": ctx.get(c.halt.cause), "life": ctx.get(c.life.state),
            "epoch": ctx.get(c.epoch.epoch), "meas0": ctx.get(c.meas0.value), "meas1": ctx.get(c.meas1.value),
            "mbox": ctx.get(c.mbox.status), "seq0": ctx.get(c.mbox.last_seq[0]), "alarms": ctx.get(c.alarms.alarms),
            "levers": (ctx.get(g.pwrbrk_n), ctx.get(g.perst_n), ctx.get(g.pwr_en), ctx.get(g.loop_out_open))}


def test_csr_window_reads_through_the_bus_and_the_doorbell_reaches_the_mailbox():
    bus, g = core_bus()

    async def body(ctx, h):
        await h.idle()
        v, ok, _ = await h.block_read(0x000 >> 2)
        assert v == 0x5347_0001 and ok                      # ID
        v, ok, _ = await h.block_read(0x008 >> 2)
        assert v == 0 and ok                                # STATE: HALTED_INITIAL
        v, ok, _ = await h.block_read(0x080 >> 2)
        assert v == 0b111 and ok                            # LEVERS: brake, PERST#, PWR_EN low
        v, ok, _ = await h.block_read(0x104 >> 2)
        assert v == 0 and ok                                # MBOX_STATUS idle
        lo1, _, _ = await h.block_read(0x070 >> 2)
        lo2, _, _ = await h.block_read(0x070 >> 2)
        assert lo2 > lo1                                    # MONO_LO moves (one tick per cycle here)
        acks = await h.doorbell(64)
        await h.wait(20)
        assert all(acks) and h.doorbells == [64]
        v, ok, _ = await h.block_read(0x104 >> 2)
        assert v == 4 and ok                                # the mailbox ran: bad sequence, no firmware behind it

    simulate(bus, g.smb, body)


def test_malformed_traffic_changes_no_register_in_the_core():
    bus, g = core_bus()

    async def body(ctx, h):
        await h.idle()
        before = core_state(ctx, g)
        a = ADDR << 1
        for word in list(range(0, 0x42)) + [0x80, 0x9F, 0xFF]:   # every decoded register and some that are not
            if word == DOORBELL_CMD:
                continue
            acks = await h.doorbell(0xFFFFFFFF, cmd=word)        # block write, correct PEC
            assert acks[2] is False
        for word in (0x00, 0x02, 0x03, 0x41, 0x42):
            acks = await h.raw_write([word, 0x01])               # SMBus Write Byte
            assert acks[2] is False
            acks = await h.raw_write([word, 0x01, 0x00])         # Write Word
            assert acks[2] is False
        await h.doorbell(1, pec_delta=0x80)                      # bad PEC
        await h.doorbell(1, stop=False)                          # complete, then cut by a repeated start
        await h.block_read(0x00)
        await h.start()
        await h.write_byte(a | 1)                                # a read with no command code: NACK
        await h.stop()
        await h.wait(20)
        assert h.doorbells == [] and h.stretched == 0
        assert core_state(ctx, g) == before

    simulate(bus, g.smb, body)


# ---- the bench script's frames are the frames the RTL accepts

def load_host_test():
    path = os.path.join(ROOT, "hw", "fpga", "host_test.py")
    spec = importlib.util.spec_from_file_location("host_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bench_script_frames_match_the_rtl():
    ht = load_host_test()
    bus, g = core_bus()

    async def body(ctx, h):
        await h.idle()
        # a read, exactly as host_test.py issues it with i2c_rdwr: write [cmd], repeated start, read 6
        wr, n = ht.read_frames(ht.REG["ID"])
        await h.start()
        assert await h.write_byte(ADDR << 1)
        for b in wr:
            assert await h.write_byte(b)
        await h.start()
        assert await h.write_byte((ADDR << 1) | 1)
        data = [await h.read_byte(i < n - 1) for i in range(n)]
        await h.stop()
        assert ht.parse_read(ADDR, ht.REG["ID"], bytes(data)) == 0x5347_0001
        bad = bytes(data[:-1] + [data[-1] ^ 1])
        with pytest.raises(ht.PECError):
            ht.parse_read(ADDR, ht.REG["ID"], bad)
        # the doorbell frame
        acks = await h.raw_write(list(ht.doorbell_frame(ADDR, 0x1234)))
        await h.wait(20)
        assert all(acks) and h.doorbells == [0x1234]
        # the script's deliberately malformed frames are refused
        for frame in ht.malformed_frames(ADDR):
            await h.raw_write(list(frame))
        await h.wait(20)
        assert h.doorbells == [0x1234]

    simulate(bus, g.smb, body)


def test_csr_addr_reaches_no_state_in_the_core():
    """The SMBus target's only other wire into the core, csr_addr, drives a read mux and nothing that
    remembers: in the synthesized governor_core no flip-flop sits in its fan-out cone. A planted register on
    csr_addr is found by the same check, so the check can fail."""
    import shutil
    import subprocess
    import tempfile
    yosys = os.path.join(os.path.dirname(sys.executable), "yowasp-yosys")
    if not os.path.exists(yosys):
        yosys = shutil.which("yowasp-yosys") or pytest.skip("yowasp-yosys not installed (pip install -e '.[dev]')")

    def ffs_fed_by_csr_addr(verilog_text):
        with tempfile.TemporaryDirectory() as w:
            open(os.path.join(w, "c.v"), "w").write(verilog_text)
            r = subprocess.run([yosys, "-q", "-p", "read_verilog c.v; prep -flatten -top governor_core; "
                                "select -set fo i:csr_addr %co*; "
                                "select -write hits.txt @fo t:$*dff* t:$*dlatch* t:$mem* %u %u %i"],
                               capture_output=True, text=True, cwd=w)
            assert r.returncode == 0, r.stderr[-400:]
            return [l for l in open(os.path.join(w, "hits.txt")).read().splitlines() if l.strip()]

    real = open(os.path.join(ROOT, "rtl", "gen", "governor_core.v"), encoding="utf-8").read()
    assert ffs_fed_by_csr_addr(real) == []
    start = real.index("module governor_core(")
    end = real.index("endmodule", start)
    planted = real[:end] + "  (* keep *) reg [11:0] spy;\n  always @(posedge clk) spy <= csr_addr;\n" + real[end:]
    assert ffs_fed_by_csr_addr(planted) != []


# ---- a finding the FPGA top exposed (not an SMBus bug; recorded, not fixed, because halt.py is not this branch's)

# FINDING F1 (hw/fpga/REPORT.md) fixed on fix/halt: RUN needs loop_sense & ~loop_lost. This was a strict xfail;
# it now passes and guards the fix.
def test_core_reaches_run_and_stays_there_with_the_sense_strobe_running_from_power_on():
    class OneGovernorLoop(GovernorSMBus):
        # a bench with one governor: our own switch closed is the loop current we sense, one cycle later
        def elaborate(self, platform):
            m = super().elaborate(platform)
            d = Signal()
            m.d.sync += d.eq(~self.core.loop_out_open)
            m.d.comb += self.loop_sense.eq(d)
            return m

    g = OneGovernorLoop(tick_div=1, sample_div=100, timeout_ticks=TIMEOUT, cap_entries=2, ticket_entries=2)

    async def tb(ctx):
        for _ in range(400):                              # power-on: four sense strobes with the switch open
            await ctx.tick()
        ctx.set(g.core.hb.window, 10_000)
        ctx.set(g.core.hb.hb_valid, 1)
        await ctx.tick()
        ctx.set(g.core.hb.hb_valid, 0)
        states = []
        for _ in range(1000):
            await ctx.tick()
            states.append(ctx.get(g.core.halt.state))
        assert 1 in states, "never reached RUN"
        first = states.index(1)
        assert all(s == 1 for s in states[first:]), f"left RUN: {sorted(set(states[first:]))}, cause {ctx.get(g.core.halt.cause)}"

    sim = Simulator(g)
    sim.add_clock(1e-6)
    sim.add_testbench(tb)
    sim.run()
