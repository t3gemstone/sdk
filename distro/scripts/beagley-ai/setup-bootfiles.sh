#!/bin/bash

set -euo pipefail

cd /boot

find . -maxdepth 1 -type l -ls -exec rm {} \; >/dev/null

mv uEnv-* uEnv.txt
mv tispl.bin-* tispl.bin
mv u-boot-*.img u-boot.img
mv Image-* Image

rm fitImage*
rm u-boot-spl*
