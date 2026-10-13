#!/usr/bin/env bash
set -Eeuo pipefail

WORKDIR="${WORKDIR:-/home/workdir}"
MACHINE="${MACHINE:-t3-gem-o1}"
JOBS="${JOBS:-8}"
IMAGE_SIZE="${IMAGE_SIZE:-16G}"

cd "$WORKDIR"

echo "[1/4] Static integration verification"
task distro:verify:wayland WORKDIR="$WORKDIR"

echo "[2/4] Resuming Yocto boot/rootfs build (sstate and completed tasks are reused)"
export BB_NUMBER_THREADS="$JOBS"
export PARALLEL_MAKE="-j $JOBS"
task yocto:build MACHINE="$MACHINE" WORKDIR="$WORKDIR"

echo "[3/4] Building the PowerVR Plasma Wayland disk image"
task distro:build:wayland:t3-gem-o1 WORKDIR="$WORKDIR" IMG_SIZE="$IMAGE_SIZE"

echo "[4/4] Listing deliverables"
find "$WORKDIR/build" "$WORKDIR/output" "$WORKDIR/dist" \
  -maxdepth 4 -type f \
  \( -name '*.img' -o -name '*.img.xz' -o -name '*.wic' -o -name '*.wic.*' \) \
  -printf '%s bytes  %p\n' 2>/dev/null | sort -n || true

