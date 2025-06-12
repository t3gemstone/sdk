#!/bin/bash

set -ex

. /utils.sh

SDK_PATH="/work"
REPOS_YML_FILE="$SDK_PATH/repos.yml"
YOCTO_DIR="$REPOS_DIR/yocto"
BUILD_DIR="$HOME/build"
LOCAL_CONF_FILE="${BUILD_DIR}/conf/local.conf"

[ -f "$REPOS_YML_FILE" ] ||
    error "repos.yml file is needed. Make sure that it is located in root directory of repo."
[ -n "$MACHINE" ] ||
    error "Machine to be used for build is not provided."
[ -n "$IMAGE" ] ||
    error "Image to build is not provided."

vcs import --input "$REPOS_YML_FILE" "$REPOS_DIR"

# shellcheck disable=SC1091
TEMPLATECONF="$YOCTO_DIR/meta-gemstone/conf/templates/$MACHINE" . "$YOCTO_DIR/poky/oe-init-build-env" "$BUILD_DIR"

sed -i "s@DL_DIR ?= .*@DL_DIR ?= \"${DL_DIR}\"@" "$LOCAL_CONF_FILE"
sed -i "s@SSTATE_DIR ?= .*@SSTATE_DIR ?= \"${SSTATE_DIR}\"@" "$LOCAL_CONF_FILE"
sed -i "s@TMPDIR = .*@@" "$LOCAL_CONF_FILE"

{
    echo 'OE_NUMBER_THREADS = "6"';
    echo 'PARALLEL_MAKE = "-j 6"';
    echo 'INHERIT += "rm_work"';
} >> "$LOCAL_CONF_FILE"

sed -i "s@GEMSTONE_WORKDIR = .*@GEMSTONE_WORKDIR = \"$REPOS_DIR\"@g" "$BUILD_DIR/conf/bblayers.conf"

cat "$BUILD_DIR/conf/bblayers.conf"
cat "$BUILD_DIR/conf/local.conf"

env

bitbake gemstone-boot-files
IMG_DEPLOY_DIR=$(bitbake-getvar --value -r "$IMAGE" DEPLOY_DIR_IMAGE)
DEB_DEPLOY_DIR=$(bitbake-getvar --value -r "$IMAGE" DEPLOY_DIR_DEB)

case "$MACHINE" in
    intel-corei7-64)
        KERNEL_NAME=$(bitbake-getvar --value -r "$IMAGE" PREFERRED_PROVIDER_virtual/kernel)
        PACKAGE_ARCH=$(bitbake-getvar --value -r "$IMAGE" "PACKAGE_ARCH:pn-${KERNEL_NAME}")
        ;;
    *)
        PACKAGE_ARCH=$(bitbake-getvar --value -r "$IMAGE" "PACKAGE_ARCH")
        ;;
esac

mkdir -p "$ARTIFACTS_DIR/${MACHINE}-${IMAGE}"
mkdir -p "$ARTIFACTS_DIR/${MACHINE}-${IMAGE}-debs"
tar -cf "images.tar" -C "$(dirname "$IMG_DEPLOY_DIR")/$(basename "$IMG_DEPLOY_DIR")" .
tar -cf "debs.tar" -C "$DEB_DEPLOY_DIR/$PACKAGE_ARCH" .

cp "images.tar" "$ARTIFACTS_DIR/${MACHINE}-${IMAGE}"
cp "debs.tar" "$ARTIFACTS_DIR/${MACHINE}-${IMAGE}"
