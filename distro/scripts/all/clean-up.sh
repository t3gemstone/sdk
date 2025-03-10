#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

DISTRO_TYPE="${1:-minimal}"
DISTRO_SUITE="${2:-jammy}"
DISTRO_BASE="${3:-ubuntu}"

if [[ "$DISTRO_TYPE" == "desktop" ]]; then
    echo "apt-get purge"

    if [[ "$DISTRO_BASE" == "ubuntu" ]]; then
        apt-get purge -y elementary-xfce-icon-theme
        apt-get purge -y ubuntu-wallpapers
        apt-get purge -y xfce4-screensaver
    fi

    apt-get purge -y gnome-accessibility-themes
    apt-get purge -y gnome-themes-extra
    apt-get purge -y light-locker
    apt-get purge -y xarchiver

    apt-get autoremove -y

    # Reinstall automatically removed packages
    apt-get install -y gtk2-engines-pixbuf xdg-utils

    rm -f /usr/share/xsessions/{xfce.desktop,lightdm-xsession.desktop}
    rm -f /etc/xdg/autostart/{xscreensaver.desktop,light-locker.desktop}
    find /usr/share/backgrounds -mindepth 1 -not -path "*t3-gemstone*" -exec rm -rf {} \; 2>/dev/null
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
