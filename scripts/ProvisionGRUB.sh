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

cp -u /proc/mounts /etc/mtab

sed -i 's/^GRUB_DISABLE_LINUX_UUID=true/#GRUB_DISABLE_LINUX_UUID=true/' /etc/default/grub
sed -i 's/^GRUB_DISABLE_UUID=true/#GRUB_DISABLE_UUID=true/' /etc/default/grub

if [ "$GRUB_VERSION" -lt 1 ];then
#Run grub install
        grub-install --recheck $ROOT_DEV
        if  command -v update-grub &>/dev/null; then
                rm -f /boot/grub/menu.lst
		sed -i 's/kopt="$default_kopt"/kopt="$default_kopt net.ifnames=0 biosdevname=0"/g' /usr/sbin/update-grub
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
