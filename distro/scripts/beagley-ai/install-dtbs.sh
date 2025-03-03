#!/bin/bash

set -euo pipefail

WORKDIR="$1"
ROOTDIR="$2"

DIR_IMGS="$WORKDIR/build/beagley-ai/deploy-ti/images/beagley-ai"

mkdir -p "$ROOTDIR/boot/overlays"
cp "$DIR_IMGS/tiboot3.bin" "$ROOTDIR/boot"
cp "$DIR_IMGS/k3-am67a-beagley-ai.dtb" "$ROOTDIR/boot/"
cp "$DIR_IMGS/gemstone-image-rd-beagley-ai.cpio.gz" "$ROOTDIR/boot/"
find "$DIR_IMGS" -name '*.dtbo' -type f -exec cp {} "$ROOTDIR/boot/overlays" \;
