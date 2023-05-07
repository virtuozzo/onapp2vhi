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

cp -f /proc/mounts /etc/mtab

sed -i 's/^GRUB_DISABLE_LINUX_UUID=true/#GRUB_DISABLE_LINUX_UUID=true/' /etc/default/grub
sed -i 's/^GRUB_DISABLE_UUID=true/#GRUB_DISABLE_UUID=true/' /etc/default/grub

if [ "$GRUB_VERSION" -lt 1 ];then
        grub-install --recheck $ROOT_DEV
else
  if [ -f /boot/grub/grub.cfg ]; then
        GRUB_CONF=/boot/grub/grub.cfg
  elif [ -f /boot/grub2/grub.cfg  ]; then
      GRUB_CONF=/boot/grub2/grub.cfg
  fi

        grub-install --recheck $ROOT_DEV || grub2-install --recheck $ROOT_DEV
        grub-mkconfig -o $GRUB_CONF || grub2-mkconfig -o $GRUB_CONF
fi

if  command -v update-grub &>/dev/null; then
	rm -f /boot/grub/menu.lst
	update-grub
fi
