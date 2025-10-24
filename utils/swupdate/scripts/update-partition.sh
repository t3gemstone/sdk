#!/bin/sh
set -e

slot="$1"

echo "Slot '$slot' is given."

if [ "$slot" != 'A' ] && [ "$slot" != 'B' ]; then
    echo "Invalid slot info"
    exit 1
fi

udevadm trigger && sleep 2

if ! btrfs filesystem label "/dev/disk/by-label/root" "ROOTFS_${slot}"; then
    echo "Unable to rename partition"
    exit 1
fi

udevadm trigger && sleep 2

sudo btrfstune -f -u "/dev/disk/by-label/ROOTFS_${slot}"

udevadm trigger && sleep 2

mntdir="/tmp/$(uuidgen)"

mkdir -p "$mntdir" \
    && mount -t btrfs "/dev/disk/by-label/ROOTFS_${slot}" "$mntdir" \
    && btrfs filesystem resize max "$mntdir" \
    && umount "$mntdir" \
    && udevadm trigger \
|| { echo "Unable to resize rootfs"; exit 1; }
