#!/bin/sh -ex

rsync -avz . lab.m-labs.hk:si5324
ssh lab.m-labs.hk '
set -ex
export PATH=${HOME}/miniconda/bin:${PATH}
cd si5324
./i2c_test.py
'
scp lab.m-labs.hk:/tmp/i2c_test/top.bit top.bit
xc3sprog -c ftdi top.bit
