#!/bin/bash

if [ -f /usr/local/bin/gem-usb-gadgets ]; then
    chmod +x /usr/local/bin/gem-usb-gadgets
    systemctl enable gem-usb-gadgets
fi
