# T3 Gemstone O1 Wayland build state

Last update: 2026-10-14 (Europe/Istanbul)

The PowerVR accelerated Plasma Wayland image build is complete. Yocto
successfully completed all 4335 tasks, and the final debos recipe completed
without an error.

## Final image

- Image: `build/debos/gemstone-wayland-desktop-v2026.2-ubuntu-jammy-t3-gem-o1.img`
- Raw size: 14,000,000,000 bytes
- Partitioning: MBR, 128 MiB FAT32 boot partition, Btrfs root partition
- Root filesystem payload: approximately 1.5 GiB

## Verified contents

- TI 6.12.24 kernel, DTB, overlays, initramfs and U-Boot files
- PowerVR `pvr_dri.so`, DRI support library and `pvrsrvkm` kernel module
- KDE Plasma Wayland, KWin Wayland, SDDM, PipeWire and portals
- Automatic `t3-plasmawayland.desktop` session selection
- T3 Gemstone theme, launcher icon, system-status widget and 17 wallpapers
- T3 Gemstone Launch Eclipse as the default wallpaper

The authoritative verification report is written to
`build/debos/verification-report.txt`.

## Rebuild

From Windows PowerShell:

```powershell
wsl -d Ubuntu-22.04 --cd /home/workdir -- bash ./scripts/resume-wayland-build.sh
```

The build reuses the existing Yocto sstate and download caches.
