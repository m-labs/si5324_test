from migen import *
from misoc.interconnect import wishbone


__all__ = [
    "I2CMaster",
    "I2C_XFER_ADDR", "I2C_CONFIG_ADDR",
    "I2C_ACK", "I2C_READ", "I2C_WRITE", "I2C_STOP", "I2C_START", "I2C_IDLE",
]


class I2CClockGen(Module):
    def __init__(self, width):
        self.load  = Signal(width)
        self.clk2x = Signal()

        cnt = Signal.like(self.load)
        self.comb += [
            self.clk2x.eq(cnt == 0),
        ]
        self.sync += [
            If(self.clk2x,
                cnt.eq(self.load),
            ).Else(
                cnt.eq(cnt - 1),
            ),
        ]


class I2CMasterMachine(Module):
    def __init__(self, clock_width):
        self.scl_o = Signal(reset=1)
        self.sda_o = Signal(reset=1)
        self.sda_i = Signal()

        self.submodules.cg  = CEInserter()(I2CClockGen(clock_width))
        self.idle  = Signal()
        self.start = Signal()
        self.stop  = Signal()
        self.write = Signal()
        self.read  = Signal()
        self.ack   = Signal()
        self.data  = Signal(8)

        ###

        busy = Signal()
        bits = Signal(4)

        fsm = CEInserter()(FSM("IDLE"))
        self.submodules += fsm

        fsm.act("IDLE",
            If(self.start,
                NextState("START0"),
            ).Elif(self.stop & self.start,
                NextState("RESTART0"),
            ).Elif(self.stop,
                NextState("STOP0"),
            ).Elif(self.write,
                NextValue(bits, 8),
                NextState("WRITE0"),
            ).Elif(self.read,
                NextValue(bits, 8),
                NextState("READ0"),
            )
        )

        fsm.act("START0",
            NextValue(self.scl_o, 1),
            NextState("START1"))
        fsm.act("START1",
            NextValue(self.sda_o, 0),
            NextState("IDLE"))

        fsm.act("RESTART0",
            NextValue(self.scl_o, 0),
            NextState("RESTART1"))
        fsm.act("RESTART1",
            NextValue(self.sda_o, 1),
            NextState("START0"))

        fsm.act("STOP0",
            NextValue(self.scl_o, 0),
            NextState("STOP1"))
        fsm.act("STOP1",
            NextValue(self.scl_o, 1),
            NextValue(self.sda_o, 0),
            NextState("STOP2"))
        fsm.act("STOP2",
            NextValue(self.sda_o, 1),
            NextState("IDLE"))

        fsm.act("WRITE0",
            NextValue(self.scl_o, 0),
            If(bits == 0,
                NextValue(self.sda_o, 1),
                NextState("READACK0"),
            ).Else(
                NextValue(self.sda_o, self.data[7]),
                NextState("WRITE1"),
            )
        )
        fsm.act("WRITE1",
            NextValue(self.scl_o, 1),
            NextValue(self.data[1:], self.data[:-1]),
            NextValue(bits, bits - 1),
            NextState("WRITE0"),
        )
        fsm.act("READACK0",
            NextValue(self.scl_o, 1),
            NextState("READACK1"),
        )
        fsm.act("READACK1",
            NextValue(self.ack, ~self.sda_i),
            NextState("IDLE")
        )

        fsm.act("READ0",
            NextValue(self.scl_o, 0),
            NextState("READ1"),
        )
        fsm.act("READ1",
            NextValue(self.data[0], self.sda_i),
            NextValue(self.scl_o, 0),
            If(bits == 0,
                NextValue(self.sda_o, ~self.ack),
                NextState("WRITEACK0"),
            ).Else(
                NextValue(self.sda_o, 1),
                NextState("READ2"),
            )
        )
        fsm.act("READ2",
            NextValue(self.scl_o, 1),
            NextValue(self.data[:-1], self.data[1:]),
            NextValue(bits, bits - 1),
            NextState("READ1"),
        )
        fsm.act("WRITEACK0",
            NextValue(self.scl_o, 1),
            NextState("IDLE"),
        )

        run = Signal()
        self.comb += [
            run.eq(self.start | self.stop | self.write | self.read),
            self.idle.eq(~run & fsm.ongoing("IDLE")),
            self.cg.ce.eq(~self.idle),
            fsm.ce.eq(run | self.cg.clk2x),
        ]


