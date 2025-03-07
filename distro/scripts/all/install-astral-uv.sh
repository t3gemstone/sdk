#!/bin/bash

set -euo pipefail

curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="/usr/bin/" sh

mkdir -p /etc/bash_completion.d

echo 'eval "$(uv generate-shell-completion bash)"' | tee /etc/bash_completion.d/uv
