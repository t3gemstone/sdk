#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

MACHINE="beagley_ai"
CI="$3"

if [ "$CI" = "true" ]; then
    mkdir -p /etc/apt/sources.list.d
    mkdir -p /etc/apt/keyrings

    curl -fsSL https://packages.t3gemstone.org/apt/gemstone-packages-keyring.gpg -o /etc/apt/keyrings/gemstone-packages-keyring.gpg

    echo "deb [signed-by=/etc/apt/keyrings/gemstone-packages-keyring.gpg] https://packages.t3gemstone.org/apt/beagley-ai jammy main" | tee /etc/apt/sources.list.d/gemstone.list
else
    echo "deb [trusted=yes] http://0.0.0.0:8000/${MACHINE} ./" | tee /etc/apt/sources.list.d/local-apt.list
fi

apt-get update -y
apt-get install -y \
    gemstone-boot-files \
    kernel-module-cc33xx \
    kernel-module-cc33xx-sdio \
    kernel-module-at24 \
    kernel-module-rpmsg-pru \
    kernel-module-rpmsg-char \
    kernel-module-ti-k3-dsp-remoteproc \
    kernel-module-ti-k3-r5-remoteproc \
    kernel-module-bluetooth \
    kernel-module-usb-f-mass-storage \
    kernel-module-usb-f-acm \
    kernel-module-usb-f-rndis \
    kernel-module-u-ether \
    kernel-module-u-serial \
    kernel-module-libcomposite \
    ti-img-rogue-driver
