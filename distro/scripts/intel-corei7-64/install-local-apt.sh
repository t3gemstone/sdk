#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

MACHINE="corei7-64-intel-common"
DISTRO_TYPE="${2:-minimal}"

echo "deb [trusted=yes] http://0.0.0.0:8000/${MACHINE} ./" | tee /etc/apt/sources.list.d/local-apt.list

apt-get update -y
apt-get install -y \
    kernel \
    kernel-image \
    kernel-module-configfs \
    kernel-module-fuse \
    kernel-module-squashfs

if [[ "$DISTRO_TYPE" == "desktop" || "$DISTRO_TYPE" == "gui" ]]; then
    apt-get install -y \
        kernel-module-cirrus \
        kernel-module-drm-display-helper \
        kernel-module-usbtouchscreen \
        kernel-module-video \
        kernel-module-virtio-input
fi
