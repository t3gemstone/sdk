#!/bin/bash

set -euo pipefail

DISTRO_TYPE="${1:-minimal}"

adduser \
  --gecos gemstone \
  --disabled-password \
  --shell /bin/bash gemstone

getent group gpio >/dev/null || groupadd gpio
getent group spi >/dev/null || groupadd spi
getent group render >/dev/null || groupadd --system render

# render: the GPU's render node is only the seat user's otherwise, so programs
# started over SSH or VNC could not use the GPU
usermod gemstone -G sudo,dialout,tty,video,render,i2c,gpio,spi

if [[ "$DISTRO_TYPE" == "tablet" ]]; then
    echo "gemstone:4380" | chpasswd
else
    echo "gemstone:t3" | chpasswd
fi

localedef -i en_US -f UTF-8 en_US.UTF-8
