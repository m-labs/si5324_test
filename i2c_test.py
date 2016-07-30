#!/usr/bin/env python3.5

import os, argparse
from fractions import Fraction

from migen import *
from migen.build.generic_platform import *
from migen.build.platforms import pipistrello
from misoc.integration.builder import Builder, builder_args, builder_argdict

from sequencer import *
from i2c import *


class _PLL(Module):
    def __init__(self, platform, clk_freq):
        self.clock_domains.cd_sys = ClockDomain()

        f0 = Fraction(50, 1)*1000000
        p = 12
        f = Fraction(clk_freq*p, f0)
        n, d = f.numerator, f.denominator
        assert 19e6 <= f0/d <= 500e6  # pfd
        assert 400e6 <= f0*n/d <= 1080e6  # vco

        clk50 = platform.request("clk50")
        clk50a = Signal()
        self.specials += Instance("IBUFG", i_I=clk50, o_O=clk50a)
        clk50b = Signal()
        self.specials += Instance("BUFIO2", p_DIVIDE=1,
                                  p_DIVIDE_BYPASS="TRUE", p_I_INVERT="FALSE",
                                  i_I=clk50a, o_DIVCLK=clk50b)
        pll_lckd = Signal()
        pll_fb = Signal()
        pll = Signal(6)
        self.specials.pll = Instance("PLL_ADV", p_SIM_DEVICE="SPARTAN6",
                                     p_BANDWIDTH="OPTIMIZED", p_COMPENSATION="INTERNAL",
                                     p_REF_JITTER=.01, p_CLK_FEEDBACK="CLKFBOUT",
                                     i_DADDR=0, i_DCLK=0, i_DEN=0, i_DI=0, i_DWE=0, i_RST=0, i_REL=0,
                                     p_DIVCLK_DIVIDE=d, p_CLKFBOUT_MULT=n, p_CLKFBOUT_PHASE=0.,
                                     i_CLKIN1=clk50b, i_CLKIN2=0, i_CLKINSEL=1,
                                     p_CLKIN1_PERIOD=1e9/f0, p_CLKIN2_PERIOD=0.,
                                     i_CLKFBIN=pll_fb, o_CLKFBOUT=pll_fb, o_LOCKED=pll_lckd,
                                     o_CLKOUT0=pll[0], p_CLKOUT0_DUTY_CYCLE=.5,
                                     o_CLKOUT1=pll[1], p_CLKOUT1_DUTY_CYCLE=.5,
                                     o_CLKOUT2=pll[2], p_CLKOUT2_DUTY_CYCLE=.5,
                                     o_CLKOUT3=pll[3], p_CLKOUT3_DUTY_CYCLE=.5,
                                     o_CLKOUT4=pll[4], p_CLKOUT4_DUTY_CYCLE=.5,
                                     o_CLKOUT5=pll[5], p_CLKOUT5_DUTY_CYCLE=.5,
                                     p_CLKOUT0_PHASE=0., p_CLKOUT0_DIVIDE=p//4,  # sdram wr rd
                                     p_CLKOUT1_PHASE=0., p_CLKOUT1_DIVIDE=p//4,
                                     p_CLKOUT2_PHASE=270., p_CLKOUT2_DIVIDE=p//2,  # sdram dqs adr ctrl
                                     p_CLKOUT3_PHASE=250., p_CLKOUT3_DIVIDE=p//2,  # off-chip ddr
                                     p_CLKOUT4_PHASE=0., p_CLKOUT4_DIVIDE=p//1,
                                     p_CLKOUT5_PHASE=0., p_CLKOUT5_DIVIDE=p//1,  # sys
        )
        self.specials += Instance("BUFG", i_I=pll[5], o_O=self.cd_sys.clk)


class I2CTest(Module):
    def __init__(self, platform):
        self.platform = platform
        self.platform.add_extension([
            ("i2c", 0,
                Subsignal("scl", Pins("A:0")),
                Subsignal("sda", Pins("A:1")),
                IOStandard("LVTTL"), Misc("PULLUP"),
            ),
        ])

        self.submodules.pll = _PLL(platform, Fraction(62.5e6))

        i2c = self.platform.request("i2c")
        self.submodules.i2c_master = I2CMaster(i2c)

        program = [
            InstWrite(I2C_CONFIG_ADDR, 62.5e3),
            InstEnd(),
        ]
        self.submodules.sequencer = Sequencer(program, self.i2c_master.bus)


if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.abspath(__file__))

    platform = pipistrello.Platform()
    top = I2CTest(platform)
    # from migen.fhdl.verilog import convert
    # print(convert(top, platform.constraint_manager.get_io_signals()))
    platform.build(top, build_dir="/tmp/i2c_test")
