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
        iputils-ping \
        libacl1 \
        libelf-dev \
        liblz4-tool \
        libncurses-dev \
        libsdl2-2.0-0 \
        libsdl2-dev \
        libssl-dev \
        locales \
        nano \
        openssl \
        parted \
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

# Allow minimum password length of image in Distrobox to be 1 character
RUN sed -i 's/pam_unix\.so obscure/pam_unix.so minlen=1 obscure/' /etc/pam.d/common-password
RUN echo gemstone > /etc/hostname

# Taskfile Installation
RUN curl --location https://taskfile.dev/install.sh | sudo sh -s -- -d -b /usr/local/bin && \
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

CMD ["bash"]
