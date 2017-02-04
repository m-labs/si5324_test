#!/bin/sh -ex

rsync -avz . lab.m-labs.hk:si5324
ssh lab.m-labs.hk <<END
set -ex
export PATH=${HOME}/miniconda/bin:${PATH}
cd si5324
./si5324_test.py
openocd -f board/kc705.cfg -c '
  init
  jtagspi_init 0 {${HOME}/.migen/bscan_spi_xc7k325t.bit}
  jtagspi_program {/tmp/si5324_test/top.bin} 0x000000
  xc7_program xc7.tap
  exit
'
END
