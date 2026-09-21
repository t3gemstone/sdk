#!/bin/bash

# Installs TI's mesa-pvr into an isolated prefix. Nothing in the image links
# against it by default -- the rootfs keeps its own Mesa and its Xorg session --
# so applications opt in through /usr/local/bin/gem-gpu-run.
#
# Built by: task graphics:build MACHINE=t3-gem-o1

set -euo pipefail

WORKDIR="$1"
ROOTDIR="$2"

GPU_PREFIX="$WORKDIR/build/graphics/t3-gem-o1/opt/ti-gpu"

if [ ! -f "$GPU_PREFIX/lib/dri/pvr_dri.so" ]; then
    echo "ERROR: $GPU_PREFIX/lib/dri/pvr_dri.so missing." >&2
    echo "       Run 'task graphics:build MACHINE=t3-gem-o1' first." >&2
    exit 1
fi

mkdir -p "$ROOTDIR/opt"
cp -ar "$GPU_PREFIX" "$ROOTDIR/opt/"
