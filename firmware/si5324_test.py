#!/usr/bin/env python3

import os, argparse

from migen import *
from migen.build.platforms import kc705
from migen.build.xilinx.vivado import XilinxVivadoToolchain
from migen.build.xilinx.ise import XilinxISEToolchain
from misoc.cores import gpio
from misoc.targets.kc705 import BaseSoC, soc_kc705_args, soc_kc705_argdict
from misoc.integration.builder import Builder, builder_args, builder_argdict

class Si5324ClockRouting(Module):
    def __init__(self, platform):
        si5324_clkin = platform.request("si5324_clkin")
        si5324_clkout = platform.request("si5324_clkout")
        user_sma_clock_p = platform.request("user_sma_clock_p")
        user_sma_clock_n = platform.request("user_sma_clock_n")

        dirty_clk = ClockSignal("sys") # 125MHz
        self.specials += [
            Instance("OBUFDS",
                     i_I=dirty_clk,
                     o_O=si5324_clkin.p, o_OB=si5324_clkin.n),
            Instance("OBUF",
                     i_I=dirty_clk,
                     o_O=user_sma_clock_p)
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
                     o_O=user_sma_clock_n)
        ]

class Si5324Test(BaseSoC):
    def __init__(self, cpu_type="or1k", **kwargs):
        BaseSoC.__init__(self,
                         cpu_type=cpu_type,
                         sdram_controller_type="minicon",
                         l2_size=128*1024,
                         with_timer=True,
                         ident="Si5324 test SoC",
                         **kwargs)
        if isinstance(self.platform.toolchain, XilinxVivadoToolchain):
            self.platform.toolchain.bitstream_commands.extend([
                "set_property BITSTREAM.GENERAL.COMPRESS True [current_design]",
            ])
        if isinstance(self.platform.toolchain, XilinxISEToolchain):
            self.platform.toolchain.bitgen_opt += " -g compress"

        self.submodules.leds = gpio.GPIOOut(Cat(
            self.platform.request("user_led", 0),
            self.platform.request("user_led", 1)))

        i2c = self.platform.request("i2c")
        self.submodules.i2c = gpio.GPIOTristate([i2c.scl, i2c.sda])
        self.csr_devices.append("i2c")

        si5324 = self.platform.request("si5324", 0)
        self.submodules.si5324_rst_n = gpio.GPIOOut(si5324.rst_n)
        self.csr_devices.append("si5324_rst_n")

        self.submodules.si5324_clock_routing = Si5324ClockRouting(self.platform)

if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(
        description="Si5324 test SoC")
    builder_args(parser)
    soc_kc705_args(parser)
    args = parser.parse_args()

    soc = Si5324Test(**soc_kc705_argdict(args))
    builder = Builder(soc, **builder_argdict(args))
    builder.add_software_package("runtime", os.path.join(root_dir, "runtime"))
    builder.build()
