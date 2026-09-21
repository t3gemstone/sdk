FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
        bash \
        binfmt-support \
        build-essential \
        ca-certificates \
        ccache \
        chrpath \
        cmake \
        cryptsetup \
        cpio \
        curl \
        debianutils \
        debootstrap \
        diffstat \
        dosfstools \
        file \
        gawk \
        gcc \
        git \
        initramfs-tools \
        iputils-ping \
        libacl1 \
        libdrm-dev \
        libelf-dev \
        libinih-dev \
        libinput-dev \
        liblz4-tool \
        libncurses-dev \
        libsdl2-2.0-0 \
        libsdl2-dev \
        libssl-dev \
        libsystemd-dev \
        libxkbcommon-dev \
        locales \
        meson \
        nano \
        openssl \
        parted \
        pkg-config \
        python3 \
        python3-git \
        python3-jinja2 \
        python3-pexpect \
        python3-pip \
        python3-subunit \
        qemu-system-arm \
        qemu-system-x86 \
        qemu-user \
        qemu-user-static \
        scdoc \
        sed \
        socat \
        software-properties-common \
        sudo \
        tar \
        texinfo \
        udev \
        unzip \
        vim \
        wget \
        x11-xserver-utils \
        xterm \
        xz-utils \
        zstd \
    && locale-gen en_US.UTF-8

RUN rm -f /etc/os-release && cp /usr/lib/os-release /etc/os-release

# add Pardus 23 keyring
RUN wget -q https://depo.pardus.org.tr/pardus/pool/main/p/pardus-archive-keyring/pardus-archive-keyring_2021.1_all.deb && \
    dpkg -i pardus-archive-keyring_2021.1_all.deb && \
    rm pardus-archive-keyring_2021.1_all.deb

# Allow minimum password length of image in Distrobox to be 1 character
RUN sed -i 's/pam_unix\.so obscure/pam_unix.so minlen=1 obscure/' /etc/pam.d/common-password
RUN echo gemstone > /etc/hostname

# Taskfile Installation
RUN curl --location https://github.com/go-task/task/releases/download/v3.50.0/task_3.50.0_linux_amd64.deb --output ~/task_3.50.0_linux_amd64.deb && \
    sudo apt install ~/task_3.50.0_linux_amd64.deb && \
    task --completion bash > /etc/bash_completion.d/task

# VCS Repotool
RUN pip install vcstool --force-reinstall && \
    cp /usr/local/share/vcstool-completion/vcs.bash /etc/bash_completion.d/vcs

# Debos requirements
RUN apt-get install -y \
        binfmt-support \
        bmap-tools \
        btrfs-progs \
        debian-archive-keyring \
        debian-keyring \
        dosfstools \
        e2fsprogs \
        equivs \
        f2fs-tools \
        fdisk \
        golang \
        libglib2.0-dev \
        libostree-dev \
        systemd-container \
        ubuntu-keyring

# Debos
RUN cd /tmp && \
    export GOPATH=/tmp/debos && \
    go install -v github.com/t3gemstone/debos/cmd/debos@v1.1.3.6 && \
    cp /tmp/debos/bin/debos /usr/local/bin && \
    rm -rf /tmp/debos

# arm64 cross toolchain for 'task graphics:build' (TI mesa-pvr).
# The GPU userspace has to match the target rootfs ABI (jammy, glibc 2.35), so it
# cannot come out of Yocto -- that toolchain is musl. Cross building here against
# the arm64 ports archive gives binaries the Ubuntu/Debian rootfs can actually load.
RUN sed -i 's|^deb http|deb [arch=amd64] http|' /etc/apt/sources.list && \
    printf '%s\n' \
        'deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports jammy main restricted universe multiverse' \
        'deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports jammy-updates main restricted universe multiverse' \
        'deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports jammy-security main restricted universe multiverse' \
        > /etc/apt/sources.list.d/arm64-ports.list && \
    dpkg --add-architecture arm64 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        bison \
        crossbuild-essential-arm64 \
        flex \
        ninja-build \
        python3-mako \
        libdrm-dev:arm64 \
        libexpat1-dev:arm64 \
        libzstd-dev:arm64 \
        zlib1g-dev:arm64

CMD ["bash"]
