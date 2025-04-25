#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

MACHINE="t3_gem_o1"

echo "deb [trusted=yes] http://0.0.0.0:8000/${MACHINE} ./" | tee /etc/apt/sources.list.d/local-apt.list

apt-get update -y
apt-get install -y \
    kernel \
    u-boot \
    kernel-module-at24 \
    kernel-module-rpmsg-pru \
    kernel-module-rpmsg-char \
    kernel-module-ti-k3-dsp-remoteproc \
    kernel-module-ti-k3-r5-remoteproc \
    kernel-module-bluetooth \
    kernel-module-wl18xx \
    kernel-module-wlcore-sdio \
    kernel-module-wlcore \
    kernel-module-btusb \
    kernel-module-fusb302 \
    kernel-module-gb-usb \
    kernel-module-musb-hdrc \
    kernel-module-plusb \ \
    kernel-module-snd-usb-audio \
    kernel-module-ti-usb-3410-5052 \
    kernel-module-ums-usbat \
    kernel-module-usb3503 \
    kernel-module-usb-conn-gpio \
    kernel-module-usb-f-acm \
    kernel-module-usb-f-ecm \
    kernel-module-usb-f-ecm-subset \
    kernel-module-usb-f-eem \
    kernel-module-usb-f-fs \
    kernel-module-usb-f-hid \
    kernel-module-usb-f-mass-storage \
    kernel-module-usb-f-ncm \
    kernel-module-usb-f-serial \
    kernel-module-usb-f-ss-lb \
    kernel-module-usb-f-uac1 \
    kernel-module-usb-f-uac2 \
    kernel-module-usb-f-uvc \
    kernel-module-usbnet \
    kernel-module-usbserial \
    kernel-module-usb-serial-simple \
    kernel-module-usb-storage \
    kernel-module-usb-wwan \
    kernel-module-wpanusb \
    kernel-module-imx219 \
    kernel-module-v4l2-async \
    kernel-module-v4l2-dv-timings \
    kernel-module-v4l2-fwnode \
    kernel-module-v4l2-mem2mem \
    kernel-module-videobuf2-v4l2 \
    kernel-module-can \
    kernel-module-can-dev \
    kernel-module-can-raw \
    kernel-module-m-can \
    kernel-module-m-can-platform \
    kernel-module-phy-can-transceiver \
    kernel-module-pwm-fan \
    kernel-module-at24 \
    kernel-module-st-lsm6dsx \
    kernel-module-st-lsm6dsx-i2c \
    ti-img-rogue-driver
