#!/bin/bash

set -euo pipefail

BOOTFILES="$1"
ROOTDIR="$2"

# Replace the bootloader installed from the apt repository with locally built binaries
cd "$BOOTFILES"
sha256sum -c SHA256SUMS

for f in tiboot3.bin tispl.bin u-boot.img; do
    cp "$f" "$ROOTDIR/boot/$f"
done

sha256sum "$ROOTDIR/boot/tiboot3.bin" "$ROOTDIR/boot/tispl.bin" "$ROOTDIR/boot/u-boot.img"
