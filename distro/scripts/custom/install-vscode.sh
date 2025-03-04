#!/bin/bash

export DEBIAN_FRONTEND=noninteractive

mkdir -p /etc/apt/keyrings /etc/apt/sources.list.d \
&& wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/keyrings/packages.microsoft.gpg \
&& echo "deb [arch=amd64,arm64 signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list \
&& apt-get update -y \
&& apt-get install -y \
    apt-transport-https \
    code \
    git

# Extensions
ext=(
    "be5invis.vscode-icontheme-nomo-dark"
    "charliermarsh.ruff"
    "daylerees.rainglow"
    "eamodio.gitlens"
    "henriiik.vscode-sort"
    "jetpack-io.devbox"
    "mads-hartmann.bash-ide-vscode"
    "ms-python.python"
    "ms-python.debugpy"
    "ms-python.vscode-pylance"
    "ms-vscode.hexeditor"
    "spywhere.guides"
    "task.vscode-task"
)

chown -R gemstone:gemstone /home/gemstone

for i in "${ext[@]}"; do
    HOME=/home/gemstone code --disable-chromium-sandbox --user-data-dir=/home/gemstone/.config/Code/User --force --install-extension $i
done
