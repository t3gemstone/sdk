#!/bin/bash
# T3 Foundation Gemstone Project [t3gemstone.org]
# SPDX-License-Identifier: Apache-2.0
#
# Cross build TI's patched Mesa (mesa-pvr) for the target rootfs.
#
# Only pvr_dri.so and the EGL/GLES/GBM libraries that load it are built. There is
# deliberately no swrast driver: llvmpipe is exactly the software fallback this
# exists to get away from, and dropping it drops the libLLVM dependency with it.
#
# The result is installed into an isolated prefix (/opt/ti-gpu) so the rootfs keeps
# its own Mesa and its Xorg session untouched -- see the gem-gpu-run wrapper.

set -euo pipefail

WORKDIR="$1"
MACHINE="$2"
JOBS="${3:-$(nproc)}"

SRCDIR="$WORKDIR/src/mesa-pvr"
RECIPE="$WORKDIR/yocto/meta-ti/meta-ti-bsp/recipes-graphics/mesa/mesa-pvr_24.0.1.bb"
PATCHDIR="$WORKDIR/yocto/meta-ti/meta-ti-bsp/recipes-graphics/mesa/mesa-pvr-24.0.1"
CROSSFILE="$WORKDIR/graphics/cross/aarch64.txt"
BUILDDIR="$WORKDIR/build/graphics/$MACHINE/.build"
STAGEDIR="$WORKDIR/build/graphics/$MACHINE"

# SRCREV of yocto/meta-ti/meta-ti-bsp/recipes-graphics/mesa/mesa-pvr_24.0.1.bb
SRCREV="68af6a102c2298569e77d1aa8bccc1ff61438b3e"

if [ ! -d "$SRCDIR/.git" ]; then
    echo "ERROR: $SRCDIR missing. Run 'task fetch' first." >&2
    exit 1
fi

if ! command -v aarch64-linux-gnu-gcc >/dev/null; then
    echo "ERROR: arm64 cross toolchain missing. The gemstone-sdk image is stale --" >&2
    echo "       rebuild it with 'task destroy && task box' on the host." >&2
    exit 1
fi

# Read the patch order out of SRC_URI rather than globbing the directory: the
# llvm-19 patch builds on the llvm-17 and gallivm ones, so order is load bearing.
mapfile -t PATCHES < <(sed -n 's|^[[:space:]]*file://\([^[:space:]]*\.patch\).*|\1|p' "$RECIPE")
if [ ${#PATCHES[@]} -eq 0 ]; then
    echo "ERROR: no patches found in $RECIPE" >&2
    exit 1
fi

# Reapply from a pristine SRCREV every time so repeated runs stay idempotent.
echo ">>> Preparing $SRCDIR at $SRCREV"
git -C "$SRCDIR" checkout -f "$SRCREV"
for patch in "${PATCHES[@]}"; do
    echo "    applying $patch"
    # GNU patch, not 'git apply': some of these carry unpadded blank context
    # lines, which git rejects as corrupt and Yocto's own patch tool accepts.
    patch -d "$SRCDIR" -p1 --batch --forward --silent -i "$PATCHDIR/$patch"
done

echo ">>> Configuring"
rm -rf "$BUILDDIR" "$STAGEDIR/opt"
meson setup "$BUILDDIR" "$SRCDIR" \
    --cross-file "$CROSSFILE" \
    --prefix=/opt/ti-gpu --libdir=lib \
    --wrap-mode=nodownload \
    -Dgallium-drivers=pvr \
    -Dvulkan-drivers= \
    -Dllvm=disabled \
    -Dshared-glapi=enabled \
    -Dglvnd=false \
    -Dglx=disabled \
    -Ddri3=disabled \
    -Dplatforms= \
    -Degl=enabled \
    -Dgbm=enabled \
    -Dgles1=enabled \
    -Dgles2=enabled \
    -Dopengl=true \
    -Dosmesa=false \
    -Dtools= \
    -Dlibunwind=disabled \
    -Dgallium-opencl=disabled \
    -Dgallium-va=disabled \
    -Dgallium-vdpau=disabled \
    -Dgallium-xa=disabled \
    -Dvideo-codecs=all_free \
    -Dlmsensors=disabled \
    -Dperfetto=false \
    -Dvulkan-beta=false \
    -Dglx-read-only-text=true \
    -Dopencl-spirv=false \
    -Dimagination-srv=false \
    -Ddri-drivers-path=/opt/ti-gpu/lib/dri

echo ">>> Building"
ninja -C "$BUILDDIR" "-j$JOBS"

echo ">>> Installing into $STAGEDIR/opt/ti-gpu"
DESTDIR="$STAGEDIR" meson install -C "$BUILDDIR" --quiet

# The headers and .pc files are only useful when cross building against this
# prefix, which the SDK does not do -- keep them out of the image.
rm -rf "$STAGEDIR/opt/ti-gpu/include" "$STAGEDIR/opt/ti-gpu/lib/pkgconfig"

DRI="$STAGEDIR/opt/ti-gpu/lib/dri/pvr_dri.so"
if [ ! -f "$DRI" ]; then
    echo "ERROR: build finished but $DRI is missing." >&2
    exit 1
fi

# The whole point of this build is an ABI the target rootfs can load. Assert it
# rather than discovering it on the board.
MAXGLIBC=$(readelf -V "$DRI" | grep -oE 'GLIBC_[0-9.]+' | sort -uV | tail -1)
echo ">>> pvr_dri.so requires at most $MAXGLIBC"
if [ "$(printf '%s\nGLIBC_2.35\n' "$MAXGLIBC" | sort -uV | tail -1)" != "GLIBC_2.35" ]; then
    echo "ERROR: $MAXGLIBC is newer than the jammy rootfs (GLIBC_2.35) can provide." >&2
    exit 1
fi

echo ">>> Done: $STAGEDIR/opt/ti-gpu"
