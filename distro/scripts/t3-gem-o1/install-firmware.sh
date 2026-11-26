#!/bin/bash

set -euo pipefail

WORKDIR="$1"
ROOTDIR="$2"

"$WORKDIR/src/gemstone-firmware/copy-firmware.sh" "$ROOTDIR/lib/firmware"

cp -ar "$WORKDIR/src/ti-img-rogue-umlibs/targetfs/j721s2_linux/lws-generic/release/etc/"* "$ROOTDIR/etc"
cp -ar "$WORKDIR/src/ti-img-rogue-umlibs/targetfs/j721s2_linux/lws-generic/release/usr/"* "$ROOTDIR/usr"
cp -ar "$WORKDIR/src/ti-img-rogue-umlibs/targetfs/j721s2_linux/lws-generic/release/lib/"* "$ROOTDIR/lib"
