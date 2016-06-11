#!/usr/bin/env python3.5

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
        si5324_clkin    = self.platform.request("si5324_clkin")
        si5324_clkout   = self.platform.request("si5324_clkout")
        user_sma_gpio_p = self.platform.request("user_sma_gpio_p")

        clean_clk = Signal()
        self.specials += [
            Instance("OBUFDS",
                     i_I=self.cd_sys.clk,
                     o_O=si5324_clkin.p, o_OB=si5324_clkin.n),
            Instance("IBUFDS",
                     i_I=si5324_clkout.p, i_IB=si5324_clkout.n,
                     o_O=clean_clk),
            Instance("OBUF",
                     i_I=clean_clk,
                     o_O=user_sma_gpio_p)
        ]

class Si5324Test(BaseSoC):
    csr_map = {
        "i2c": 20,
        "si5324_rst_n": 21
    }
    csr_map.update(BaseSoC.csr_map)

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

        si5324 = self.platform.request("si5324", 0)
        self.submodules.si5324_rst_n = gpio.GPIOOut(si5324.rst_n)

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
