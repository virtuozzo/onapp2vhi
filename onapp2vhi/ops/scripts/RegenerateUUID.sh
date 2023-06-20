#!/bin/bash
DATE=`date +%R-%m-%d-%Y`
cp /etc/fstab /etc/fstab.onapp2vhi$DATE

sed -n 's|^/dev/\([xvsh]\+da[0-9]\?\).*|\1|p' </etc/fstab >/tmp/devices   			# Stores primary /dev entries from fstab into a file

while read LINE; do                                                     			# For each line in /tmp/devices
        UUID=`ls -l /dev/disk/by-uuid | grep "$LINE" | sed -n 's/^.* \([^ ]*\) -> .*$/\1/p'` 	# Sets the UUID name for that device
	if [ ! -z "${UUID}" ]; then
        	sed -i "s|^/dev/${LINE}|UUID=${UUID}|" /etc/fstab               		# Changes the entry in fstab to UUID form
	fi
done </tmp/devices

sed -i "s|^/dev/vd|/dev/sd|" /etc/fstab			                			# Changes the entry in fstab from vd to sd
