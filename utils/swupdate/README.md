# Quick SWUpdate Guide

This tutorial shows how to use the experimental SWUpdate implementation on T3-GEM-O1 board with Gemstone Kiosk image.

## Installing SWUpdate based Image for the First Time

### 1. Generate Kiosk Image with Debos

```sh
# Generate kiosk image
🚀 distrobox:workdir> task distro:build MACHINE=t3-gem-o1 DISTRO_TYPE=kiosk DISTRO_BASE=ubuntu DISTRO_SUITE=jammy IMG_SIZE=4G
```

### 2. Write the Image to the Board Using U-Boot Console

```sh
# On host PC, split the image into 1GB chunks and put them onto TFTP directory
user@host:$ split -b 1GB "$KIOSK_IMG_FILE" "$TFTP_DIR/gemstone_"

# Download the image and write it to eMMC
u-boot> mmc dev 0; setenv loadaddr 0xc2000000; dhcp; setenv image_addr "0xc2000000"; tftp ${image_addr} gemstone_aa; mmc write ${image_addr} 0x0 0x1dcd65; tftp ${image_addr} gemstone_ab; mmc write ${image_addr} 0x1dcd65 0x1dcd65; tftp ${image_addr} gemstone_ac; mmc write ${image_addr} 0x3b9aca 0x1dcd65; tftp ${image_addr} gemstone_ad; mmc write ${image_addr} 0x59682f 0x1dcd65
```

### 3. Save the U-Boot Environment to the boot partition

Set boot mode switches to eMMC UDA filesystem boot mode (11000010 00000000).

```sh
# Reset the board so it can boot with the newly written U-Boot
u-boot> reset

# Set the environment to default state and write it to boot partition
u-boot> env default -a; saveenv

# Reset the board again but this time let it boot
u-boot> reset
```

### 4. Setup Update Server

There is a basic HTTP based update server code in SWUpdate source repository. We will use it for simplicity. For
production Hawkbit is preferred.

```sh
# Clone SWUpdate repository to anywhere you want
user@host:$ git clone https://github.com/sbabic/swupdate.git && \
                cd swupdate && \
                git checkout 2025.05 && \
                mkdir -p examples/suricatta/firmwares && \
                cd examples/suricatta && \
                wget http://bottlepy.org/bottle.py
```

### 5. Generate SWU File and Copy It to Server

Suricatta (the service which checks for updates periodically), sends hw (t3-gem-o1), sw (1.0) and sp (1.0) identifiers
to the update server. Server then merges these identifiers into one string (removes non-alphanumeric chars) and
searches for a file which matches with this string. That's why we change SWU file name to `fw10hwt3gemo1sp10`.

```sh
# Generate SWU package
🚀 distrobox:workdir> task utils:generate-swu

# Copy generated file to server and change the name to suricatta format
user@host:$ cp <sdk-dir>/build/swupdate/gemstone-kiosk-*-t3-gem-o1.swu <swupdate-repo-dir>/examples/suricatta/firmwares/fw10hwt3gemo1sp10
```

### 6. Set IP Address of Your Host

Host PC: 192.168.1.11

Update server IP address is hardcoded into kiosk image. So you need to set it correctly. IP address of T3-GEM-O1 is
also hardcoded and it is 192.168.1.12. Use the commands below to set your Host PC IP address.

```sh
# Host PC
sudo nmcli con add type ethernet ifname eno1 con-name eno1-static ipv4.addresses 192.168.1.11/24 ipv4.method manual
sudo nmcli con up eno1-static
```

Note: `eno1` is the Ethernet interface name for Host PC and it can be different on your PC. Check it by runnning
`ip link` command.

### 6. Run the Server and Follow SWUpdate Logs to See Progress

```sh
# Run the server
user@host:$ cd <swupdate-repo-dir>/examples/suricatta
user@host:$ python3 server_general.py

# Watch the logs on your board
gemstone@t3-gem-o1:$ sudo journalctl -u swupdate.service -f

# If installation succeeds, you will see the output below.
# => [WARN ] : SWUPDATE running :  [server_has_pending_action] : An already installed update is pending testing.
```

Close the server before rebooting the board. If you keep server open after rebooting the board, then it will try to
download the update file again. It will not try to download image before you reboot so you don't need to hurry.

### 7. Reboot the Board and Check If the Update was Successful

```sh
gemstone@t3-gem-o1:$ cat /proc/cmdline

# => ... root=LABEL=ROOTFS_B rw rootfstype=btrfs ...
```

If you see `root=LABEL=ROOTFS_B` that means you use the rootfs from SWU file. Next time you install an update,
you will see that output will be `root=LABEL=ROOTFS_A`.

```sh
gemstone@t3-gem-o1:$ sudo fw_printenv ustate
# => Environment OK, copy 0
# => ustate=0

gemstone@t3-gem-o1:$ sudo fw_printenv upgrade_available
# => Environment OK, copy 0
# => upgrade_available=0

gemstone@t3-gem-o1:~$ sudo fw_printenv bootcount
# => Environment OK, copy 0
# => bootcount=0
```

If your output is same as above that means you updated your system successfully.

## Checking If A/B Partitioning Mechanism Works

U-Boot increases `bootcount` variable by 1 on every boot if `upgrade_available=1`. After installing the update,
a properly running OS should set `upgrade_available` to 0. If it can't, that means it is faulty. When boot counter
hits 3, U-Boot will run `altbootcmd` instead of `bootcmd`. This way we can switch to old partition if the updated
partition fails to boot the system.

```sh
# Note the current rootfs partition. In out case ROOTFS_B
gemstone@t3-gem-o1:$ cat /proc/cmdline
# => ... root=LABEL=ROOTFS_B rw rootfstype=btrfs ...

# Set the upgrade_available variable to 1
gemstone@t3-gem-o1:~$ sudo fw_setenv upgrade_available 1
# => Environment OK, copy 0

# Reboot your system and enter U-Boot console by pressing 'Space' key in right after rebooting.
gemstone@t3-gem-o1:~$ sudo reboot
# => ...

# Check for bootcount variable. You should see that it is increased to 1.
u-boot> printenv bootcount
# => bootcount=1

# Reset the board and re-enter the U-Boot console
u-boot> reset
u-boot> printenv bootcount
# => bootcount=2

# Re-run the two commands above until you see this output from U-Boot
# Don't enter to console when you see it, let the system boot
# => Warning: Bootlimit (3) exceeded. Using altbootcmd.

# Check the current rootfs partition. If it is different from the output earlier then rollback was successful.
gemstone@t3-gem-o1:$ cat /proc/cmdline
# => ... root=LABEL=ROOTFS_A rw rootfstype=btrfs ...
```
