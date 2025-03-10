#!/usr/bin/env bash
#
# NOTE: Must have PiXflat theme installed in the directory /usr/share/icons/PiXflat
#
# Sample usage: ./link-pixflat-icons.sh path=apps/accessories-document-viewer.png symlink=apps/atril.png
#

for ARG in "$@"; do
  eval "$ARG"
done

if [ -z "$path" ] || [ -z "$symlink" ]; then
    echo "usage: $0 path=<relative path to pixflat icon> symlink=<relative path to new symlink>" >&2
    exit 1
fi

readonly ICON_REL_PATH="$path"
readonly SYMLINK_PATH="$symlink"

readonly ICON_NAME=$(basename $ICON_REL_PATH)
readonly ICON_PATHS=$(cd /usr/share/icons/PiXflat && find . -name "*${ICON_NAME}*" -type f)
ICON_SIZES=""

for ICON_PATH in ${ICON_PATHS}; do
    ICON_SIZE=$(echo "$ICON_PATH" | cut -d'/' -f2)
    ICON_SIZES="${ICON_SIZES} ${ICON_SIZE}"
done

ICON_SIZES=$(echo "$ICON_SIZES" | uniq)

for ICON_SIZE in ${ICON_SIZES}; do
    echo "Path   : ../../../PiXflat/$ICON_SIZE/$ICON_REL_PATH"
    echo "Symlink: $ICON_SIZE/$SYMLINK_PATH"
    echo
    mkdir -p $(dirname "$ICON_SIZE/$SYMLINK_PATH")
    ln -sf "../../../PiXflat/$ICON_SIZE/$ICON_REL_PATH" "$ICON_SIZE/$SYMLINK_PATH"
done
