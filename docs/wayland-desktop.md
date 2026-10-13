# T3 Gemstone O1 Plasma Wayland image

This image type layers a minimal KDE Plasma Wayland session on the SDK's
PowerVR-enabled Ubuntu Jammy root filesystem. The SDK remains the sole owner of
Mesa, EGL, GBM, kernel, firmware and boot artifacts.

## Build

```bash
task yocto:build MACHINE=t3-gem-o1
task graphics:build MACHINE=t3-gem-o1
task distro:verify:wayland
task distro:build:wayland:t3-gem-o1 IMG_SIZE=16G
```

The first command can be skipped when validated boot artifacts for the selected
SDK revision already exist. The graphics build is required and is copied to
`/opt/ti-gpu` in the resulting image.

## Initial acceptance criteria

1. SDDM autologin starts `T3 Plasma (Wayland + PowerVR)`.
2. `loginctl` reports a `wayland` session with desktop `KDE`.
3. KWin maps `/opt/ti-gpu/lib/dri/pvr_dri.so`.
4. KWin reports `Imagination Technologies`, not `llvmpipe`.
5. HDMI, USB input, Wi-Fi and Bluetooth survive ten cold boots.
6. KWin and plasmashell show no restart loop or core dump.

Remote desktop, browser integration and branding are intentionally deferred
until this baseline passes on hardware.

The SDDM greeter intentionally keeps its distro-default display server. Only
the authenticated Plasma session is Wayland. This avoids running a nested
Weston greeter against the same DRM device immediately before KWin starts.
