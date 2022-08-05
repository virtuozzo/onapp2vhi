#!/usr/bin/env python2

import os
import re
import sys
import xml
import json
import click
import time
import xml.etree.ElementTree as KVMxml
from click_default_group import DefaultGroup

plug_path = os.getcwd()
# logs.info plug_path
sys.path.append(plug_path)
sys.path.append(plug_path + '/cfg')
sys.path.append(plug_path + '/inc')

from o2v_config import *
from functions import *
from onapp_helpers import *


@click.group(cls=DefaultGroup, default='vm', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn', '--tmpl', '--label', '--template-label', default='', help="OnApp template label.")
@click.option('--verb', '-v', '--v', '--verbosity', default='', help="Verbolity level of values between 0 and 8")
# click.argument('name',default='') - not used
def vm(idn='', vhip='', verb=''):
    if idn == '':
        logs.info('You need to pass OnApp template label value through --template-label=? parameter ')
        exit(17)

    if verb == '': verb = str(VERBOSITY)
    if not str(verb).isdigit():
        logs.info("Effor: '--verbosity' parameter should be a number")
        exit(11)
    if int(verb) < 0 or int(verb) > 8:
        logs.info("Effor: '--verbosity' parameter should be a number between 0 and 8")
        exit(12)
    if verb != '':
        verbosity = int(verb)
    else:
        verbosity = int(VERBOSITY)

    TMPL_LABEL = idn

    # --step_1--#
    # --OnApp: get source template parameters--#

    NOTE = """ -- OnApp: get source template parameters -- """
    URL = ONAPP_CP_URL + "/templates.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c --arg template_label \"{tmpl_label}\" '.[] | select(.image_template.label==$template_label) | [ .image_template.label, .image_template.id, .image_template.min_disk_size, .image_template.file_name ] '".format(
        user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL, tmpl_label=TMPL_LABEL)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    TMPL_label = str(json.loads(ou)[0]).encode('ascii')
    TMPL_id = int(json.loads(ou)[1])
    TMPL_disk_size = int(json.loads(ou)[2])
    TMPL_file_name = str(json.loads(ou)[3]).encode('ascii')

    # --step_2--#
    # --OnApp: Create QCOW disk at OnApp hypervisor --#

    NOTE = """ -- Create QCOW disk at OnApp hypervisor -- """

    CMD = "ssh -p{ssh_port} {sshopt} root@{hv_ip} 'qemu-img create -o cluster_size=1048576,lazy_refcounts=on -f qcow2 /tmp/{disk_name}.qcow2 {disk_size}G' ".format(
        hv_ip=ONAPP_HV_IP, ssh_port=ONAPP_SSH_PORT, sshopt=SSH_OPTS, disk_name=TMPL_file_name, disk_size=TMPL_disk_size)
    (rc, ou) = run_command(CMD, verbosity, 0)

    # --step_3--#
    # --OnApp: Create QCOW disk at OnApp hypervisor --#

    NOTE = """ -- Deploy QCOW disk from template at OnApp hypervisor -- """

    CMD = """ssh -p{ssh_port} {sshopt} root@{hv_ip} "
guestfish <<EOF
add /tmp/{disk_name}.qcow2
run
part-disk /dev/sda mbr
mke2fs /dev/sda1 fstype:ext4
mount /dev/sda1 /
copy-in /onapp/backups/templates/{disk_name} /
rename /{disk_name} /tmplroot
umount /
exit
EOF" """.format(hv_ip=ONAPP_HV_IP, ssh_port=ONAPP_SSH_PORT, sshopt=SSH_OPTS, disk_name=TMPL_file_name)
    (rc, ou) = run_command(CMD, verbosity, 0)

    # Generate recovery config xml
    tree = KVMxml.parse('scripts/recovery-tmpl.xml')
    root = tree.getroot()
    for device in root.findall("devices"):
        for disk in device.findall("disk"):
            if disk.attrib['device'] == "disk":
                for source in disk.findall('source'):
                    source.attrib['file'] = "/tmp/{disk_name}.qcow2".format(disk_name=TMPL_file_name)
    tree.write('scripts/recovery-tmpl.xml.mg')

    # --OnApp: Run scp--#
    logs.info('-------')
    #    logs.info("-- OnApp: Copy scripts and configs to HV [{hv_ip}] --".format(hv_ip=ONAPP_HV_IP))
    CMD = "scp -P{ssh_port} {sshopt} -r scripts  root@{hv_ip}:/onapp/tools/".format(hv_ip=ONAPP_HV_IP,
                                                                                    ssh_port=ONAPP_SSH_PORT,
                                                                                    sshopt=SSH_OPTS, )
    (rc, ou) = run_command(CMD, verbosity, 0)

    # --step_5--#
    # --OnApp: Start VM is recovery mode --#
    logs.info('-------')
    logs.info("-- OnApp: Start VM is recovery mode  on HV [{hv_ip}] --".format(hv_ip=ONAPP_HV_IP))
    CMD = "ssh -p{ssh_port} {sshopt} root@{hv_ip} 'virsh create /onapp/tools/scripts/recovery-tmpl.xml.mg'".format(
        hv_ip=ONAPP_HV_IP, ssh_port=ONAPP_SSH_PORT, sshopt=SSH_OPTS, )
    (rc, ou) = run_command(CMD, verbosity, 0)

    # --step_8--#
    # --OnApp: Install grub --#
    logs.info('-------')
    logs.info("-- OnApp: Install grub in recovery VM on HV [{hv_ip}] --".format(hv_ip=ONAPP_HV_IP))
    CMD = "ssh -t -t -p{ssh_port} {sshopt} root@{hv_ip} sh -c -l '/onapp/tools/scripts/tmpl_grub_install.sh'".format(
        hv_ip=ONAPP_HV_IP, ssh_port=ONAPP_SSH_PORT, sshopt=SSH_OPTS, )
    (rc, ou) = run_command(CMD, verbosity, 0)

    # --step_8--#
    # --OnApp: Shutdown VM  --#
    logs.info('-------')
    logs.info("-- OnApp: shutdown recovery VM on HV [{hv_ip}] --".format(hv_ip=ONAPP_HV_IP))
    CMD = "ssh -p{ssh_port} {sshopt} root@{hv_ip} 'virsh shutdown identifier'".format(hv_ip=ONAPP_HV_IP,
                                                                                      ssh_port=ONAPP_SSH_PORT,
                                                                                      sshopt=SSH_OPTS, )
    (rc, ou) = run_command(CMD, verbosity, 0)
    while rc != 1:
        time.sleep(30)
        CMD = "ssh -p{ssh_port} {sshopt} root@{hv_ip} 'virsh dominfo identifier | grep -w State'".format(
            hv_ip=ONAPP_HV_IP, ssh_port=ONAPP_SSH_PORT, sshopt=SSH_OPTS, )
        (rc, ou) = run_command(CMD, verbosity, 0)

    # --step_9--#
    # --OnApp: Upload qcow2 image to VHI--#
    logs.info('-------')
    logs.info("-- Upload qcow2 image to VHI --".format(hv_ip=ONAPP_HV_IP))

    CMD = "scp -P{ssh_port} {sshopt} root@{hv_ip}:/tmp/{disk_name}.qcow2 root@{vhi_cp}:/tmp/ 2>/dev/null ".format(
        hv_ip=ONAPP_HV_IP, ssh_port=ONAPP_SSH_PORT, sshopt=SSH_OPTS, vhi_cp=VHI_CP_IP, disk_name=TMPL_file_name)
    (rc, ou) = run_command(CMD, verbosity, 0)

    # --step_10--#
    # --OnApp: Import qcow2 image to VHI- --#
    logs.info('-------')
    logs.info("-- Import qcow2 image from [{hv_ip}] to VHI --".format(hv_ip=ONAPP_HV_IP))

    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'openstack image create --container-format bare --disk-format qcow2 --file /tmp/{disk_name}.qcow2 \"{tmpl_label}\"' ".format(
        ssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhi_cp=VHI_CP_IP, disk_name=TMPL_file_name, tmpl_label=TMPL_label)
    # logs.info(CMD)
    (rc, ou) = run_command(CMD, verbosity, 0)

    # --step_11--#
    # -- rm qcow2 image from ONAPP_HV and from VHI - --#
    logs.info('-------')
    logs.info("-- rm qcow2 image from ONAPP_HV and from VHI --")

    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'rm -rf /tmp/{disk_name}.qcow2 ' ".format(vhi_cp=VHI_CP_IP,
                                                                                             ssh_port=VHI_SSH_PORT,
                                                                                             sshopt=SSH_OPTS,
                                                                                             disk_name=TMPL_file_name)
    # logs.info(CMD)
    (rc, ou) = run_command(CMD, verbosity, 0)

    CMD = "ssh -p{ssh_port} {sshopt} root@{hv_ip} 'rm -rf /tmp/{disk_name}.qcow2 ' ".format(hv_ip=ONAPP_HV_IP,
                                                                                            ssh_port=ONAPP_SSH_PORT,
                                                                                            sshopt=SSH_OPTS,
                                                                                            disk_name=TMPL_file_name)
    # logs.info(CMD)
    (rc, ou) = run_command(CMD, verbosity, 0)


cli.add_command(vm)
