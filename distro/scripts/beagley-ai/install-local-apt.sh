#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

MACHINE="beagley_ai"

echo "deb [trusted=yes] http://0.0.0.0:8000/${MACHINE} ./" | tee /etc/apt/sources.list.d/local-apt.list

apt-get update -y
apt-get install -y \
    kernel \
    u-boot \
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
