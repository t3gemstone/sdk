#!/bin/bash

if [ -f /usr/local/bin/gem-first-init ]; then
    chmod +x /usr/local/bin/gem-first-init
    systemctl enable gem-first-init
fi
