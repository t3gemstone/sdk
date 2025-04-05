#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

ROOTDIR="$1"


apt-get update -y
apt-get install -y gpiod

if ! getent group gpio > /dev/null; then
    groupadd gpio
else
    echo "[i] GPIO grup already exist."
fi



if groups "" | grep -q '\bgpio\b'; then
    echo "[i] The user is already in the GPIO group ."
else
    usermod -a -G gpio gemstone
fi

UDEV_RULE="$ROOTDIR/etc/udev/rules.d/99-gpio.rules"
echo "[+] Generating Udev udev rule..."
echo 'SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="660"' | tee $UDEV_RULE
