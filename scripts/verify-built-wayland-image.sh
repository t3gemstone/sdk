#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:-/home/workdir/build/debos/gemstone-wayland-desktop-v2026.2-ubuntu-jammy-t3-gem-o1.img}"
MOUNT_ROOT="${2:-/mnt/t3-wayland-verify}"
LOOP=""

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

cleanup() {
    set +e
    mountpoint -q "$MOUNT_ROOT/boot" && sudo umount "$MOUNT_ROOT/boot"
    mountpoint -q "$MOUNT_ROOT/root" && sudo umount "$MOUNT_ROOT/root"
    if [[ -n "$LOOP" ]]; then
        sudo losetup -d "$LOOP"
    fi
}
trap cleanup EXIT

[[ -f "$IMAGE" ]] || fail "image not found: $IMAGE"
sudo mkdir -p "$MOUNT_ROOT/boot" "$MOUNT_ROOT/root"
LOOP="$(sudo losetup --find --show -P "$IMAGE")"
sudo mount -o ro "${LOOP}p1" "$MOUNT_ROOT/boot"
sudo mount -o ro "${LOOP}p2" "$MOUNT_ROOT/root"

boot_files=(
    Image
    gemstone-image-rd-t3-gem-o1.cpio.gz
    k3-am67a-t3-gem-o1.dtb
    tiboot3.bin
    tispl.bin
    u-boot.img
    uEnv.txt
)

root_files=(
    usr/bin/kwin_wayland
    usr/bin/plasmashell
    usr/local/bin/start-t3-plasma-wayland
    usr/share/wayland-sessions/t3-plasmawayland.desktop
    usr/lib/t3-gemstone/powervr-env.sh
    usr/lib/t3-gemstone/powervr-session.env
    etc/sddm.conf.d/20-t3-wayland.conf
    etc/skel/.config/plasma-org.kde.plasma.desktop-appletsrc
    usr/share/wallpapers/T3GemstoneLaunchEclipse/contents/images/1920x1080.png
    usr/share/icons/hicolor/256x256/apps/t3-gemstone.png
    usr/share/plasma/plasmoids/org.t3.gemstone.systemstatus/metadata.json
    usr/lib/systemd/user/t3-gemstone-theme.service
)

for path in "${boot_files[@]}"; do
    [[ -e "$MOUNT_ROOT/boot/$path" ]] || fail "missing boot file: $path"
done

for path in "${root_files[@]}"; do
    [[ -e "$MOUNT_ROOT/root/$path" ]] || fail "missing rootfs file: $path"
done

[[ -d "$MOUNT_ROOT/boot/overlays" ]] || fail "missing boot overlays directory"
[[ -e "$MOUNT_ROOT/root/opt/ti-gpu/lib/dri/pvr_dri.so" ]] || \
    fail "missing PowerVR DRI driver"
[[ -e "$MOUNT_ROOT/root/usr/lib/libpvr_dri_support.so.25.2.6850647" ]] || \
    fail "missing PowerVR DRI support library"
find "$MOUNT_ROOT/root/lib/modules" -type f -name 'pvrsrvkm.ko*' -print -quit | grep -q . || \
    fail "missing PowerVR kernel module"
[[ "$(readlink "$MOUNT_ROOT/root/etc/systemd/system/default.target")" == "/lib/systemd/system/graphical.target" ]] || \
    fail "graphical.target is not the default"

grep -q '^Session=t3-plasmawayland\.desktop$' "$MOUNT_ROOT/root/etc/sddm.conf.d/20-t3-wayland.conf" || \
    fail "SDDM does not select the T3 Wayland session"
grep -q 'XDG_SESSION_TYPE=wayland' "$MOUNT_ROOT/root/usr/local/bin/start-t3-plasma-wayland" || \
    fail "Wayland session environment is missing"
grep -q 'T3GemstoneLaunchEclipse' \
    "$MOUNT_ROOT/root/etc/skel/.config/plasma-org.kde.plasma.desktop-appletsrc" || \
    fail "T3 Launch Eclipse is not the default wallpaper"
wallpaper_count="$(find "$MOUNT_ROOT/root/usr/share/wallpapers" \
    -type f -path '*/contents/images/1920x1080.png' | wc -l)"
[[ "$wallpaper_count" -ge 16 ]] || \
    fail "expected at least 16 T3 wallpapers, found $wallpaper_count"

required_packages=(
    kwin-wayland
    pipewire
    plasma-workspace-wayland
    qtwayland5
    sddm
    ti-img-rogue-driver
    wireplumber
    xdg-desktop-portal-kde
)
for package in "${required_packages[@]}"; do
    status="$(dpkg-query --admindir="$MOUNT_ROOT/root/var/lib/dpkg" \
        -W -f='${db:Status-Abbrev}' "$package" 2>/dev/null || true)"
    [[ "$status" == "ii " ]] || fail "required package is not installed: $package"
done

printf 'Image: %s\n' "$IMAGE"
printf 'Size: %s bytes\n' "$(stat -c %s "$IMAGE")"
printf 'Partitions:\n'
sudo fdisk -l "$IMAGE" | sed -n '/^Device/,$p'
printf 'Boot files: OK (%d required files)\n' "${#boot_files[@]}"
printf 'Plasma Wayland files: OK (%d required files)\n' "${#root_files[@]}"
printf 'PowerVR DRI: %s\n' "$(file -b "$MOUNT_ROOT/root/opt/ti-gpu/lib/dri/pvr_dri.so")"
printf 'Required runtime packages: OK (%d packages)\n' "${#required_packages[@]}"
printf 'T3 wallpapers: OK (%s installed)\n' "$wallpaper_count"
printf 'Root filesystem usage:\n'
df -h "$MOUNT_ROOT/root" | tail -n 1
printf 'T3 Gemstone O1 PowerVR Plasma Wayland image: OK\n'
