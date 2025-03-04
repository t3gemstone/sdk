#!/bin/bash

DISTRO_TYPE=$1

list=(
    "apt-daily-upgrade.service"
    "apt-daily.service"
    "cryptsetup.target"
    "e2scrub_all.timer"
    "e2scrub_reap.service"
    "remote-cryptsetup.target"
    "remote-fs-pre.target"
    "remote-fs.target"
    "swap.target"
    "sys-kernel-debug.mount"
    "sys-kernel-tracing.mount"
    "systemd-pstore.service"
    "veritysetup.target"
    "motd-news.service"
    "motd-news.timer"
    "fstrim.service"
    "fstrim.timer"
)

for i in "${list[@]}"; do
    systemctl disable "$i"
done

