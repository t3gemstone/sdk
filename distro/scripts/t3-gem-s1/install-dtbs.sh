#!/bin/bash

set -euo pipefail

WORKDIR="$1"
ROOTDIR="$2"

DIR_IMGS="$WORKDIR/build/t3-gem-s1/deploy-ti/images/t3-gem-s1"

mkdir -p "$ROOTDIR/boot/overlays"
cp "$DIR_IMGS/tiboot3.bin" "$ROOTDIR/boot"
cp "$DIR_IMGS/k3-am67a-t3-gem-s1.dtb" "$ROOTDIR/boot/"
cp "$DIR_IMGS/gemstone-image-rd-t3-gem-s1.cpio.gz" "$ROOTDIR/boot/"
find "$DIR_IMGS" -name '*.dtbo' -type f -exec cp {} "$ROOTDIR/boot/overlays" \;
