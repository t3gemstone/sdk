#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

MACHINE="t3-gem-o1"

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
    ti-img-rogue-driver
