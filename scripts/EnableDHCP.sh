#!/bin/bash

OS=`uname -s`
REV=`uname -r`
MACH=`uname -m`


if [ "${OS}" = "Linux" ] ; then
	KERNEL=$(uname -r)
	if [ -f /etc/redhat-release ] ; then
		DIST='RedHat'
		PSUEDONAME=$(sed s/.*\(// < /etc/redhat-release | sed s/\)//)
		REV=$(sed s/.*release\ // < /etc/redhat-release | sed s/\ .*//)
	elif [ -f /etc/debian_version ] ; then
		if [ "$(awk -F= '/DISTRIB_ID/ {print $2}' /etc/lsb-release)" = "Ubuntu" ]; then
			DIST="Ubuntu"
		else
			DIST="Debian $(cat /etc/debian_version)"
			REV=""
		fi
	fi
	OSSTR="${OS} ${DIST} ${REV}(${PSUEDONAME} ${KERNEL} ${MACH})"
  echo ${OSSTR}
fi

if [ "${DIST}" = "RedHat" ] ; then
	find /etc/sysconfig/network-scripts/ -type f -iname "ifcfg-*" -print | grep -v "ifcfg-lo" | xargs -d '\n' rm
	cat << EOF > /etc/sysconfig/network-scripts/ifcfg-eth0
DEVICE=eth0
BOOTPROTO=dhcp
ONBOOT=yes
EOF
fi

if [ "${DIST}" = "Ubuntu" ] ; then
	cat << EOF > /etc/network/interfaces
# The loopback network interface
auto lo
iface lo inet loopback
# The primary network interface
auto eth0
iface eth0 inet dhcp
EOF
fi

if [ "{$DIST}" = "Debian" ] ; then
        cat << EOF > /etc/network/interfaces
# The loopback network interface
auto lo
iface lo inet loopback
# The primary network interface
auto eth0
iface eth0 inet dhcp
EOF
fi
