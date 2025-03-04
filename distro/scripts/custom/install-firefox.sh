#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

mkdir -p /etc/apt/keyrings /etc/apt/sources.list.d /etc/apt/preferences.d \
    && wget -q https://packages.mozilla.org/apt/repo-signing-key.gpg -O- > /etc/apt/keyrings/packages.mozilla.org.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main" > /etc/apt/sources.list.d/mozilla.list \
    && echo 'Package: *
Pin: origin packages.mozilla.org
Pin-Priority: 1000

Package: firefox*
Pin: release o=Ubuntu
Pin-Priority: -1' > /etc/apt/preferences.d/mozilla \
    && apt-get -qq update \
    && apt-get -qq install firefox firefox-l10n-tr
