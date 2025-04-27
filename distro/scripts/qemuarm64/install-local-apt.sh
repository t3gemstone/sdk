#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

MACHINE="qemuarm64"
DISTRO_TYPE="${2:-minimal}"

echo "deb [trusted=yes] http://0.0.0.0:8000/${MACHINE} ./" | tee /etc/apt/sources.list.d/local-apt.list

apt-get update -y
apt-get install -y \
    kernel \
    kernel-image \
    kernel-module-configfs \
    kernel-module-fuse

if [[ "$DISTRO_TYPE" == "desktop" || "$DISTRO_TYPE" == "kiosk" ]]; then
    apt-get install -y \
        kernel-module-virtio-input
fi
