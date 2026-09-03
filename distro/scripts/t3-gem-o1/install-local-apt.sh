#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

MACHINE="t3_gem_o1"
DISTRO_TYPE="${2:-minimal}"
CI="$3"

if [ "$CI" = "true" ]; then
    mkdir -p /etc/apt/sources.list.d
    mkdir -p /etc/apt/keyrings

    curl -fsSL https://packages.t3gemstone.org/apt/gemstone-packages-keyring.gpg -o /etc/apt/keyrings/gemstone-packages-keyring.gpg

    echo "deb [signed-by=/etc/apt/keyrings/gemstone-packages-keyring.gpg] https://packages.t3gemstone.org/apt/t3-gem-o1 bsp main" | tee /etc/apt/sources.list.d/gemstone.list
else
    echo "deb [trusted=yes] http://0.0.0.0:8000/${MACHINE} ./" | tee /etc/apt/sources.list.d/local-apt.list
fi

apt-get update -y
apt-get install -y \
    kernel-image-image-6.12.24-ti \
    kernel-module-arducam-pivariety-6.12.24-ti \
    kernel-module-at24-6.12.24-ti \
    kernel-module-bluetooth-6.12.24-ti \
    kernel-module-br-netfilter-6.12.24-ti \
    kernel-module-bridge-6.12.24-ti \
    kernel-module-btqca-6.12.24-ti \
    kernel-module-btusb-6.12.24-ti \
    kernel-module-can-6.12.24-ti \
    kernel-module-can-dev-6.12.24-ti \
    kernel-module-can-raw-6.12.24-ti \
    kernel-module-cdc-acm-6.12.24-ti \
    kernel-module-cdns-csi2rx-6.12.24-ti \
    kernel-module-cdns-dphy-rx-6.12.24-ti \
    kernel-module-e5010-jpeg-enc-6.12.24-ti \
    kernel-module-fusb302-6.12.24-ti \
    kernel-module-gb-usb-6.12.24-ti \
    kernel-module-goodix-ts-6.12.24-ti \
    kernel-module-hci-uart-6.12.24-ti \
    kernel-module-hdc2010-6.12.24-ti \
    kernel-module-hid-generic-6.12.24-ti \
    kernel-module-imx219-6.12.24-ti \
    kernel-module-imx290-6.12.24-ti \
    kernel-module-imx390-6.12.24-ti \
    kernel-module-ip6-tables-6.12.24-ti \
    kernel-module-ip6table-filter-6.12.24-ti \
    kernel-module-iptable-filter-6.12.24-ti \
    kernel-module-iptable-mangle-6.12.24-ti \
    kernel-module-iptable-nat-6.12.24-ti \
    kernel-module-iptable-raw-6.12.24-ti \
    kernel-module-iptable-security-6.12.24-ti \
    kernel-module-j721e-csi2rx-6.12.24-ti \
    kernel-module-loop-6.12.24-ti \
    kernel-module-m-can-6.12.24-ti \
    kernel-module-m-can-platform-6.12.24-ti \
    kernel-module-musb-hdrc-6.12.24-ti \
    kernel-module-nf-nat-6.12.24-ti \
    kernel-module-omap-mailbox-6.12.24-ti \
    kernel-module-overlay-6.12.24-ti \
    kernel-module-panel-raspberrypi-touchscreen-6.12.24-ti \
    kernel-module-panel-simple-6.12.24-ti \
    kernel-module-panel-waveshare-dsi-6.12.24-ti \
    kernel-module-phy-can-transceiver-6.12.24-ti \
    kernel-module-plusb-6.12.24-ti \
    kernel-module-pwm-fan-6.12.24-ti \
    kernel-module-rpi-panel-attiny-regulator-6.12.24-ti \
    kernel-module-rpmsg-char-6.12.24-ti \
    kernel-module-rpmsg-ctrl-6.12.24-ti \
    kernel-module-rtw88-8822c-6.12.24-ti \
    kernel-module-rtw88-8822cs-6.12.24-ti \
    kernel-module-rtw88-core-6.12.24-ti \
    kernel-module-rtw88-sdio-6.12.24-ti \
    kernel-module-snd-usb-audio-6.12.24-ti \
    kernel-module-spidev-6.12.24-ti \
    kernel-module-tc358762-6.12.24-ti \
    kernel-module-ti-k3-dsp-remoteproc-6.12.24-ti \
    kernel-module-ti-k3-r5-remoteproc-6.12.24-ti \
    kernel-module-ti-usb-3410-5052-6.12.24-ti \
    kernel-module-ums-usbat-6.12.24-ti \
    kernel-module-usb-conn-gpio-6.12.24-ti \
    kernel-module-usb-f-uac1-6.12.24-ti \
    kernel-module-usb-f-uac2-6.12.24-ti \
    kernel-module-usb-serial-simple-6.12.24-ti \
    kernel-module-usb-storage-6.12.24-ti \
    kernel-module-usb-wwan-6.12.24-ti \
    kernel-module-usb3503-6.12.24-ti \
    kernel-module-usbhid-6.12.24-ti \
    kernel-module-usbnet-6.12.24-ti \
    kernel-module-usbserial-6.12.24-ti \
    kernel-module-v4l2-async-6.12.24-ti \
    kernel-module-v4l2-dv-timings-6.12.24-ti \
    kernel-module-v4l2-fwnode-6.12.24-ti \
    kernel-module-v4l2-mem2mem-6.12.24-ti \
    kernel-module-veth-6.12.24-ti \
    kernel-module-videobuf2-v4l2-6.12.24-ti \
    kernel-module-virtio-rpmsg-bus-6.12.24-ti \
    kernel-module-wave5-6.12.24-ti \
    kernel-module-wl18xx-6.12.24-ti \
    kernel-module-wlcore-6.12.24-ti \
    kernel-module-wlcore-sdio-6.12.24-ti \
    kernel-module-xt-addrtype-6.12.24-ti \
    kernel-module-xt-conntrack-6.12.24-ti \
    kernel-module-xt-masquerade-6.12.24-ti \
    kernel-module-xt-nat-6.12.24-ti \
    ti-img-rogue-driver \
    u-boot

if [[ "$DISTRO_TYPE" == "tablet" ]]; then
    apt-get install -y \
        kernel-module-fuse-6.12.24-ti \
        kernel-module-xt-checksum-6.12.24-ti \
        ;
fi

if [ "$CI" = "true" ]; then
    apt-get install -y gem-t3-gem-o1-bsp
fi
