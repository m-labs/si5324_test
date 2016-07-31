#!/usr/bin/env python3.5

import os, argparse

from migen import *
from migen.build.generic_platform import *
from migen.build.platforms import kc705
from migen.build.xilinx.vivado import XilinxVivadoToolchain
from migen.build.xilinx.ise import XilinxISEToolchain

from misoc.targets.kc705 import _CRG

from sequencer import *
from i2c import *


class Si5324ClockRouting(Module):
    def __init__(self, platform):
        si5324_reset    = platform.request("si5324").rst_n
        si5324_clkin    = platform.request("si5324_clkin")
        si5324_clkout   = platform.request("si5324_clkout")
        user_sma_gpio_p = platform.request("user_sma_gpio_p")
        user_sma_gpio_n = platform.request("user_sma_gpio_n")

        self.comb += [
            si5324_reset.eq(~ResetSignal("sys")),
        ]

        dirty_clk = ClockSignal("sys")
        self.specials += [
            Instance("OBUFDS",
                     i_I=dirty_clk,
                     o_O=si5324_clkin.p, o_OB=si5324_clkin.n),
            Instance("OBUF",
                     i_I=dirty_clk,
                     o_O=user_sma_gpio_n)
        ]

        clean_clk = Signal()
        clean_clk2 = Signal()
        self.specials += [
            Instance("IBUFDS_GTE2",
                     i_I=si5324_clkout.p, i_IB=si5324_clkout.n,
                     o_O=clean_clk),
            Instance("BUFG",
                     i_I=clean_clk,
                     o_O=clean_clk2),
            Instance("OBUF",
                     i_I=clean_clk2,
                     o_O=user_sma_gpio_p)
        ]


class Si5324CRG(Module):
    def __init__(self, platform):
        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_clk200 = ClockDomain()

        clk200 = platform.request("clk200")
        clk200_se = Signal()
        self.specials += Instance("IBUFDS", i_I=clk200.p, i_IB=clk200.n, o_O=clk200_se)

        pll_locked = Signal()
        pll_fb = Signal()
        pll_sys = Signal()
        pll_clk200 = Signal()
        self.specials += [
            Instance("PLLE2_BASE",
                     p_STARTUP_WAIT="FALSE", o_LOCKED=pll_locked,

                     # VCO @ 1GHz
                     p_REF_JITTER1=0.01, p_CLKIN1_PERIOD=5.0,
                     p_CLKFBOUT_MULT=5, p_DIVCLK_DIVIDE=1,
                     i_CLKIN1=clk200_se, i_CLKFBIN=pll_fb, o_CLKFBOUT=pll_fb,

                     # 125MHz
                     p_CLKOUT0_DIVIDE=8, p_CLKOUT0_PHASE=0.0, o_CLKOUT0=pll_sys,

                     # 200MHz
                     p_CLKOUT1_DIVIDE=5, p_CLKOUT1_PHASE=0.0, o_CLKOUT1=pll_clk200,
            ),
            Instance("BUFG", i_I=pll_sys, o_O=self.cd_sys.clk),
            Instance("BUFG", i_I=pll_clk200, o_O=self.cd_clk200.clk),
        ]

        self.freq = 125e6

        reset_ctr = Signal(32, reset=int(self.freq / 20e3)) # 20ms
        reset = Signal(reset=1)
        self.sync.clk200 += [
            If(reset_ctr != 0,
                reset_ctr.eq(reset_ctr - 1),
            ).Else(
                reset.eq(0),
            ),
        ]
        self.specials += [
            Instance("BUFG", i_I=reset, o_O=self.cd_sys.rst),
        ]


class Si5324Test(Module):
    def __init__(self, platform):
        self.platform = platform
        self.platform.add_extension([
            ("i2c_debug", 0, Pins("XADC:GPIO0 XADC:GPIO1"), IOStandard("LVCMOS25")),
        ])

        if isinstance(self.platform.toolchain, XilinxVivadoToolchain):
            self.platform.toolchain.bitstream_commands.extend([
                "set_property BITSTREAM.GENERAL.COMPRESS True [current_design]",
            ])
        if isinstance(self.platform.toolchain, XilinxISEToolchain):
            self.platform.toolchain.bitgen_opt += " -g compress"

        self.submodules.crg = Si5324CRG(self.platform)
        clk_freq = self.crg.freq

        self.submodules.si5324_clock_routing = Si5324ClockRouting(self.platform)

        i2c = self.platform.request("i2c")
        self.submodules.i2c_master = I2CMaster(i2c)

        i2c_debug = self.platform.request("i2c_debug")
        self.comb += [
            i2c_debug[0].eq(self.i2c_master.scl_t.i),
            i2c_debug[1].eq(self.i2c_master.sda_t.i),
        ]

        # NOTE: the logical parameters DO NOT MAP to physical values written
        # into registers. They have to be mapped; see the datasheet.
        # DSPLLsim reports the logical parameters in the design summary, not
        # the physical register values (but those are present separately).
        if clk_freq == 125e6:
            N1_HS  = 1   # 5
            NC1_LS = 7   # 8
            N2_HS  = 3   # 7
            N2_LS  = 359 # 360
            N31    = 62
        else:
            assert False

        # Select channel 7 of PCA9548
        i2c_sequence = [
            [(0x74 << 1), 1 << 7],
            [(0x68 << 1), 2,   0b0010 | (4 << 4)], # BWSEL=4
            [(0x68 << 1), 3,   0b0101 | 0x10],     # SQ_ICAL=1
            [(0x68 << 1), 6,            0x07],     # SFOUT1_REG=b111
            [(0x68 << 1), 25,  (N1_HS  << 5 ) & 0xff],
            [(0x68 << 1), 31,  (NC1_LS >> 16) & 0xff],
            [(0x68 << 1), 32,  (NC1_LS >> 8 ) & 0xff],
            [(0x68 << 1), 33,  (NC1_LS)       & 0xff],
            [(0x68 << 1), 40,  (N2_HS  << 5 ) & 0xff |
                               (N2_LS  >> 16) & 0xff],
            [(0x68 << 1), 41,  (N2_LS  >> 8 ) & 0xff],
            [(0x68 << 1), 42,  (N2_LS)        & 0xff],
            [(0x68 << 1), 43,  (N31    >> 16) & 0xff],
            [(0x68 << 1), 44,  (N31    >> 8)  & 0xff],
            [(0x68 << 1), 45,  (N31)          & 0xff],
            [(0x68 << 1), 137,          0x01],     # FASTLOCK=1
            [(0x68 << 1), 136,          0x40],     # ICAL=1
        ]

        program = [
            InstWrite(I2C_CONFIG_ADDR, int(clk_freq / 1e3)),
        ]
        for subseq in i2c_sequence:
            program += [
                InstWrite(I2C_XFER_ADDR, I2C_START),
                InstWait(I2C_XFER_ADDR, I2C_IDLE),
            ]
            for octet in subseq:
                program += [
                    InstWrite(I2C_XFER_ADDR, I2C_WRITE | octet),
                    InstWait(I2C_XFER_ADDR, I2C_IDLE),
                ]
            program += [
                InstWrite(I2C_XFER_ADDR, I2C_STOP),
                InstWait(I2C_XFER_ADDR, I2C_IDLE),
            ]
        program += [
            InstEnd(),
        ]
        self.submodules.sequencer = Sequencer(program, self.i2c_master.bus)


if __name__ == "__main__":
    platform = kc705.Platform()
    top = Si5324Test(platform)
    platform.build(top, build_dir="/tmp/si5324_test")

