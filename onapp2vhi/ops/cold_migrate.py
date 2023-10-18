import json
import re
import xml.etree.ElementTree as KVMxml

from onapp2vhi.inc.onapp_helpers import (
    activate_disk,
    deactivate_disk,
    attach_security_group_to_nic_and_enable_spoofing,
    transfer_firewall_rules_to_sg,
    get_iface_from_specific_vs,
    create_new_vhi_vm,
    get_onapp_vm_disks,
    get_onapp_vm_nics,
    get_onapp_vm_flavor,
    suspend_vm,
    check_sg_exists_in_project,
)
from onapp2vhi.inc.vhi_helpers import (
    get_vhi_hv_ip
)
from onapp2vhi.inc.helper import Helper
from onapp2vhi.inc.network_handler import get_network_configuration
from onapp2vhi.utilities.logs.logger import OnAppVHILogger
from onapp2vhi.inc.utils import exit_status_code_handler
from onapp2vhi.inc.ssh_connector import SSH
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.inc.vinfra_wrapper import VinfraCommand, VinfraError

logs = OnAppVHILogger()


def vm_cold_migrate(cfg: OnApp2VHIConfig,
                    vdom: str,
                    vproj: str,
                    idn: str,
                    vm_properties: dict,
                    vhi_obj,
                    placement='',
                    cpu_hotplug=False):
    # ToDo
    #  verify IP address before running script
    if not idn:
        logs.info('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False
    vm_idn = idn

    _vhidom = vdom if vdom else cfg.vhi_conf['vinfra_domain']
    _vhiproj = vproj if vproj else cfg.vhi_conf['vinfra_project']
    _migration_network_id = cfg.vhi_conf['migration_network_id']

    _spaces = Helper.SPACES.value
    _cm_msg = 'COLD MIGRATION -- '
    logs.info(f'{_spaces}-- {_cm_msg}', header=True)

    # -- STEP 1 --
    logs.info(f"{_spaces}{_cm_msg}STEP #1 -- OnApp: Get source VM properties --", header=True)
    _vm_properties = vm_properties
    _vm_hv_ip = _vm_properties['hv_ip']
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

    # -- STEP 2 --
    logs.info(f"{_spaces}{_cm_msg}STEP #2 -- OnApp: Get VM's NICs' params --", header=True)
    _onapp_nics = get_onapp_vm_nics(cfg, idn)

    # -- STEP 3 --
    logs.info(f"{_spaces}{_cm_msg}STEP #3 -- OnApp: get VM's disk info --", header=True)
    _onapp_disks = get_onapp_vm_disks(cfg, idn)

    # -- STEP 4 --
    logs.info(f"{_spaces}{_cm_msg}STEP #4 -- OnApp: check if VM [{vm_idn}] is running on HV [{_vm_hv_ip}] --",
              header=True)
    _hv_ssh = SSH(**{'host': _vm_hv_ip, 'ssh_key': cfg.ssh_key})
    exit_status, output = _hv_ssh.execute(f"virsh list | grep {vm_idn}")
    if output:
        logs.warn("VM IS RUNNING.\n PLEASE, STOP THE VM BEFORE ITS OFFLINE MIGRATION.")
        return False

    # -- STEP 5 --
    logs.info(f"{_spaces}{_cm_msg}STEP #5 -- VHI: create similar to OnApp VM [{vm_idn}] on VHI side --",
              separator=True)
    onappvm_pri_ip = _onapp_nics[0]['ips'][0]
    onappvm_pri_mac = _onapp_nics[0]['mac']

    # Here we generate vinfra access to create VM
    vinfra_access = f"{cfg.ADMIN_AUTH} --vinfra-domain='{_vhidom}' --vinfra-project='{_vhiproj}'"
    if cfg.vhi_conf['vinfra_domain'] != 'Default':
        vinfra_access = f"{cfg.DOMAIN_AUTH}  --vinfra-domain='{_vhidom}' --vinfra-project='{_vhiproj}'"
    _vhi_ssh = SSH(**{'host': cfg.vhi_conf['cp_ip'], 'port': cfg.vhi_conf['cloud_ssh_port'], 'ssh_key': cfg.ssh_key})

    vinfra_command = VinfraCommand(cfg, vinfra_access=cfg.ADMIN_AUTH, cp_ip=True)
    try:
        output = vinfra_command.execute("service compute server list --long -f json")
    except VinfraError as e:
        exit_status_code_handler(
            exit_code=e.exit_code,
            message=f"[cold_migrate.py | STEP 5] {e}")
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
                                       vhi_storage_policy=_vm_properties['storage_policy'],
                                       cpu_hotplug=cpu_hotplug)
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

    # -- STEP 6 --
    logs.info(f"{_spaces}{_cm_msg}STEP #6 -- VHI: define VHI VM's hypervisor and disks --", header=True)
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
            message=f"[cold_migrate.py | STEP 6] {e}")
        return False

    vhivm_disks = json.loads(output)
    _vhi_vm_disks = {str(x['device'].split('/')[2]): str(x['id']) for x in vhivm_disks}
    _vhi_hv_ssh = SSH(**{'host': _vhi_hv_ip, 'ssh_key': cfg.ssh_key})
    for disk_lb, disk_id in _vhi_vm_disks.items():
        exit_status, output = _vhi_hv_ssh.execute(
            f"find /mnt/vstorage/vols/datastores/cinder/ -type f -name \"*volume-{disk_id}\" 2>/dev/null"
        )
        _vhi_vm_disks[disk_lb] = output.strip()
    logs.info(f"VHI VM DISKS: {_vhi_vm_disks}")

    # -- STEP 7 --
    logs.info(f"{_spaces}{_cm_msg}STEP #7 -- VHI: get VHI VM XML config parameters --", header=True)
    exit_status, output = _vhi_hv_ssh.execute(
        f"virsh dumpxml {_vhi_vm_id} 2>/dev/null > /tmp/{_vhi_vm_id}.xml ; cat /tmp/{_vhi_vm_id}.xml 2>/dev/null"
    )
    if not exit_status_code_handler(exit_code=exit_status, message='[cold_migrate.py | STEP 7] VM dumpxml failed.'):
        return False

    _vm_xml_cfg = output
    vhixml = KVMxml.fromstring(_vm_xml_cfg)
    _xml_vvm_disks = []
    for device in vhixml.findall("devices"):
        for disk in device.findall("disk"):
            if disk.attrib['device'] == "disk":
                _xml_vvm_disks.append(disk.find('source').attrib['file'])

    logs.info(f"XML VVM DISKS: {_xml_vvm_disks}")

    # -- STEP 8 --
    logs.info(f"{_spaces}{_cm_msg}STEP #8 -- Run O2V offline VM's disks migration from OnApp to VHI hypervisor --",
              header=True)
    if Helper.IMG_SPARSING.value:
        sparse_opt = '-S 1M'
    else:
        sparse_opt = ''

    dsk_num = 0
    for ovm_dsk in _onapp_disks:
        store_idn = ovm_dsk['datastore_idn']
        disk_idn = ovm_dsk['disk_idn']
        activate_disk(cfg, vm_idn=vm_idn, vm_ohv_ip=_vm_hv_ip, multiply_disks=True, disk=ovm_dsk)
        exit_status, output = _hv_ssh.execute(
            f"for port in {{2048..2064}}; do nbd=`qemu-nbd -f -t --nocache --aio=native -p $port -f raw "
            f"/dev/{store_idn}/{disk_idn} --fork 2>&1` ; res=$? ; if [[ $res == 0 ]] && [[ $nbd == \"\" ]];"
            f" then echo $port; break; else port=$((port+1)); fi ; done"
        )
        if not exit_status_code_handler(
                exit_code=exit_status,
                message=f'[cold_migrate.py | STEP 8] Disk Migration failed. Output:\n\t{output}'
        ):
            return False

        nbd_port = output.strip()
        exit_status, output = _vhi_hv_ssh.execute(
            "qemu-img convert -p -n -t directsync"
            f" {sparse_opt} nbd://{_vm_hv_ip}:{nbd_port} -O qcow2 {_xml_vvm_disks[dsk_num]}", real_data=True
        )
        if not exit_status_code_handler(
                exit_code=exit_status,
                message=f'[cold_migrate.py | STEP 8] Disk Migration failed. Output:\n\t{output}'
        ):
            return False

        dsk_num += 1

        # Deactivate Disk
        _deactivation_props = {'disk_idn': ovm_dsk['disk_idn'],
                               'datastore_type': ovm_dsk['datastore_type'],
                               'path': ovm_dsk['path']}
        deactivate_result = deactivate_disk(cfg, vm_idn='', vm_ohv_ip=_vm_hv_ip, **_deactivation_props)
        if not deactivate_result:
            return False

    logs.info(f"The virtual server ``COLD MIGRATION`` has completed successfully:"
              f" {cfg.vhi_conf.url}/compute/servers/instances/{_vhi_vm_id}")

    # -- STEP 9 --
    logs.info(f"{_spaces}{_cm_msg}STEP #9 -- OnApp: Suspend VM [{vm_idn} | {_vm_properties['vm_ip_addr']}] --",
              header=True)
    result = suspend_vm(cfg, vm_id=vm_idn)
    if not result:
        logs.warn(msg=f'{_spaces} -- VM [{vm_idn} | {_vm_properties["vm_ip_addr"]}] has NOT been suspended.')

    logs.info(f"The virtual server ``COLD MIGRATION`` has completed successfully:"
              f" {cfg.vhi_conf.url}/compute/servers/instances/{_vhi_vm_id}")
    return True
