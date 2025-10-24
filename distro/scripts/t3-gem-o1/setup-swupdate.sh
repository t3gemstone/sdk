#!/bin/bash

set -euo pipefail

ldconfig

echo -e 'swupdate=1\nfirstboot=1' > /boot/uEnv.txt

cat > /etc/fstab << 'EOF'
LABEL=BOOT	/boot	vfat	defaults	0	2
LABEL=DATA	/data	btrfs	defaults	0	1
EOF

chmod 0644 /etc/fstab

systemctl enable boot-succeeded
systemctl enable swupdate
