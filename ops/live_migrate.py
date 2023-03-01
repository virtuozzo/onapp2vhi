import json
import re
import xml.etree.ElementTree as KVMxml

import click
from click_default_group import DefaultGroup
from inc.ssh_connector import ssh_run, SSH
from inc.onapp_helpers import (
    get_onapp_vm_flavor,
    get_onapp_vm_disks,
    get_onapp_vm_nics,
    create_new_vhi_vm,
    get_vm_source_properties,
    transfer_firewall_rules_to_sg, get_iface_from_specific_vs, attach_security_group_to_nic_and_enable_spoofing
)
from inc.vhi_helpers import Vhi
from inc.network_hanlder import get_network_configuration
from inc.logger import logs
from inc.helper import Helper
from cfg.config_parser import ONAPP_CREDS, VHI_CREDS, VINFRA_AUTH, ADMIN_AUTH


def vm_live_migrate(vdom: str, vproj: str, idn: str, network: str):
    if not idn:
        logs.info('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False

    VM_IDn = idn
    _network = network if network else VHI_CREDS['network']
    _vhidom = vdom if vdom else VHI_CREDS['vinfra_domain']
    _vhiproj = vproj if vproj else VHI_CREDS['vinfra_project']

    _spaces = Helper.SPACES.value
    live_migration = 'LIVE MIGRATION -- '
    logs.info(f'{_spaces}-- {live_migration}', header=True)

    # -- STEP 1 --
    logs.info(f"{_spaces}{live_migration}STEP #1 -- OnApp: Get source VM properties --", header=True)
    _vm_properties = get_vm_source_properties(vm_idn=VM_IDn)
    _vm_hv_ip = _vm_properties['hv_ip']
    _vm_ip_addr = _vm_properties['vm_ip_addr']
    _hot_migrate = _vm_properties['hot_migrate']
    vhi = Vhi()
    vhi.check_default_project()
    _on_app_flavor = get_onapp_vm_flavor(vm_idn=VM_IDn)
    logs.debug(f'OnApp flavor: {_on_app_flavor}')
    result = vhi.flavor_handler(onapp_flavor=_on_app_flavor)
    if not result:
        logs.warn('Flavor has NOT been created on VHI side, further process does not make sense.')
        return False

    logs.debug(f'VHI flavor: {vhi.flavor_name}')
    _flavour = vhi.flavor_name
    _vhi_image = VHI_CREDS['linux_image']

    if _vm_properties['vm_os'] == 'windows':
        _vhi_image = VHI_CREDS['windows_image']

    if _hot_migrate == 'False':
        logs.error(f"{_spaces}ATTENTION hot_migrate is not allowed for VM")
        return False

    else:
        logs.info("HOT migrate is allowed for VM")

    # -- STEP 2 --
    logs.info(f"{_spaces}{live_migration}STEP #2 -- OnApp: Get VM's NICs' params --", header=True)
    _onapp_nics = get_onapp_vm_nics(idn)

    # -- STEP 3 --
    logs.info(f"{_spaces}{live_migration}STEP #3 -- OnApp: Get VM's disk info --", header=True)
    _onapp_disks = get_onapp_vm_disks(idn)

    # -- STEP 4 --
    logs.info(f"{_spaces}{live_migration}STEP #4 -- OnApp: Check if VM is running on HV --", header=True)
    _hv_ssh = SSH(**{'host': _vm_hv_ip})
    exit_status, output = _hv_ssh.execute(f"virsh list | grep {VM_IDn} 2>/dev/null")
    if not output:
        logs.error("VM IS NOT RUNNING. PLEASE, START VM OR USE ``cold_migrate`` OPTION.")
        return False

    # -- STEP 5 --
    logs.info(f"{_spaces}{live_migration}STEP #5 -- OnApp: Get VM's XML config from OnApp hypervisor --",
              header=True)
    exit_status, output = _hv_ssh.execute(f"virsh dumpxml {VM_IDn} > /tmp/{VM_IDn}.xml && cat /tmp/{VM_IDn}.xml")
    _vm_xml_cfg = output
    if exit_status:
        logs.error(f"Can't find VM running on Hypervisor. {_vm_xml_cfg}\n")
        return False
    vmxml = KVMxml.fromstring(_vm_xml_cfg)
    _xml_ovm_disks = []
    _xml_ovm_macs = []

    for device in vmxml.findall("devices"):
        for disk in device.findall("disk"):
            if disk.attrib['device'] == "disk":
                disk_name = disk.find('target').attrib['dev']
                disk_path = disk.find('source').attrib['dev']
                _xml_ovm_disks.append({'name': disk_name, 'path': disk_path})
        for nic in device.findall("interface"):
            _xml_ovm_macs.append(nic.find('mac').attrib['address'])

    logs.info(f"XML OVM DISKS: {_xml_ovm_disks}")
    logs.info(f"XML OVM MACS: {_xml_ovm_macs}")

    # -- STEP 6 --
    logs.info(f"{_spaces}{live_migration}STEP #6 -- VHI: Create similar VM on VHI side --", header=True)
    vinfra_access = f"{VINFRA_AUTH} --vinfra-domain='{_vhidom}' --vinfra-project='{_vhiproj}'"
    onappvm_pri_ip = _onapp_nics[0]['ips'][0]
    onappvm_pri_mac = _onapp_nics[0]['mac']
    _vhi_ssh = SSH(**{'host': VHI_CREDS['cp_ip'], 'port': VHI_CREDS['cloud_ssh_port']})
    exit_status, output = _vhi_ssh.execute(f"{ADMIN_AUTH} service compute server list --long -f json")
    vhi_vms = json.loads(output)
    _error_msg = ''
    vm_created = False
    for _vm in vhi_vms:
        _vm_id = _vm['id']
        _error_msg = (f"VM with [IP: {onappvm_pri_ip} | MAC: {onappvm_pri_mac}] ALREADY EXISTS on VHI side.\n"
                      f"VM: {VHI_CREDS['url']}/compute/servers/instances/{_vm_id}/")
        if not _vm['networks'] and _vm['name'] == f'vm_{_vm_properties["hostname"].lower()}_{VM_IDn}':
            vm_created = True
            break

        if onappvm_pri_mac == _vm['networks'][0]['mac_addr'] or onappvm_pri_ip in _vm['networks'][0]['ips']:
            vm_created = True
            break

    _vhi_vm_id = ''
    _network = get_network_configuration(virtual_server_identifier=VM_IDn)
    logs.debug(f'NETWORK PARAMS: {_network}', separator=True)
    if not vm_created:
        _vhi_vm_id = create_new_vhi_vm(vhi_ssh=_vhi_ssh,
                                       vinfra_access=vinfra_access,
                                       vm_idn=VM_IDn,
                                       network=_network,
                                       vhi_image=_vhi_image,
                                       onapp_disks=_onapp_disks,
                                       flavour=_flavour,
                                       onapp_nics=_onapp_nics,
                                       hostname=_vm_properties['hostname'])
        if not _vhi_vm_id:
            return False
    else:
        logs.error(_error_msg)
        logs.error("*** Please, remove the target VM on VHI or remove conflicting network interface of it ***\n")
        return False

    # -- Attach Security group to NIC
    # -- Enable Spoofing for NIC
    iface_id = get_iface_from_specific_vs(vm_name=_vhi_vm_id)
    security_group_id = transfer_firewall_rules_to_sg(vm_idn=VM_IDn, vhiproj=_vhiproj)
    attach_security_group_to_nic_and_enable_spoofing(vm_name=_vhi_vm_id, iface=iface_id, sg_id=security_group_id)

    # -- STEP 7 --
    logs.info(f"{_spaces}{live_migration}STEP #7 -- VHI: define VM's hypervisor and disks --", header=True)
    exit_status, output = _vhi_ssh.execute(f"host `vinfra service compute server show {_vhi_vm_id} -f json"
                                           f" | jq -r .host` 2>/dev/null | awk '/ has address /{{print $NF}}'")
    if re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', output):
        _vhi_hv_ip = output.strip("\n")
        logs.info(f"VMs HV IP: {_vhi_hv_ip}")
    else:
        logs.error(f"Destination Appliance network is not configured properly:\nOnApp VM IP [{_vm_ip_addr}]"
                   f" | Output: [{output}]")
        return False

    _vhi_hv_ssh = SSH(**{'host': _vhi_hv_ip})
    exit_status, output = _vhi_hv_ssh.execute(f"{VINFRA_AUTH} service compute server volume list"
                                              f" --server {_vhi_vm_id} -f json | jq -c 2>/dev/null")
    vhivm_disks = json.loads(output)
    _vhi_vm_disks = {str(x['device'].split('/')[2]): str(x['id']) for x in vhivm_disks}
    for disk_lb, disk_id in _vhi_vm_disks.items():
        exit_status, output = _vhi_hv_ssh.execute(
            f"find /mnt/vstorage/vols/datastores/cinder/ -type f -name \"*volume-{disk_id}\" 2>/dev/null"
        )
        _vhi_vm_disks[disk_lb] = output.strip()
    logs.info(f"VHI VM DISKS: {_vhi_vm_disks}")

    # -- STEP 8 --
    logs.info(f"{_spaces}{live_migration}STEP #8 -- VHI: Get VHI VM XML config parameters --", header=True)
    exit_status, output = _vhi_hv_ssh.execute(
        f"virsh dumpxml {_vhi_vm_id} 2>/dev/null > /tmp/{_vhi_vm_id}.xml ; cat /tmp/{_vhi_vm_id}.xml 2>/dev/null"
    )
    _vm_xml_cfg = output
    vhixml = KVMxml.fromstring(_vm_xml_cfg)
    _xml_vvm_disks, _xml_vvm_nics = [], []
    for device in vhixml.findall("devices"):
        for disk in device.findall("disk"):
            if disk.attrib['device'] == "disk":
                _xml_vvm_disks.append(disk.find('source').attrib['file'])

        # FIXED - https://virtuozzo.atlassian.net/browse/SYS-1525
        for nic in device.findall("interface"):
            vvm_mac = nic.find('mac').attrib['address']
            vvm_tap = nic.find('target').attrib['dev']
            _xml_vvm_nics.append({'mac': vvm_mac, 'tap': vvm_tap})
    logs.info(f"XML VVM DISKS: {_xml_vvm_disks}")
    logs.info(f"XML VVM NETWORKS: {_xml_vvm_nics}")

    # -- STEP 9 --
    logs.info(f"{_spaces}{live_migration}STEP #9 -- VHI: Process and upload VM's XML config --", header=True)
    for device in vmxml.findall("devices"):
        for disk in device.findall("disk"):
            if disk.attrib['device'] == "disk":
                disk.attrib['type'] = 'file'
                disk_label = disk.find('target').attrib['dev']
                for driver in disk.findall('driver'):
                    driver.attrib['type'] = 'qcow2'
                    driver.attrib['io'] = 'native'
                    driver.attrib['discard'] = 'unmap'
                for source in disk.findall('source'):
                    # We faced with an issue with different disks
                    # vda, vdb == sda, sdb
                    try:
                        source.attrib['file'] = _vhi_vm_disks[disk_label]
                    except KeyError:
                        disk_label = 's' + disk_label[1:]
                        source.attrib['file'] = _vhi_vm_disks[disk_label]
                    del source.attrib['dev']
            elif disk.attrib['device'] == "cdrom":
                cdrom_file = disk.find('source').attrib['file']
                disk.find('source').attrib['file'] = '/tmp/grub2.img'
                _hv_ssh.execute(f"scp -P {ONAPP_CREDS['hv_ssh_port']} {Helper.SCP_OPTS.value}"
                                f" {cdrom_file} root@{_vhi_hv_ip}:/tmp/ 2>/dev/null ")
                _vhi_hv_ssh.execute(f'ls /tmp/grub2* 2>/dev/null')
        nic_num = 0
        # FIXED - https://virtuozzo.atlassian.net/browse/SYS-1525
        for nic in device.findall("interface"):
            nic.attrib['type'] = 'ethernet'
            if not nic_num:
                for sources in nic.findall('source'):
                    nic.remove(sources)
                for tgt in nic.findall('target'):
                    tgt.attrib['dev'] = _xml_vvm_nics[0]['tap']
            elif nic_num > 0:
                device.remove(nic)
            nic_num += 1
    xmltree = KVMxml.ElementTree(vmxml)
    xmltree.write(f"/tmp/{VM_IDn}.xml")

    # -- STEP 10 --
    logs.info(f"{_spaces}{live_migration}STEP #10 -- VHI: Upload OnApp2VHI VM migration XML to OnApp HV --",
              header=True)
    ssh_run(
        command=f"scp -P{ONAPP_CREDS['hv_ssh_port']} {Helper.SCP_OPTS.value} /tmp/{VM_IDn}.xml root@{_vm_hv_ip}:/tmp/ "
                f"2>/dev/null ; ssh -p{ONAPP_CREDS['hv_ssh_port']} {Helper.SSH_OPTS.value} root@{_vm_hv_ip} "
                f"'ls /tmp/{VM_IDn}.xml' 2>/dev/null"
    )

    # -- STEP 11 --
    logs.info(f"{_spaces}{live_migration}STEP #11 -- VHI: Run OnApp2VHI VM migration from OnApp to VHI hypervisor --",
              header=True)
    _onappvm_disks = ",".join([str(dsk['name']) for dsk in _xml_ovm_disks])
    exit_status, output = _hv_ssh.execute(
        f"virsh migrate --live --auto-converge --unsafe --copy-storage-all --migrate-disks {_onappvm_disks}"
        f" --xml /tmp/{VM_IDn}.xml --verbose {VM_IDn} qemu+ssh://{_vhi_hv_ip}:"
        f"{VHI_CREDS['hv_ssh_port']}/system?no_verify=1 tcp:{_vhi_hv_ip}", real_data=True
    )
    if exit_status:
        return False

    # -- STEP 12 --
    logs.info(f"{_spaces}{live_migration}STEP #12 -- VHI: Stop just migrated OnApp VM on VHI hypervisor --",
              header=True)
    # ToDo add validation to check whether VM is created
    #  "virsh info {VM_IDn}"
    _vhi_hv_ssh.execute(f"virsh destroy {VM_IDn} 2>/dev/null")

    # -- STEP 13 --
    logs.info(f"{_spaces}{live_migration}STEP #13 -- VHI: Start original pre-created VHI VM on VHI hypervisor --",
              header=True)
    _vhi_hv_ssh.execute(f"{vinfra_access} service compute server start {_vhi_vm_id}"
                        f" -f json | jq -c -r \"[ .id , .power_state ]\" 2>/dev/null")

    logs.info(
        f"The virtual server live migration has completed successfully:"
        f" {VHI_CREDS.url}/compute/servers/instances/{_vhi_vm_id}"
    )
    return True


@click.group(cls=DefaultGroup, default='livemigrate', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--vdom', '--vhi-domain', default='', help="VHI Domain.")
@click.option('--vproj', '--vhi-project', default='', help="VHI Project.")
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
@click.option('--network', default='', help="Set network id")
def livemigrate(vdom='', vproj='', idn='', network=''):
    vm_live_migrate(vdom=vdom,
                    vproj=vproj,
                    idn=idn,
                    network=network)


cli.add_command(livemigrate)
