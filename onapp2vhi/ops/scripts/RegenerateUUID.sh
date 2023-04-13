#!/bin/bash
cp /etc/fstab /etc/fstab.backup

sed -i '/ swap / s/^/#/' /etc/fstab					#Disable swap

sed -n 's|^/dev/\([xvsh]\+da[0-9]\?\).*|\1|p' </etc/fstab >/tmp/devices   # Stores primary /dev entries from fstab into a file

while read LINE; do                                                     # For each line in /tmp/devices
        UUID=`ls -l /dev/disk/by-uuid | grep "$LINE" | sed -n 's/^.* \([^ ]*\) -> .*$/\1/p'` # Sets the UUID name for that device
        sed -i "s|^/dev/${LINE}|UUID=${UUID}|" /etc/fstab               # Changes the entry in fstab to UUID form
done </tmp/devices
