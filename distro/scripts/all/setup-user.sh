#!/bin/bash

set -euo pipefail

DISTRO_TYPE="${1:-minimal}"

adduser \
  --gecos gemstone \
  --disabled-password \
  --shell /bin/bash gemstone

getent group gpio >/dev/null || groupadd gpio
getent group spi >/dev/null || groupadd spi

# GPU render nodes (/dev/dri/renderD*) are root:render 0660. Without this the
# PowerVR userspace cannot open the GPU and GLES silently falls back to
# llvmpipe. The group does not exist yet this early in the build, so create it.
getent group render >/dev/null || groupadd -r render

# /dev/input/event* are root:input 0660 with no ACL. Under Xorg the server owns
# them, but an eglfs kiosk opens them itself and would come up without input.
getent group input >/dev/null || groupadd -r input

usermod gemstone -G sudo,dialout,tty,video,i2c,gpio,spi,render,input

if [[ "$DISTRO_TYPE" == "tablet" ]]; then
    echo "gemstone:4380" | chpasswd
else
    echo "gemstone:t3" | chpasswd
fi

localedef -i en_US -f UTF-8 en_US.UTF-8
