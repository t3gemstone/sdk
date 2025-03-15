#!/bin/bash

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

MACHINE="${1}"
DISTRO_SUITE="${2}"

mkdir -p /etc/apt/sources.list.d
mkdir -p /etc/apt/keyrings

curl -fsSL https://packages.t3gemstone.org/apt/gemstone-packages-keyring.gpg -o /etc/apt/keyrings/gemstone-packages-keyring.gpg

if [[ "$DISTRO_SUITE" == "jammy" ]]; then
    echo "deb [signed-by=/etc/apt/keyrings/gemstone-packages-keyring.gpg] https://packages.t3gemstone.org/apt $DISTRO_SUITE main" | tee /etc/apt/sources.list.d/gemstone.list
    apt-get update -y
fi
