<p align="center">
    <picture>
        <source media="(prefers-color-scheme: dark)" srcset=".meta/logo-dark.png" width="40%" />
        <source media="(prefers-color-scheme: light)" srcset=".meta/logo-light.png" width="40%" />
        <img alt="T3 Foundation" src=".meta/logo-light.png" width="40%" />
    </picture>
</p>

# T3 Gemstone SDK

 [![T3 Foundation](./.meta/t3-foundation.svg)](https://www.t3vakfi.org/en) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) [![Built with Distrobox](https://img.shields.io/badge/Built_with-distrobox-red)](https://github.com/89luca89/distrobox) [![Built with Devbox](https://www.jetify.com/img/devbox/shield_galaxy.svg)](https://www.jetify.com/devbox/docs/contributor-quickstart/)

## What is it?

This project includes all the necessary work for compiling the operating system, kernel, and other tools found on T3 Gemstone boards, and is intended for developers who wish to prepare a GNU/Linux Distribution.

All details related to the project can be found at https://docs.t3gemstone.org/en/sdk. Below, only a summary of how to perform the installation is provided.

##### 1. Install Docker and jetify-devbox on the host computer.

```bash
user@host:$ ./setup.sh
```

<a name="section-ii"></a>
##### 2. After the installation is successful, activate the jetify-devbox shell to automatically install tools such as Distrobox, taskfile, etc.

```bash
user@host:$ devbox shell
```

##### 3. Download the repositories, create a Docker image, and enter it.

```bash
📦 devbox:sdk> task fetch
📦 devbox:sdk> task permissions
📦 devbox:sdk> task box
```

##### 4. Build the Yocto recipes and Gemstone distro.

```bash
# Show all available tasks and environment variables
🚀 distrobox:workdir> task default

# Build kernel, bootloader, initrd
# Note: First build takes approximately 2 hours and you need at least 32GB empty disk space
# Note: MACHINE can be 'intel-corei7-64', 'beagley-ai' or 't3-gem-o1'
🚀 distrobox:workdir> task yocto:build MACHINE=intel-corei7-64

# Pack Gemstone Distro
🚀 distrobox:workdir> task distro:build MACHINE=intel-corei7-64 DISTRO_ARCH=amd64 DISTRO_TYPE=desktop DISTRO_BASE=ubuntu IMG_SIZE=16G

# After build images, run virtual machine
🚀 distrobox:workdir> task yocto:runqemu MACHINE=intel-corei7-64 DISTRO_ARCH=amd64 DISTRO_TYPE=desktop DISTRO_BASE=ubuntu WORKDIR=$PWD
```

### Screencast

[![asciicast](https://asciinema.org/a/KDwPPlCV2wxzpwDB4sLseW2X9.svg)](https://asciinema.org/a/KDwPPlCV2wxzpwDB4sLseW2X9)

### Troubleshoting

#### First Installation of Docker

Docker is installed on your system via the `./setup.sh` command. If you are installing Docker for the first time, you must log out and log in again after the installation is complete.

#### Debos Segmentation Fault Error

When you perform the compilation process with the task:distro command many times, debos may occasionally give a "Segmentation Fault" error. To solve this problem, first try running the following command inside [devbox shell](#section-ii)

```bash
# Activate devbox shell
user@host:$ devbox shell
```

```bash
📦 devbox:sdk> distrobox stop gemstone-sdk
```

if it does not work, run the destroy command.

```bash
📦 devbox:sdk> task destroy
```

#### Yocto Issues

```bash
# Activate devbox shell
user@host:$ devbox shell
```

```bash
# Stop distrobox
📦 devbox:sdk> distrobox stop gemstone-sdk

# Start and Enter distrobox image
📦 devbox:sdk> task box

# Clean yocto image
🚀 distrobox:workdir> task yocto:build MACHINE=intel-corei7-64 TARGET='-c clean -c cleansstate gemstone-image-rd virtual/kernel'

# Rebuild
🚀 distrobox:workdir> task yocto:build MACHINE=intel-corei7-64
```
