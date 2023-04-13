<domain xmlns:ns0="http://libvirt.org/schemas/domain/qemu/1.0" type="kvm">
  <name>identifier</name>
  <description>recovery</description>
  <memory>2048576</memory>
  <currentMemory>2048576</currentMemory>
  <vcpu current="1">4</vcpu>
  <vcpus>
    <vcpu enabled="yes" hotpluggable="no" id="0" order="1" />
  </vcpus>
  <cputune>
    <shares>1</shares>
  </cputune>
  <features>
    <pae />
    <acpi />
    <apic />
  </features>
  <os>
    <type arch="x86_64" machine="pc">hvm</type>
    <kernel>/onapp/tools/recovery/recovery-centos-7.7.kernel</kernel>
    <initrd>/onapp/tools/recovery/recovery-centos-7.7.initrd</initrd>
    <cmdline>root=live:CDLABEL=recovery-centos rootfstype=auto ro liveimg quiet rhgb rd.luks=0 rd.md=0 rd.dm=0 rdshell ip=10.63.0.124::10.63.0.1:255.255.255.0:recovery.kvm:eth0:off console=ttyS0,11520 password=$1$UvXIC532$IwuT/uTlEV9r..EewzL9h1 </cmdline>
  </os>
  <devices>
    <emulator>/usr/libexec/qemu-kvm</emulator>
    <disk device="cdrom" type="file">
      <source file="/onapp/tools/recovery/recovery-centos-7.7.iso" />
      <target bus="virtio" dev="hdb" />
      <readonly />
    </disk>
    <disk device="disk" type="file">
      <driver name="qemu" type="qcow2" />
      <source file="/tmp/dvcrmjyzvitvwm_20220708103453.qcow2" />
      <target bus="virtio" dev="vda" />
      <driver cache="none" discard="ignore" name="qemu" type="raw" />
    </disk>
    <disk device="cdrom" type="file">
      <source file="/onapp/tools/scripts/scripts.iso" />
      <target bus="ide" dev="hdc" />
      <readonly />
    </disk>

 <serial type="pty">
   <target port="0" />
 </serial>
 <console type="pty">
   <target port="0" type="serial" />
 </console>
    <input bus="usb" type="tablet" />
  </devices>
  <ns0:commandline>
    <ns0:arg value="-global" />
    <ns0:arg value="virtio-pci.disable-modern=on" />
  </ns0:commandline>
</domain>