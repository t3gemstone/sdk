#!/bin/bash

set -euo pipefail

DISTRO_TYPE="$1"
IMG_RELEASE="$2"

if ! grep 'GEMSTONE_' /etc/lsb-release; then
    echo "GEMSTONE_DISTRO_TYPE=$DISTRO_TYPE" >> /etc/lsb-release
    echo "GEMSTONE_DISTRO_RELEASE=$IMG_RELEASE" >> /etc/lsb-release
fi
