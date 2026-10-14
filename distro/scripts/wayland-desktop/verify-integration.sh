#!/bin/bash
set -euo pipefail

workdir="${1:-$(pwd)}"
overlay="$workdir/distro/overlays/wayland-desktop"

required=(
  "$workdir/distro/distro-wayland-desktop.yaml"
  "$overlay/all/usr/local/bin/start-t3-plasma-wayland"
  "$overlay/all/usr/share/wayland-sessions/t3-plasmawayland.desktop"
  "$overlay/all/etc/sddm.conf.d/20-t3-wayland.conf"
  "$overlay/all/etc/skel/.config/plasma-org.kde.plasma.desktop-appletsrc"
  "$overlay/all/usr/share/wallpapers/T3GemstoneCollection01/contents/images/1920x1080.png"
  "$overlay/all/usr/share/icons/hicolor/256x256/apps/t3-gemstone.png"
  "$overlay/all/usr/share/plasma/plasmoids/org.t3.gemstone.systemstatus/metadata.json"
  "$overlay/t3-gem-o1/usr/lib/t3-gemstone/powervr-env.sh"
  "$overlay/t3-gem-o1/usr/lib/t3-gemstone/powervr-session.env"
)

for path in "${required[@]}"; do
  test -s "$path" || { echo "missing integration file: $path" >&2; exit 1; }
done

grep -q 'DISTRO_TYPE=wayland-desktop' "$workdir/distro/Taskfile.yml"
grep -q 'MESA_LOADER_DRIVER_OVERRIDE=pvr' \
  "$overlay/t3-gem-o1/usr/lib/t3-gemstone/powervr-session.env"
grep -q 'Exec=/usr/local/bin/start-t3-plasma-wayland' \
  "$overlay/all/usr/share/wayland-sessions/t3-plasmawayland.desktop"
grep -q 'T3GemstoneCollection01' \
  "$overlay/all/etc/skel/.config/plasma-org.kde.plasma.desktop-appletsrc"
if grep -q '^DisplayServer=wayland' \
  "$overlay/all/etc/sddm.conf.d/20-t3-wayland.conf"; then
  echo "SDDM greeter must not compete with KWin for the PowerVR DRM device" >&2
  exit 1
fi

echo "T3 Plasma Wayland integration: OK"
