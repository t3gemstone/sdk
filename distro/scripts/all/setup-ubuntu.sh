#!/bin/bash

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

DISTRO_SUITE="${1}"

# debootstrap only writes the release pocket into sources.list, so the
# -updates, -security and -backports pockets have to be added explicitly.
#
# amd64 builds use the Azure mirror for every pocket, including -security:
# archive.ubuntu.com drops TLS connections from CI runners and some
# security.ubuntu.com backends lag behind and 404 on current packages.
# clean-up.sh switches back to archive/security.ubuntu.com before the image is
# finalized.
if [ "$(dpkg --print-architecture)" = "amd64" ]; then
    MIRROR="https://azure.archive.ubuntu.com/ubuntu"
    SECURITY_MIRROR="https://azure.archive.ubuntu.com/ubuntu"
else
    MIRROR="https://ports.ubuntu.com/ubuntu-ports"
    SECURITY_MIRROR="https://ports.ubuntu.com/ubuntu-ports"
fi

COMPONENTS="main universe multiverse"

cat > /etc/apt/sources.list << EOF
deb $MIRROR $DISTRO_SUITE $COMPONENTS
deb $MIRROR $DISTRO_SUITE-updates $COMPONENTS
deb $MIRROR $DISTRO_SUITE-backports $COMPONENTS
deb $SECURITY_MIRROR $DISTRO_SUITE-security $COMPONENTS
EOF

apt-get update
apt-get dist-upgrade -y
