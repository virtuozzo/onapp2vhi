import json
import re
import xml.etree.ElementTree as KVMxml

from onapp2vhi.inc.ssh_connector import ssh_run, SSH
from onapp2vhi.inc.onapp_helpers import (
    get_onapp_vm_flavor,
    get_onapp_vm_disks,
    get_onapp_vm_nics,
    create_new_vhi_vm,
    transfer_firewall_rules_to_sg,
    get_iface_from_specific_vs,
    attach_security_group_to_nic_and_enable_spoofing,
    deactivate_disk,
    suspend_vm,
    find_correct_disk_key,
    check_sg_exists_in_project
)
from onapp2vhi.inc.vhi_helpers import (
    get_vhi_hv_ip
)
from onapp2vhi.inc.utils import exit_status_code_handler
from onapp2vhi.inc.network_handler import get_network_configuration
from onapp2vhi.utilities.logs.logger import OnAppVHILogger
from onapp2vhi.inc.helper import Helper
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.inc.vinfra_wrapper import VinfraCommand, VinfraError
from time import time, sleep

VHI_VM_CREATION_TIMEOUT = 300

logs = OnAppVHILogger()


def vm_live_migrate(cfg: OnApp2VHIConfig, vdom: str, vproj: str, idn: str, vm_properties: dict, vhi_obj, placement=''):
    if not idn:
        logs.info('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False

    vm_idn = idn
    _vhidom = vdom if vdom else cfg.vhi_conf['vinfra_domain']
    _vhiproj = vproj if vproj else cfg.vhi_conf['vinfra_project']
    _migration_network_id = cfg.vhi_conf['migration_network_id']

    _spaces = Helper.SPACES.value
    live_migration = 'LIVE MIGRATION -- '
    logs.info(f'{_spaces}-- {live_migration}', header=True)

    # -- STEP 1 --
    logs.info(f"{_spaces}{live_migration}STEP #1 -- OnApp: Get source VM properties --", header=True)
    _vm_properties = vm_properties
    _vm_hv_ip = _vm_properties['hv_ip']
    _vm_ip_addr = _vm_properties['vm_ip_addr']
    _hot_migrate = _vm_properties['hot_migrate']
    vhi = vhi_obj
    _on_app_flavor = get_onapp_vm_flavor(cfg, vm_idn=vm_idn)
    logs.debug(f'OnApp flavor: {_on_app_flavor}')
    result = vhi.flavor_handler(onapp_flavor=_on_app_flavor, placement=placement)
    if not result:
        logs.warn('Flavor has NOT been created on VHI side, further process does not make sense.')
        return False

    logs.debug(f'VHI flavor: {vhi.flavor_name}')
    _flavour = vhi.flavor_name
    _vhi_image = cfg.vhi_conf['linux_image']

    if _vm_properties['vm_os'] == 'windows':
        _vhi_image = cfg.vhi_conf['windows_image']

    if _hot_migrate == 'False':
        logs.error(f"{_spaces}ATTENTION hot_migrate is not allowed for VM")
        return False

    logs.info("HOT migrate is allowed for VM")

    # -- STEP 2 --
    logs.info(f"{_spaces}{live_migration}STEP #2 -- OnApp: Get VM's NICs' params --", header=True)
    _onapp_nics = get_onapp_vm_nics(cfg, idn)

    # -- STEP 3 --
    logs.info(f"{_spaces}{live_migration}STEP #3 -- OnApp: Get VM's disk info --", header=True)
    _onapp_disks = get_onapp_vm_disks(cfg, idn)

    # -- STEP 4 --
    logs.info(f"{_spaces}{live_migration}STEP #4 -- OnApp: Check if VM is running on HV --", header=True)
    _hv_ssh = SSH(**{'host': _vm_hv_ip, 'ssh_key': cfg.ssh_key})
    exit_status, output = _hv_ssh.execute(f"virsh list | grep {vm_idn} 2>/dev/null")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message="VM IS NOT RUNNING. PLEASE, START VM OR USE ``cold_migrate`` OPTION."
    ):
        return False

    # -- STEP 5 --
    logs.info(f"{_spaces}{live_migration}STEP #5 -- OnApp: Get VM's XML config from OnApp hypervisor --",
              header=True)
    exit_status, output = _hv_ssh.execute(
        f"virsh dumpxml {vm_idn} --migratable > /tmp/{vm_idn}.xml && cat /tmp/{vm_idn}.xml"
    )
    _vm_xml_cfg = output
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[live_migrate.py | STEP 5] Can't find VM running on Hypervisor. {_vm_xml_cfg}. Output\n\t{output}"
    ):
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
    vinfra_access = f"{cfg.ADMIN_AUTH} --vinfra-domain='{_vhidom}' --vinfra-project='{_vhiproj}'"
    if cfg.vhi_conf['vinfra_domain'] != 'Default':
        vinfra_access = f"{cfg.DOMAIN_AUTH}  --vinfra-domain='{_vhidom}' --vinfra-project='{_vhiproj}'"
    onappvm_pri_ip = _onapp_nics[0]['ips'][0]
    onappvm_pri_mac = _onapp_nics[0]['mac']

    vinfra_command = VinfraCommand(cfg, vinfra_access=cfg.ADMIN_AUTH, cp_ip=True)
    try:
        output = vinfra_command.execute("service compute server list --long -f json")
    except VinfraError as e:
        exit_status_code_handler(
            exit_code=e.exit_code,
            message=f"[live_migrate.py | STEP 6] {e}")
        return False

    vhi_vms = json.loads(output)
    _error_msg = ''
    vm_created = False
    for _vm in vhi_vms:
        _vm_id = _vm['id']
        _error_msg = (f"VM with [IP: {onappvm_pri_ip} | MAC: {onappvm_pri_mac}] ALREADY EXISTS on VHI side.\n"
                      f"VM: {cfg.vhi_conf['url']}/compute/servers/instances/{_vm_id}/")

        if not _vm['networks'] and _vm['name'] == f'vm_{_vm_properties["hostname"].lower()}_{vm_idn}':
            vm_created = True
            break

        if not _vm['networks'] and _vm['status'] == "ERROR":
            logs.error(f"VM with {_vm['name']} name is in \"error\" status, aborting migration. Please remove the vm and try again.\n"
                       f"VM: {cfg.vhi_conf['url']}/compute/servers/instances/{_vm_id}/")
            return False

        if not _vm['networks'] and _vm['status'] == "BUILD":
            #Rare situation where vm's network is still building and there is another migration instance running
            logs.error(f"VM with {_vm['name']} name is still in \"build\" status, aborting migration. Please try again.\n"
                       f"VM: {cfg.vhi_conf['url']}/compute/servers/instances/{_vm_id}/")
            return False

        if not _vm['networks']:
            logs.info(f"VM with {_vm['name']} name has no networks\n"
                      f"VM: {cfg.vhi_conf['url']}/compute/servers/instances/{_vm_id}/")
            continue

        if onappvm_pri_mac == _vm['networks'][0]['mac_addr'] or onappvm_pri_ip in _vm['networks'][0]['ips']:
            vm_created = True
            break

    _vhi_vm_id = ''
    _network = get_network_configuration(cfg, virtual_server_identifier=vm_idn, vinfra_project=_vhiproj)
    if not _network:
        logs.error("The network issue is hit. Could you please check logs.")
        return False

    logs.debug(f'NETWORK PARAMS: {_network}', separator=True)
    _vhi_ssh = SSH(**{'host': cfg.vhi_conf['cp_ip'],
                      'port': cfg.vhi_conf['cloud_ssh_port'],
                      'ssh_key': cfg.ssh_key})
    if not vm_created:
        _vhi_vm_id = create_new_vhi_vm(cfg,
                                       vhi_ssh=_vhi_ssh,
                                       vinfra_access=vinfra_access,
                                       vm_idn=vm_idn,
                                       network=_network,
                                       vhi_image=_vhi_image,
                                       onapp_disks=_onapp_disks,
                                       flavour=_flavour,
                                       onapp_nics=_onapp_nics,
                                       hostname=_vm_properties['hostname'],
                                       domain=_vm_properties['domain'],
                                       vhi_storage_policy=_vm_properties['storage_policy'])
        if not _vhi_vm_id:
            return False

    else:
        logs.error(_error_msg)
        logs.error("*** Please, remove the target VM on VHI or remove conflicting network interface of it ***\n")
        return False

    # -- Attach Security group to NIC
    # -- Enable Spoofing for NIC
    iface_ids = get_iface_from_specific_vs(cfg, vm_name=_vhi_vm_id)

    # Set Up primary SG
    _primary_iface_id = iface_ids.pop(0)
    security_group_id = transfer_firewall_rules_to_sg(cfg, vm_idn=vm_idn, vhiproj=_vhiproj)
    attach_security_group_to_nic_and_enable_spoofing(cfg,
                                                     vm_name=_vhi_vm_id,
                                                     iface=_primary_iface_id['id'],
                                                     sg_id=security_group_id)

    # Set Up secondary SG
    _secondary_sg_id = cfg.vhi_conf['vhi_secondary_security_group']

    if _secondary_sg_id:
        if check_sg_exists_in_project(cfg, vhiproj=_vhiproj, sg_id=_secondary_sg_id):
            for iface_id in iface_ids:
                attach_security_group_to_nic_and_enable_spoofing(cfg,
                                                                 vm_name=_vhi_vm_id,
                                                                 iface=iface_id['id'],
                                                                 sg_id=_secondary_sg_id)
        else:
            logs.warn(f"*** Security Group with ID[{_secondary_sg_id}] does NOT exists in Project [{_vhiproj}] ***")

    # -- STEP 7 --
    logs.info(f"{_spaces}{live_migration}STEP #7 -- VHI: define VM's hypervisor and disks --", header=True)
    _vhi_hv_ip = ""
    if not _migration_network_id:
        logs.warn(msg='Migration Network ID [migration_network_id] is NOT set in config properties `cfg/config.cfg`.'
                      ' Using default VHI management IP')
        exit_status, output = _vhi_ssh.execute(f"host `{cfg.ADMIN_AUTH} service compute server show {_vhi_vm_id} -f json"
                                               f" | jq -r .host` 2>/dev/null | awk '/ has address /{{print $NF}}'")
        if re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', output):
            _vhi_hv_ip = output.strip("\n")
            logs.info(f"VMs HV IP: {_vhi_hv_ip}")
    else:
        _vhi_hv_ip = get_vhi_hv_ip(cfg, vhi_vm_id=_vhi_vm_id, vhi_ssh=_vhi_ssh)
        if not _vhi_hv_ip:
            return False

    vinfra_command = VinfraCommand(cfg, vinfra_access=vinfra_access, host=_vhi_hv_ip)
    try:
        output = vinfra_command.execute("service compute server volume list"
                                        f" --server {_vhi_vm_id} -f json")
    except VinfraError as e:
        exit_status_code_handler(
            exit_code=e.exit_code,
            message=f"[live_migrate.py | STEP 7] {e}")
        return False

    vhivm_disks = json.loads(output)
    _vhi_vm_disks = {str(x['device'].split('/')[2]): str(x['id']) for x in vhivm_disks}

    _vhi_hv_ssh = SSH(**{'host': _vhi_hv_ip, 'ssh_key': cfg.ssh_key})
    for disk_lb, disk_id in _vhi_vm_disks.items():
        exit_status, output = _vhi_hv_ssh.execute(
            f"find /mnt/vstorage/vols/datastores/cinder/ -type f -name \"*volume-{disk_id}\" 2>/dev/null"
        )
        if not exit_status_code_handler(exit_code=exit_status,
                                        message='[live_migrate.py | STEP 7] VHI VM disks NOT found.'):
            return False

        _vhi_vm_disks[disk_lb] = output.strip()
    logs.info(f"VHI VM DISKS: {_vhi_vm_disks}")

    # -- STEP 8 --
    logs.info(f"{_spaces}{live_migration}STEP #8 -- VHI: Get VHI VM XML config parameters --", header=True)
    exit_status, output = _vhi_hv_ssh.execute(
        f"virsh dumpxml {_vhi_vm_id} 2>/dev/null > /tmp/{_vhi_vm_id}.xml ; cat /tmp/{_vhi_vm_id}.xml 2>/dev/null"
    )
    if not exit_status_code_handler(exit_code=exit_status,
                                    message='[live_migrate.py | STEP 8] VM dumpxml failed.'):
        return False

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
                    driver.attrib['detect_zeroes'] = 'unmap'
                for source in disk.findall('source'):
                    # We faced with an issue with different disks
                    # vda, vdb == sda, sdb
                    disk_label = find_correct_disk_key(on_app_disks=_xml_ovm_disks,
                                                       target=disk_label)
                    try:
                        source.attrib['file'] = _vhi_vm_disks[disk_label]
                    except KeyError:
                        disk_label = 's' + disk_label[1:]
                        source.attrib['file'] = _vhi_vm_disks[disk_label]
                    del source.attrib['dev']
            elif disk.attrib['device'] == "cdrom":
                cdrom_file = disk.find('source').attrib['file']
                disk.find('source').attrib['file'] = '/tmp/grub2.img'
                _hv_ssh.execute(f"scp -P {cfg.onapp_conf['hv_ssh_port']} {Helper.SCP_OPTS.value}"
                                f" {cdrom_file} root@{_vhi_hv_ip}:/tmp/ 2>/dev/null ")
                _vhi_hv_ssh.execute('ls /tmp/grub2* 2>/dev/null')
        nic_num = 0
        # FIXED - https://virtuozzo.atlassian.net/browse/SYS-1525
        for nic in device.findall("interface"):
            nic.attrib['type'] = 'ethernet'
            if not nic_num:
                for sources in nic.findall('source'):
                    nic.remove(sources)
                for tgt in nic.findall('target'):
                    tgt.attrib['dev'] = _xml_vvm_nics[0]['tap']
            nic_num += 1
    xmltree = KVMxml.ElementTree(vmxml)
    xmltree.write(f"/tmp/{vm_idn}.xml")

    # -- STEP 10 --
    logs.info(f"{_spaces}{live_migration}STEP #10 -- VHI: Upload OnApp2VHI VM migration XML to OnApp HV --",
              header=True)
    [exit_code, _output] = ssh_run(
        command=f"scp -P{cfg.onapp_conf['hv_ssh_port']} {Helper.SCP_OPTS.value} /tmp/{vm_idn}.xml root@{_vm_hv_ip}:/tmp/ "
                f"2>/dev/null ; ssh -p{cfg.onapp_conf['hv_ssh_port']} {Helper.SSH_OPTS.value} root@{_vm_hv_ip} "
                f"'ls /tmp/{vm_idn}.xml' 2>/dev/null"
    )
    if not exit_status_code_handler(
            exit_code=exit_code,
            message='[live_migrate.py | STEP 10] VM DUMPXML copy process from VHI to OnApp failed.'
    ):
        return False

    # -- STEP 11 --
    logs.info(f"{_spaces}{live_migration}STEP #11 -- VHI: Run OnApp2VHI VM migration from OnApp to VHI hypervisor --",
              header=True)
    _onappvm_disks = ",".join([str(dsk['name']) for dsk in _xml_ovm_disks])
    exit_status, output = _hv_ssh.execute(
        f"virsh migrate --live --auto-converge --unsafe --copy-storage-all --migrate-disks {_onappvm_disks}"
        f" --xml /tmp/{vm_idn}.xml --verbose {vm_idn} qemu+ssh://{_vhi_hv_ip}:"
        f"{cfg.vhi_conf['hv_ssh_port']}/system?no_verify=1 tcp:{_vhi_hv_ip}", real_data=True
    )
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f'[live_migrate.py | STEP 11] VM migration process from OnApp to VHI failed. Output\n\t{output}'
    ):
        return False
    else:
        vm_created = False
        pattern = re.compile(r'^State:\s*(\w+)$', re.MULTILINE)
        deadline = time() + VHI_VM_CREATION_TIMEOUT

        while not vm_created and time() < deadline:
            exit_status, output = _vhi_hv_ssh.execute(f'virsh dominfo {vm_idn}')
            if not exit_status_code_handler(exit_code=exit_status,
                                            message='Failed to query VHI vm info.\n\t\{output}'):
                continue
            result = pattern.findall(output)
            if result:
                if result[0] == 'running':
                    vm_created = True
            else:
                sleep(5)

        if not vm_created:
            exit_status_code_handler(exit_code=1, message='VHI vm creation timeout.')
            return False

    # -- STEP 12 --
    logs.info(f"{_spaces}{live_migration}STEP #12 -- VHI: Stop just migrated OnApp VM on VHI hypervisor --",
              header=True)
    exit_status, output = _vhi_hv_ssh.execute(f"virsh shutdown {vm_idn} 2>/dev/null")
    if not exit_status_code_handler(exit_code=exit_status,
                                    message='[live_migrate.py | STEP 12] VM "virsh shutdown" on VHI node failed.'):
        return False

    # -- STEP 13 --
    logs.info(f"{_spaces}{live_migration}STEP #13 -- VHI: Deactivate VM disks at OnApp hypervisor --",
              header=True)
    for ovm_dsk in _onapp_disks:
        _deactivation_props = {'disk_idn': ovm_dsk['disk_idn'],
                               'datastore_type': ovm_dsk['datastore_type'],
                               'path': ovm_dsk['path']}
        deactivate_result = deactivate_disk(cfg, vm_idn='', vm_ohv_ip=_vm_hv_ip, **_deactivation_props)
        if not deactivate_result:
            return False

    # -- STEP 14 --
    logs.info(f"{_spaces}{live_migration}STEP #14 -- VHI: Start original pre-created VHI VM on VHI hypervisor --",
              header=True)
    exit_status, output = _vhi_hv_ssh.execute(f"{vinfra_access} service compute server start {_vhi_vm_id}"
                                              f" -f json | jq -c -r \"[ .id , .power_state ]\" 2>/dev/null")
    if not exit_status_code_handler(exit_code=exit_status,
                                    message=f'[live_migrate.py | STEP 13] {vinfra_access}'
                                            f' service compute server start {_vhi_vm_id} on VHI node failed.'):
        return False

    # -- STEP 15 --
    logs.info(f"{_spaces}{live_migration}STEP #15 -- OnApp: Suspend VM [{vm_idn} | {_vm_ip_addr}] --", header=True)
    result = suspend_vm(cfg, vm_id=vm_idn)
    if not result:
        logs.warn(msg=f'{_spaces} -- VM [{vm_idn} | {_vm_ip_addr}] has NOT been suspended.')
    logs.info(f"The virtual server ``LIVE MIGRATION`` has completed successfully:"
              f" {cfg.vhi_conf['url']}/compute/servers/instances/{_vhi_vm_id}")
    return True
