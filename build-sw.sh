#!/bin/sh -ex

rsync -avz . lab.m-labs.hk:si5324
ssh -tt lab.m-labs.hk <<END
set -ex
export PATH=${HOME}/miniconda/bin:${PATH}
cd si5324
./si5324_test.py --no-compile-gateware
openocd -f board/kc705.cfg -c '
  init
  xc7_program xc7.tap
  exit
'
flterm /dev/ttyUSB0 --kernel misoc_si5324test_kc705/software/runtime/runtime.bin
END
