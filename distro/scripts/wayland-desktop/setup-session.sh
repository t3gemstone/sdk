#!/bin/bash
set -euo pipefail

machine="${1:?machine is required}"

if [[ "$machine" != "t3-gem-o1" ]]; then
    echo "wayland-desktop currently supports only t3-gem-o1" >&2
    exit 1
fi

test -x /usr/bin/startplasma-wayland
test -x /usr/bin/kwin_wayland
test -f /usr/share/wayland-sessions/t3-plasmawayland.desktop
test -f /usr/lib/t3-gemstone/powervr-session.env

chmod 0755 /usr/local/bin/start-t3-plasma-wayland
chmod 0644 /usr/lib/t3-gemstone/powervr-env.sh
chmod 0644 /usr/lib/t3-gemstone/powervr-session.env

systemctl enable sddm.service
systemctl set-default graphical.target

# Disable the legacy X11 VNC service if an earlier desktop layer installed it.
systemctl disable t3-gem-vnc.service 2>/dev/null || true
