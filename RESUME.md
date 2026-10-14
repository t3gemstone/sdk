# T3 Gemstone O1 Wayland build: continue commands

Run these commands from Windows PowerShell.

## Normal continuation

This is the preferred command. It verifies the integration, reuses the Yocto
sstate cache, completes any missing boot artifacts, and then builds the disk
image:

```powershell
wsl -d Ubuntu-22.04 --cd /home/workdir -- bash ./scripts/resume-wayland-build.sh
```

Enter the WSL `t3` user's sudo password when prompted.

## Continue only the final disk-image stage

Use this when the Yocto summary has already reported all 4335 tasks successful:

```powershell
wsl -d Ubuntu-22.04 --cd /home/workdir -- bash -lc "task distro:build:wayland:t3-gem-o1 WORKDIR=/home/workdir IMG_SIZE=14G"
```

The task automatically enables ARM64 binfmt support on WSL, prepares the WSL
device-directory compatibility path, rebuilds the local Yocto package index,
and invokes debos.

## Observe progress

In a second PowerShell window:

```powershell
wsl -d Ubuntu-22.04 --cd /home/workdir -- bash -lc "pgrep -af 'bitbake|debos|debootstrap|qemu-aarch64' || true; tail -n 80 build/debos/log.txt"
```

List generated artifacts:

```powershell
wsl -d Ubuntu-22.04 --cd /home/workdir -- bash -lc "find build/debos build/tmp-musl/deploy/images/t3-gem-o1 -maxdepth 2 -type f -printf '%p  %s bytes\n' 2>/dev/null | sort"
```

## Safe interruption

Press `Ctrl+C` once in the build terminal and wait until running tasks stop.
Do not run `clean` or `cleansstate`, and do not delete `/home/workdir/build`.
The normal continuation command above will reuse completed Yocto work.

## Useful verification

```powershell
wsl -d Ubuntu-22.04 --cd /home/workdir -- bash -lc "task distro:verify:wayland WORKDIR=/home/workdir"
wsl -d Ubuntu-22.04 --cd /home/workdir -- bash -lc "git status --short; git log -3 --oneline"
```

The build log is stored at `/home/workdir/build/debos/log.txt`.
