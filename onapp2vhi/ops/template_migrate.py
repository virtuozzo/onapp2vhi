import json
import click
import time
import xml.etree.ElementTree as KVMxml

from click_default_group import DefaultGroup
from inc.ssh_connector import ssh_run
from inc.logger import logs
from inc.helper import Helper
from cfg.config_parser import ONAPP_CREDS, VHI_CREDS


@click.group(cls=DefaultGroup, default='vm', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn', '--tmpl', '--label', '--template-label', default='', help="OnApp template label.")
# click.argument('name',default='') - not used
def vm(idn='', vhip=''):
    if not idn:
        logs.info('You need to pass OnApp template label value through --template-label=? parameter ')
        exit(17)
    TMPL_LABEL = idn

    # --step_1--#
    # --OnApp: get source template parameters--#
    _template_url = f'{ONAPP_CREDS["url"]}/templates.json'
    cmd = (f"curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json'"
           f" -u {ONAPP_CREDS['email']}:{ONAPP_CREDS['api_key']} {_template_url} |"
           f" jq -c --arg template_label \"{TMPL_LABEL}\" '.[] | select(.image_template.label==$template_label) | "
           f"[ .image_template.label, .image_template.id, .image_template.min_disk_size, .image_template.file_name ] '")
    (rc, ou) = ssh_run(command=cmd, comment=" -- OnApp: get source template parameters -- ")
    TMPL_label = str(json.loads(ou)[0]).encode('ascii')
    # TMPL_id = int(json.loads(ou)[1])
    TMPL_disk_size = int(json.loads(ou)[2])
    TMPL_file_name = str(json.loads(ou)[3]).encode('ascii')

    # --step_2--#
    # --OnApp: Create QCOW disk at OnApp hypervisor --#
    _disk_cmd = (f"ssh -p{ONAPP_CREDS['cp_ssh_port']} {Helper.SSH_OPTS.value}"
                 f" root@{ONAPP_CREDS['onapp_hv_ip']} 'qemu-img create -o cluster_size=1048576,lazy_refcounts=on"
                 f" -f qcow2 /tmp/{TMPL_file_name}.qcow2 {TMPL_disk_size}G' ")
    ssh_run(command=_disk_cmd, comment=" -- Create QCOW disk at OnApp hypervisor -- ")

    # --step_3--#
    # --OnApp: Create QCOW disk at OnApp hypervisor --#
    cmd = f"""ssh -p{ONAPP_CREDS['cp_ssh_port']} {Helper.SSH_OPTS.value} root@{ONAPP_CREDS['onapp_hv_ip']} "
            guestfish <<EOF
            add /tmp/{TMPL_file_name}.qcow2
            run
            part-disk /dev/sda mbr
            mke2fs /dev/sda1 fstype:ext4
            mount /dev/sda1 /
            copy-in /onapp/backups/templates/{TMPL_file_name} /
            rename /{TMPL_file_name} /tmplroot
            umount /
            exit
            EOF" """
    ssh_run(command=cmd, comment="-- Deploy QCOW disk from template at OnApp hypervisor --")
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
    logs.info('', separator=True)
    #    logs.info("-- OnApp: Copy scripts and configs to HV [{hv_ip}] --".format(hv_ip=ONAPP_CREDS['onapp_hv_ip']))
    _copy_cmd = (f"scp -P{ONAPP_CREDS['cp_ssh_port']} {Helper.SSH_OPTS.value} -r scripts"
                 f"  root@{ONAPP_CREDS['onapp_hv_ip']}:/onapp/tools/")
    ssh_run(command=_copy_cmd)

    # --step_5--#
    # --OnApp: Start VM is recovery mode --#
    _comm = f"-- OnApp: Start VM is recovery mode on HV [{ONAPP_CREDS['onapp_hv_ip']}] --"
    _start_cmd = (f"ssh -p{ONAPP_CREDS['cp_ssh_port']} {Helper.SSH_OPTS.value} root@{ONAPP_CREDS['onapp_hv_ip']}"
                  f" 'virsh create /onapp/tools/scripts/recovery-tmpl.xml.mg'")
    ssh_run(command=_start_cmd, comment=_comm)

    # --step_8--#
    # --OnApp: Install grub --#
    logs.info(f"-- OnApp: Install grub in recovery VM on HV [{ONAPP_CREDS['onapp_hv_ip']}] --", separator=True)
    _install_grub = (f"ssh -t -t -p{ONAPP_CREDS['cp_ssh_port']} {Helper.SSH_OPTS.value} "
                     f"root@{ONAPP_CREDS['onapp_hv_ip']}  sh -c -l '/onapp/tools/scripts/tmpl_grub_install.sh'")
    ssh_run(command=_install_grub)

    # --step_8--#
    # --OnApp: Shutdown VM  --#
    logs.info(f"-- OnApp: shutdown recovery VM on HV [{ONAPP_CREDS['onapp_hv_ip']}] --", separator=True)
    _shut_down_vm = (f"ssh -p{ONAPP_CREDS['cp_ssh_port']} {Helper.SSH_OPTS.value} "
                     f"root@{ONAPP_CREDS['onapp_hv_ip']} 'virsh shutdown identifier'")
    (rc, ou) = ssh_run(command=_shut_down_vm)
    while rc != 1:
        time.sleep(30)
        _cmd = (f"ssh -p{ONAPP_CREDS['cp_ssh_port']} {Helper.SSH_OPTS.value}"
                f" root@{ONAPP_CREDS['onapp_hv_ip']} 'virsh dominfo identifier | grep -w State'")
        (rc, ou) = ssh_run(command=_cmd)

    # --step_9--#
    # --OnApp: Upload qcow2 image to VHI--#
    logs.info(f"-- Upload qcow2 image to VHI {ONAPP_CREDS['onapp_hv_ip']} --", separator=True)
    _cmd = (f"scp -P{ONAPP_CREDS['cp_ssh_port']} {Helper.SSH_OPTS.value}"
            f" root@{ONAPP_CREDS['onapp_hv_ip']}:/tmp/{TMPL_file_name}.qcow2"
            f" root@{VHI_CREDS['cp_ip']}:/tmp/ 2>/dev/null ")
    ssh_run(command=_cmd)

    # --step_10--#
    # --OnApp: Import qcow2 image to VHI- --#
    logs.info(f"-- Import qcow2 image from [{ONAPP_CREDS['onapp_hv_ip']}] to VHI --", separator=True)
    _cmd = (f"ssh -p{VHI_CREDS['cloud_ssh_port']} {Helper.SSH_OPTS.value} root@{VHI_CREDS['cp_ip']}"
            f" 'openstack image create --container-format bare --disk-format qcow2 --file"
            f" /tmp/{TMPL_file_name}.qcow2 \"{TMPL_label}\"' ")
    ssh_run(command=_cmd)

    # --step_11--#
    # -- rm qcow2 image from ONAPP_HV and from VHI - --#
    logs.info("-- rm qcow2 image from ONAPP_HV and from VHI --", separator=True)
    _cmd = (f"ssh -p{VHI_CREDS['cloud_ssh_port']} {Helper.SSH_OPTS.value}"
            f" root@{VHI_CREDS['cp_ip']} 'rm -rf /tmp/{TMPL_file_name}.qcow2 ' ")
    ssh_run(command=_cmd)
    _cmd = (f"ssh -p{ONAPP_CREDS['cp_ssh_port']} {Helper.SSH_OPTS.value} "
            f"root@{ONAPP_CREDS['onapp_hv_ip']} 'rm -rf /tmp/{TMPL_file_name}.qcow2 ' ")
    # logs.info(CMD)
    ssh_run(command=_cmd)


cli.add_command(vm)
