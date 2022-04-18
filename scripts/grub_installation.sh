#!/bin/bash

expect -c '
set timeout -1
spawn virsh console identifier
match_max 100000
expect -exact "Connected to domain identifier\r
Escape character is ^\]\r
"
send -- "\r"
expect "recovery login: "
send -- "root\r"
expect -exact "root\r\r
Password: "
send -- "forRecovery1\r"
expect -exact "\r
\[root@recovery ~\]# "
send -- "mkdir -p /sysroot"
expect -exact "mkdir -p /sysroot"
send -- "\r"
expect -exact "\r
\[root@recovery ~\]# "
send -- "mount /dev/vda1 /sysroot/"
send -- "\r"
expect -exact "\r
\[root@recovery ~\]# "
send -- "mount /dev/cdrom /mnt"
send -- "\r"
expect -exact "\r
\[root@recovery ~\]# "
send -- "/bin/cp -rf /mnt/provisiongrub.sh /sysroot/root/ProvisionGRUB.sh\r"
send -- "\r"
expect -exact "\r
\[root@recovery ~\]# "
send -- "mount --bind /dev /sysroot/dev"
expect -exact "mount --bind /dev /sysroot/dev"
send -- "\r"
expect -exact "\r
\[root@recovery ~\]# "
send -- "mount --bind /proc /sysroot/proc"
expect -exact "mount --bind /proc /sysroot/proc"
send -- "\r"
expect -exact "\r
\[root@recovery ~\]# "
send -- "mount --bind /sys /sysroot/sys"
expect -exact "mount --bind /sys /sysroot/sys"
send -- "\r"
expect -exact "\r
\[root@recovery ~\]# "
send -- "chroot /sysroot /bin/bash  /root/ProvisionGRUB.sh\r"
expect "#"
send -- "umount -R /sysroot"
expect -exact "umount -R /sysroot"
send -- "\r"
expect -exact "\r
\[root@recovery ~\]# "
send -- "exit\r"
expect "recovery login: "
send -- ""
expect eof
'
