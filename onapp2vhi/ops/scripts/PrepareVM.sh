#!/bin/sh

PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
export PATH

if command -v grub-install &>/dev/null; then
        GRUB_VERSION="$(grub-install --version | grep  -Eo '[0-2]\.[0-9]{2}'| cut -f1 -d".")"
else
        GRUB_VERSION="$(grub2-install --version | grep  -Eo '[0-2]\.[0-9]{2}'| cut -f1 -d".")"
fi


if [ -e /dev/sda ]; then
        ROOT_DEV=/dev/sda
else
        ROOT_DEV=/dev/vda
fi

sed -i 's/^GRUB_DISABLE_LINUX_UUID=true/#GRUB_DISABLE_LINUX_UUID=true/' /etc/default/grub
sed -i 's/^GRUB_DISABLE_UUID=true/#GRUB_DISABLE_UUID=true/' /etc/default/grub

if [ "$GRUB_VERSION" -lt 1 ];then
#Run grub install
        grub-install --recheck $ROOT_DEV
        if  command -v update-grub &>/dev/null; then
                rm -f /boot/grub/menu.lst
                update-grub -y
        fi
else
        if [ -f /boot/grub/grub.cfg ]; then
                GRUB_CONF=/boot/grub/grub.cfg
        elif [ -f /boot/grub2/grub.cfg  ]; then
                GRUB_CONF=/boot/grub2/grub.cfg
        fi
#Run grub2 install
        if  command -v grub-install &>/dev/null; then
                grub-install --recheck $ROOT_DEV
        else
                grub2-install --recheck $ROOT_DEV
        fi
#Run mkconfig
        if  command -v grub-mkconfig &>/dev/null; then
                grub-mkconfig -o $GRUB_CONF
        else
                grub2-mkconfig -o $GRUB_CONF
        fi
fi

#RegenerateUUID
cp /etc/fstab /etc/fstab.backup

sed -n 's|^/dev/\([xvsh]\+d[a-z][0-9]\?\).*|\1|p' </etc/fstab >/tmp/devices   # Stores all /dev entries from fstab into a file

while read LINE; do                                                     # For each line in /tmp/devices
        UUID=`ls -l /dev/disk/by-uuid | grep "$LINE" | sed -n 's/^.* \([^ ]*\) -> .*$/\1/p'` # Sets the UUID name for that device
        sed -i "s|^/dev/${LINE}|UUID=${UUID}|" /etc/fstab               # Changes the entry in fstab to UUID form
done </tmp/devices
