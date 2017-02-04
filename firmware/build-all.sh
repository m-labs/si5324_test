#!/bin/sh -ex

rsync -avz . lab.m-labs.hk:si5324
ssh -tt lab.m-labs.hk <<END
set -ex
export PATH=${HOME}/miniconda/bin:${PATH}
cd si5324
./si5324_test.py
openocd -f board/kc705.cfg -c '
  init
  jtagspi_init 0 {${HOME}/.migen/bscan_spi_xc7k325t.bit}
  jtagspi_program {misoc_si5324test_kc705/gateware/top.bin} 0x000000
  jtagspi_program {misoc_si5324test_kc705/software/bios/bios.bin} 0xaf0000
  jtagspi_program {misoc_si5324test_kc705/software/runtime/runtime.bin} 0xb00000
  xc7_program xc7.tap
  exit
'
flterm /dev/ttyUSB0 --kernel misoc_si5324test_kc705/software/runtime/runtime.bin
END
