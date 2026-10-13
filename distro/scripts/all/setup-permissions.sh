#!/bin/bash

set -euo pipefail

DISTRO_TYPE="${1:-minimal}"

chmod +x /usr/local/bin/gem-camera-setup

# Shipped by the t3-gem-o1 overlay only
if [[ -f /usr/local/bin/gem-gpu-run ]]; then
    chmod +x /usr/local/bin/gem-gpu-run /usr/local/bin/gem-gpu-info
fi

if [[ "$DISTRO_TYPE" == "desktop" ]]; then
    chmod +x /usr/local/bin/set-system-keyboard-layout
    chmod +x /usr/local/bin/set-system-language
    chmod +x /usr/local/bin/xfce4-popup-applicationsmenu
fi

if [[ "$DISTRO_TYPE" == "wayland-desktop" ]]; then
    chmod 0755 /usr/local/bin/start-t3-plasma-wayland
fi

if [[ "$DISTRO_TYPE" == "kiosk" ]]; then
    if [[ -f /usr/local/bin/kiosk ]]; then
        chmod +x /usr/local/bin/kiosk
    fi

    chmod +x /home/gemstone/bin/kiosk /home/gemstone/bin/kiosk-session
fi

chown -R gemstone:gemstone /home/gemstone

if [[ "$DISTRO_TYPE" == "tablet" ]]; then
    chmod 0755 /usr/local/sbin/nftables-safe

    # The dpkg wrapper + allowlist are SELinux-conditional (tablet/selinux
    # overlay). Skip silently when the build didn't include them.
    if [[ -f /usr/local/sbin/dpkg ]]; then
        chmod 0755 /usr/local/sbin/dpkg
    fi

    if [[ -f /etc/gemstone/allowed-packages.list ]]; then
        chown root:root /etc/gemstone/allowed-packages.list
        chmod 0644 /etc/gemstone/allowed-packages.list
    fi

    # root'un PATH'ine /usr/local/sbin ekle (yoksa)
    grep -qxF 'export PATH="/usr/local/sbin:$PATH"' /root/.bashrc || echo 'export PATH="/usr/local/sbin:$PATH"' >> /root/.bashrc
fi
