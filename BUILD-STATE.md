# T3 Gemstone O1 Wayland build state

Last update: 2026-10-13 (Europe/Istanbul)

The build was intentionally and cleanly interrupted on 2026-10-13 after
BitBake reached 4284/4335 tasks (98%). BitBake waited for all running tasks to
finish before exiting. All downloads, sstate objects, completed tasks, and
partial build trees remain under `/home/workdir/build`.

## Completed checks

- `task distro:verify:wayland WORKDIR=/home/workdir` passed.
- The PowerVR graphics build completed successfully.
- `pvr_dri.so` was verified as AArch64 ELF with a compatible GLIBC baseline.
- The pseudo/openat2 packaging failure was fixed with pseudo 1.9.7.
- Previously failing package tasks for `libssp-nonshared`, `bsd-headers`, and
  `linux-libc-headers` were rebuilt successfully.
- The main and K3 R5 Rust/LLVM stages completed.
- The Linux kernel compile, kernel module compile, and kernel Debian packaging
  stages completed.
- OP-TEE and the remaining native Python/Rust helper tasks progressed during
  the final run; no task failure occurred before the intentional stop.

## Resume

From PowerShell:

```powershell
wsl -d Ubuntu-22.04 --cd /home/workdir -- bash ./scripts/resume-wayland-build.sh
```

The command reuses the existing Yocto sstate and build directories. It then
builds the final 16 GiB Plasma Wayland distribution image.

Do not run `clean`, `cleansstate`, or delete `/home/workdir/build`; those would
discard the resumable state. The previous command returning exit status 1 is
expected because the build was stopped with Ctrl+C, not because a task failed.

