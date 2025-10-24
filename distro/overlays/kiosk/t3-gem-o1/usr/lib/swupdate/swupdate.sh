#!/bin/sh

# Override these variables in sourced script(s) located
# in /usr/lib/swupdate/conf.d or /etc/swupdate/conf.d
SWUPDATE_ARGS="-v ${SWUPDATE_EXTRA_ARGS}"
SWUPDATE_WEBSERVER_ARGS=""
SWUPDATE_SURICATTA_ARGS=""

rootdev=$(sed -n 's/.*root=\([^ ]*\).*/\1/p' /proc/cmdline)

case "$rootdev" in
    *ROOTFS_A*)
        next_slot="rootfsB"
        ;;
    *ROOTFS_B*)
        next_slot="rootfsA"
        ;;
    *)
        echo "Unable to find slot from 'root' kernel command line parameter"
        ;;
esac

if [ -z "$next_slot" ]; then
    env_slot=$(fw_printenv slot | grep '^slot=' | cut -d '=' -f 2)

    case "$env_slot" in
        A)
            next_slot="rootfsB"
            ;;
        B)
            next_slot="rootfsA"
            ;;
        *)
            echo "Unable to find slot from 'slot' U-Boot environment variable"
            echo "Falling back and selecting rootfsB as target partition"
            next_slot="rootfsB"
            ;;
    esac
fi

echo "Target rootfs is: $next_slot"

# source all files from /etc/swupdate/conf.d and /usr/lib/swupdate/conf.d/
# A file found in /etc replaces the same file in /usr
for f in `(test -d /usr/lib/swupdate/conf.d/ && ls -1 /usr/lib/swupdate/conf.d/; test -d /etc/swupdate/conf.d && ls -1 /etc/swupdate/conf.d) | sort -u`; do
  if [ -f /etc/swupdate/conf.d/$f ]; then
    . /etc/swupdate/conf.d/$f
  else
    . /usr/lib/swupdate/conf.d/$f
  fi
done

#  handle variable escaping in a simple way. Use exec to forward open filedescriptors from systemd open.
if [ "$SWUPDATE_WEBSERVER_ARGS" != "" -a  "$SWUPDATE_SURICATTA_ARGS" != "" ]; then
  exec /usr/bin/swupdate $SWUPDATE_ARGS -w "$SWUPDATE_WEBSERVER_ARGS" -u "$SWUPDATE_SURICATTA_ARGS"
elif [ "$SWUPDATE_WEBSERVER_ARGS" != "" ]; then
  exec /usr/bin/swupdate $SWUPDATE_ARGS -w "$SWUPDATE_WEBSERVER_ARGS"
elif [ "$SWUPDATE_SURICATTA_ARGS" != "" ]; then
  echo "Full command is: /usr/bin/swupdate $SWUPDATE_ARGS -u '$SWUPDATE_SURICATTA_ARGS'"
  exec /usr/bin/swupdate $SWUPDATE_ARGS -u "$SWUPDATE_SURICATTA_ARGS"
else
  exec /usr/bin/swupdate $SWUPDATE_ARGS
fi
