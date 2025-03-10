#!/usr/bin/env bash
#
# NOTE: Must have Hedera theme installed in the directory /usr/share/icons/Hedera
#
# Sample usage: ./copy-hedera-icons.sh src_category=applications name=settings-effects.png dest_category=apps
#

for ARG in "$@"; do
  eval "$ARG"
done

if [ -z "$src_category" ] || [ -z "$dest_category" ] || [ -z "$name" ]; then
    echo "usage: $0 src_category=<source category> name=<source icon name> dest_category=<destination category>" >&2
    exit 1
fi

readonly SRC_CATEGORY="$src_category"
readonly DEST_CATEGORY="$dest_category"
readonly ICON_NAME="$name"

for i in 16 24 32 240; do
    cp -P "/usr/share/icons/Hedera/$i/$SRC_CATEGORY/$ICON_NAME" "${i}x${i}/$DEST_CATEGORY"
done
