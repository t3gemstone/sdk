# T3 Gemstone O1 Wayland build state

Last update: 2026-10-13 (Europe/Istanbul)

The build was intentionally interrupted after BitBake reached 3180/4335 tasks
(73%). All downloads, sstate objects, completed tasks, and partial build trees
remain under `/home/workdir/build`.

## Completed checks

- `task distro:verify:wayland WORKDIR=/home/workdir` passed.
- The PowerVR graphics build completed successfully.
- `pvr_dri.so` was verified as AArch64 ELF with a compatible GLIBC baseline.
- The pseudo/openat2 packaging failure was fixed with pseudo 1.9.7.
- Previously failing package tasks for `libssp-nonshared`, `bsd-headers`, and
  `linux-libc-headers` were rebuilt successfully.

## Resume

From PowerShell:

```powershell
wsl -d Ubuntu-22.04 --cd /home/workdir -- bash ./scripts/resume-wayland-build.sh
```

The command reuses the existing Yocto sstate and build directories. It then
builds the final 16 GiB Plasma Wayland distribution image.

