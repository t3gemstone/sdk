#!/bin/bash

set -euo pipefail

DISTRO_TYPE="${1:-minimal}"

if [[ "$DISTRO_TYPE" == "desktop" ]]; then
    chmod +x /etc/X11/Xsession.d/56t3-gemstone-session
    chmod +x /usr/local/bin/set-default-keyboard-layout
    chmod +x /usr/local/bin/xfce4-popup-applicationsmenu
fi

if [[ "$DISTRO_TYPE" == "GUI" ]]; then
    if [[ -f /usr/local/bin/gui ]]; then
        chmod +x /usr/local/bin/gui
    fi
fi

localedef -i en_US -f UTF-8 en_US.UTF-8
chown -R gemstone:gemstone /home/gemstone
