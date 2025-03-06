#!/bin/bash

set -euo pipefail

DISTRO_TYPE="${1:-minimal}"

if [[ "$DISTRO_TYPE" == "desktop" ]]; then
    chmod +x /usr/local/bin/set-system-keyboard-layout
    chmod +x /usr/local/bin/set-system-language
    chmod +x /usr/local/bin/xfce4-popup-applicationsmenu
fi

if [[ "$DISTRO_TYPE" == "kiosk" ]]; then
    if [[ -f /usr/local/bin/kiosk ]]; then
        chmod +x /usr/local/bin/kiosk
    fi
fi

localedef -i en_US -f UTF-8 en_US.UTF-8
chown -R gemstone:gemstone /home/gemstone
