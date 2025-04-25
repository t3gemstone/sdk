#!/bin/bash

set -euo pipefail

WORKDIR="$1"
ROOTDIR="$2"

mkdir -p "$ROOTDIR/lib/firmware/ti-connectivity"
cp -f "$WORKDIR/src/wl18xx-fw/"*.bin "$ROOTDIR/lib/firmware/ti-connectivity"

cp -ar "$WORKDIR/src/ti-img-rogue-umlibs/targetfs/j721s2_linux/lws-generic/release/etc/"* "$ROOTDIR/etc"
cp -ar "$WORKDIR/src/ti-img-rogue-umlibs/targetfs/j721s2_linux/lws-generic/release/usr/"* "$ROOTDIR/usr"
cp -ar "$WORKDIR/src/ti-img-rogue-umlibs/targetfs/j721s2_linux/lws-generic/release/lib/"* "$ROOTDIR/lib"
