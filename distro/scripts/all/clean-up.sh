#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

DISTRO_TYPE="${1:-minimal}"

if [[ "$DISTRO_TYPE" == "desktop" ]]; then
    echo "apt-get purge"

    apt-get purge -y \
        elementary-xfce-icon-theme \
        gnome-accessibility-themes \
        gnome-themes-extra \
        humanity-icon-theme \
        ubuntu-wallpapers \
        xarchiver \
        xfce4-screensaver

    rm /usr/share/xsessions/xfce.desktop
    rm /etc/xdg/autostart/xscreensaver.desktop
    find /usr/share/backgrounds -mindepth 1 -not -path "*t3-gemstone*" -exec rm -r {} \; 2>/dev/null
fi

apt-get autoremove -y
apt-get autoclean -y

# Ubuntu Login Messages
rm -f /etc/legal
rm -f /etc/update-motd.d/10-help-text

rm -rf /var/lib/apt/lists/*
rm -rf /var/cache/apt/archives/*
rm -rf /var/cache/apt/*.bin*

rm -f /etc/apt/sources.list.d/local-apt.list

# Delete all symbolic links from boot directory
# Boot partition's filesystem is vfat and cannot accept symlinks
find /boot -maxdepth 1 -type l -delete
