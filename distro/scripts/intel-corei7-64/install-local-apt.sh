#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

MACHINE="corei7-64-intel-common"
DISTRO_TYPE="${2:-minimal}"
CI="$3"

if [ "$CI" = "true" ]; then
    mkdir -p /etc/apt/sources.list.d
    mkdir -p /etc/apt/keyrings

    curl -fsSL https://packages.t3gemstone.org/apt/gemstone-packages-keyring.gpg -o /etc/apt/keyrings/gemstone-packages-keyring.gpg

    echo "deb [signed-by=/etc/apt/keyrings/gemstone-packages-keyring.gpg] https://packages.t3gemstone.org/apt/intel-corei7-64 jammy main" | tee /etc/apt/sources.list.d/gemstone.list
else
    echo "deb [trusted=yes] http://0.0.0.0:8000/${MACHINE} ./" | tee /etc/apt/sources.list.d/local-apt.list
fi

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