class I2CMaster(Module):
    def __init__(self, pads, bus=None):
        if bus is None:
            bus = wishbone.Interface(data_width=32)
        self.bus = bus

        ###

        # Wishbone
        config = Record([
            ("div",   20),
        ])
        assert len(config) <= len(bus.dat_w)

        xfer = Record([
            ("data",  8),
            ("ack",   1),
            ("read",  1),
            ("write", 1),
            ("stop",  1),
            ("start", 1),
            ("idle",  1),
        ])
        assert len(xfer) <= len(bus.dat_w)

        registers = Array([
            xfer.raw_bits(),
            config.raw_bits()
        ])

        self.submodules.i2c = i2c = I2CMasterMachine(
            clock_width=len(config.div))

        self.comb += [
            bus.dat_r.eq(registers[bus.adr]),
            i2c.cg.load.eq(config.div),
        ]
        self.sync += [
            bus.ack.eq(0),
            If(bus.cyc & bus.stb & ~bus.ack,
                bus.ack.eq(1)
            ),
            If(bus.cyc & bus.stb & bus.we,
                registers[bus.adr].eq(bus.dat_w),
            ),
            If(bus.ack & bus.we,
                i2c.start.eq(xfer.start),
                i2c.stop.eq(xfer.stop),
                i2c.write.eq(xfer.write),
                i2c.read.eq(xfer.read),
                i2c.ack.eq(xfer.ack),
                i2c.data.eq(xfer.data),
            ).Else(
                i2c.start.eq(0),
                i2c.stop.eq(0),
                i2c.write.eq(0),
                i2c.read.eq(0),
                xfer.ack.eq(i2c.ack),
                xfer.data.eq(i2c.data),
            ),
            xfer.idle.eq(i2c.idle),
        ]

        # I/O
        scl_t = TSTriple()
        self.specials += scl_t.get_tristate(pads.scl)
        self.comb += [
            scl_t.oe.eq(1),
            scl_t.o.eq(i2c.scl_o),
        ]

        sda_t = TSTriple()
        self.specials += sda_t.get_tristate(pads.sda)
        self.comb += [
            sda_t.oe.eq(~i2c.sda_o),
            sda_t.o.eq(0),
            i2c.sda_i.eq(sda_t.i),
        ]

# Testbench

I2C_XFER_ADDR, I2C_CONFIG_ADDR = range(2)
(
    I2C_ACK,
    I2C_READ,
    I2C_WRITE,
    I2C_STOP,
    I2C_START,
    I2C_IDLE,
) = (1 << i for i in range(8, 14))


def I2C_DIV_WRITE(i):
    return i


def _test_read(bus):
    while not ((yield from bus.read(I2C_XFER_ADDR)) & I2C_IDLE):
        pass
    return (yield from bus.read(I2C_XFER_ADDR))

def _test_gen(bus):
    yield from bus.write(I2C_CONFIG_ADDR, I2C_DIV_WRITE(4))
    yield from bus.write(I2C_XFER_ADDR, I2C_START)
    yield from _test_read(bus)
    yield from bus.write(I2C_XFER_ADDR, I2C_WRITE | 0x40)
    yield from _test_read(bus)
    yield from bus.write(I2C_XFER_ADDR, I2C_WRITE | 0x05)
    yield from _test_read(bus)
    yield from bus.write(I2C_XFER_ADDR, I2C_STOP | I2C_START)
    yield from _test_read(bus)
    yield from bus.write(I2C_XFER_ADDR, I2C_WRITE | 0x81)
    yield from _test_read(bus)
    yield from bus.write(I2C_XFER_ADDR, I2C_READ | I2C_ACK)
    yield from _test_read(bus)
    yield from bus.write(I2C_XFER_ADDR, I2C_READ)
    yield from _test_read(bus)
    yield from bus.write(I2C_XFER_ADDR, I2C_STOP)
    yield from _test_read(bus)


class _TestPads:
    def __init__(self):
        self.scl = Signal()
        self.sda = Signal()


class _TestTristate(Module):
    def __init__(self, t):
        oe = Signal()
        self.comb += [
            t.target.eq(t.o),
            oe.eq(t.oe),
            t.i.eq(t.o),
        ]


if __name__ == "__main__":
    from migen.fhdl.specials import Tristate

    pads = _TestPads()
    dut = I2CMaster(pads)

    Tristate.lower = _TestTristate
    run_simulation(dut, _test_gen(dut.bus), vcd_name="i2c_master.vcd")

