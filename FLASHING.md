# Flash the T3 Gemstone O1 Wayland image

## Recommended: Raspberry Pi Imager or balenaEtcher

1. Insert a microSD card with at least 16 GB capacity.
2. Select the distributed `.img.zst` file as a custom image.
3. Select the microSD card, verify the target carefully, and start writing.
4. Safely eject the card after verification completes.
5. Insert it into the T3 Gemstone O1 and power the board on.

Raspberry Pi Imager is only the writing tool here; the image itself is built
for T3 Gemstone O1, not for Raspberry Pi hardware.

## Linux command line

```bash
zstd -dc gemstone-wayland-desktop-v2026.2-ubuntu-jammy-t3-gem-o1.img.zst \
  | sudo dd of=/dev/sdX bs=16M status=progress conv=fsync
```

Replace `/dev/sdX` with the whole microSD device. Do not use a partition such
as `/dev/sdX1`.

Before writing, validate the distributed archive:

```bash
sha256sum -c SHA256SUMS
```
