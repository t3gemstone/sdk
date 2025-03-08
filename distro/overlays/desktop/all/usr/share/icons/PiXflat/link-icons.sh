#!/usr/bin/env bash
#
# Sample usage: ./link-icons path=apps/xfce4-appfinder.png dest=../actions/system-search.png
#

for ARG in "$@"; do
  eval "$ARG"
done

if [ -z "$dest" ] || [ -z "$path" ]; then

    echo "usage: $0 dest=<link destination> path=<link path>" >&2
    exit 1
fi

readonly LINK_DEST="$dest"
readonly LINK_PATH="$path"

LINK_DEST_NAME=$(basename $LINK_DEST)
LINK_DEST_DIRS=$(find . -name "*${LINK_DEST_NAME}*" -type f)
LINK_PATH_DIRS=""

for DIR in ${LINK_DEST_DIRS}; do
    PATH_DIR=$(echo "$DIR" | cut -d'/' -f1,2)
    LINK_PATH_DIRS="${LINK_PATH_DIRS} ${PATH_DIR}"
done

LINK_PATH_DIRS=$(echo "$LINK_PATH_DIRS" | uniq)

for DIR in ${LINK_PATH_DIRS}; do
    echo "Dest: $LINK_DEST"
    echo "Path: $DIR/$LINK_PATH"
    echo
    ln -sf "$LINK_DEST" "$DIR/$LINK_PATH"
done
