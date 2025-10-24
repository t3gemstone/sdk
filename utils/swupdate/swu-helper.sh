#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$0")
KEYS_DIR="$SCRIPT_DIR/keys"
BUILD_DIR="$1"
SWUPDATE_DIR="$BUILD_DIR/swupdate"
STAGING_DIR="$BUILD_DIR/swupdate/staging"

img_path="$(find "$BUILD_DIR/debos" -maxdepth 1 -name 'gemstone-kiosk*.img')"

if [ ! -f "$img_path" ]; then
    echo "Unable to find a kiosk image. Create it using task distro:build <args> and run this again."
fi

if [ ! -d "$KEYS_DIR" ]; then
    mkdir -p "$KEYS_DIR"
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out "$KEYS_DIR/swu_signing.key.pem"
    openssl req -new -x509 -key "$KEYS_DIR/swu_signing.key.pem" -out "$KEYS_DIR/swu_signing.cert.pem" \
        -days 3650 -subj "/CN=SWUpdate Signing/O=T3/C=TR"
    printf 'key=%s\niv=%s\n' "$(openssl rand -hex 32)" "$(openssl rand -hex 16)" > "$KEYS_DIR/aeskey"
fi

mkdir -p "$SWUPDATE_DIR"
mkdir -p "$STAGING_DIR"

loopdev="$(sudo losetup --find --show -P "$img_path")"
sudo partprobe "$loopdev" || true
sleep 1

sudo dd if="${loopdev}p2" of="$STAGING_DIR/rootfs.btrfs" bs=4M status=progress conv=sparse,noerror
sudo losetup -d "$loopdev"

cp "$SCRIPT_DIR/scripts/update-partition.sh" "$STAGING_DIR"

swu_path="$SWUPDATE_DIR/$(basename "$img_path" .img).swu"

swugenerator \
    -k "CMS,$KEYS_DIR/swu_signing.key.pem,$KEYS_DIR/swu_signing.cert.pem" \
    -s "$SCRIPT_DIR/sw-description" \
    -a "$STAGING_DIR" \
    -K "$KEYS_DIR/aeskey" \
    -o "$swu_path" \
    -t create

echo "SWU file has created: $swu_path"
