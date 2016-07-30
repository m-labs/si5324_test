#!/bin/sh -ex

rsync -avz . lab.m-labs.hk:si5324
ssh -tt lab.m-labs.hk <<END
set -ex
cd si5324
./i2c_test.py
END
scp lab.m-labs.hk:/tmp/i2c_test/top.bin top.bin
openocd -f board/pipistrello.cfg -c '
  init
  jtagspi_init 0 {${HOME}/.migen/bscan_spi_xc6slx45.bit}
  jtagspi_program {top.bin} 0x000000
  xc6s_program xc6s.tap
  exit
'
