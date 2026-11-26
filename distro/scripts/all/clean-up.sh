#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

DISTRO_TYPE="${1:-minimal}"
DISTRO_BASE="${2:-ubuntu}"

if [[ "$DISTRO_TYPE" == "desktop" ]]; then
    echo "apt-get purge"

    if [[ "$DISTRO_BASE" == "ubuntu" ]]; then
        apt-get purge -y elementary-xfce-icon-theme
        apt-get purge -y ubuntu-wallpapers
        apt-get purge -y xfce4-screensaver
    fi

    apt-get purge -y gnome-themes-extra
    apt-get purge -y light-locker
    apt-get purge -y xarchiver

    apt-get autoremove -y

    # Reinstall automatically removed packages
    apt-get install -y gtk2-engines-pixbuf

    rm -f /usr/share/xsessions/{xfce.desktop,lightdm-xsession.desktop}
    rm -f /etc/xdg/autostart/{xscreensaver.desktop,light-locker.desktop}
    find /usr/share/backgrounds -mindepth 1 -not -path "*t3-gemstone*" -exec rm -rf {} \; 2>/dev/null
fi

if [[ "$DISTRO_TYPE" == "tablet" ]]; then
    echo "apt-get remove tablet"
    apt-get remove -y -qq \
        build-essential \
        can-utils \
        gcc \
        gcc-14 \
        htop \
        i2c-tools \
        mc \
        phosh-tour \
        spi-tools \
        systemd-zram-generator \
        ;

    if [ "$DISTRO_BASE" = "pardus" ]; then
        apt-get remove -y -qq phosh-osk-stub
    fi
fi

apt-get autoremove -y
apt-get autoclean -y

# The build uses the Azure Ubuntu mirror for reliability on CI runners
# (see setup-ubuntu.sh); ship images pointing at the canonical archive and
# security servers.
if [ "$DISTRO_BASE" = "ubuntu" ] && [ -f /etc/apt/sources.list ]; then
    sed -i \
        -e '/-security /s|https://azure\.archive\.ubuntu\.com/ubuntu|https://security.ubuntu.com/ubuntu|' \
        -e 's|https://azure\.archive\.ubuntu\.com/ubuntu|https://archive.ubuntu.com/ubuntu|' \
        /etc/apt/sources.list
fi

rm -f /etc/legal
rm -f /etc/update-motd.d/10-help-text
rm -f /etc/apt/sources.list.d/local-apt.list
rm -f /.empty

rm -rf /var/lib/apt/lists/*
rm -rf /var/cache/apt/archives/*
rm -rf /var/cache/apt/*.bin*

# Delete all symbolic links from boot directory
# Boot partition's filesystem is vfat and cannot accept symlinks
find /boot -maxdepth 1 -type l -delete
