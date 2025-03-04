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
if [[ "$DISTRO_SUITE" == "noble" || "$DISTRO_SUITE" == "bookworm" ]]; then
    systemctl enable systemd-resolved
fi

# NTP client
systemctl enable systemd-timesyncd
