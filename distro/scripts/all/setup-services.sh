#!/bin/bash

if [ -f /usr/local/bin/gem-first-boot ]; then
    chmod +x /usr/local/bin/gem-first-boot
    systemctl enable gem-first-boot
fi

if [ -f /usr/local/bin/gem-init ]; then
    chmod +x /usr/local/bin/gem-init
    systemctl enable gem-init
fi
