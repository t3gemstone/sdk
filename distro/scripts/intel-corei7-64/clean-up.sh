#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

DISTRO_TYPE="${1}"

if [[ "$DISTRO_TYPE" == "desktop" || "$DISTRO_TYPE" == "gui" ]]; then
    echo 'apt-get remove'
fi
