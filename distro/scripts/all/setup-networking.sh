#!/bin/bash

set -euo pipefail

MACHINE="${1}"
DISTRO_SUITE="${2}"

# Manage all network interfaces
rm -f /usr/lib/NetworkManager/conf.d/10-globally-managed-devices.conf

# Networkmanager does not allow bad permission
if [ -f /etc/NetworkManager/system-connections/eth0-dhcp.nmconnection ]; then
    chmod 0600 /etc/NetworkManager/system-connections/eth0-dhcp.nmconnection
fi

# Network management
systemctl enable NetworkManager

# DNS resolving
systemctl enable systemd-resolved

# NTP client
if [[ "$DISTRO_SUITE" == "jammy" || "$DISTRO_SUITE" == "noble" ]]; then
    systemctl enable systemd-timesyncd
fi
