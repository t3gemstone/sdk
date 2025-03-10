#!/usr/bin/env bash
#
# Sample usage: ./link-hedera-icons.sh path=settings-effects.png symlink=apps/org.xfce.xfwm4-tweaks.png
#

for ARG in "$@"; do
  eval "$ARG"
done

if [ -z "$path" ] || [ -z "$symlink" ]; then
    echo "usage: $0 path=<relative path to icon> symlink=<relative path to new symlink>" >&2
    exit 1
fi

readonly ICON_PATH="$path"
readonly SYMLINK_PATH="$symlink"

for i in 16 24 32 240; do
    pushd "${i}x${i}"
    ln -sf "$ICON_PATH" "$SYMLINK_PATH"
    popd
done
