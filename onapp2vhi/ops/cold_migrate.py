from onapp2vhi.inc.onapp_helpers import *
from onapp2vhi.inc.network_hanlder import get_network_configuration
from onapp2vhi.utilities.config import OnApp2VHIConfig

cfg = OnApp2VHIConfig()

def vm_cold_migrate(vdom: str, vproj: str, idn: str, network: str, vhi_obj, placement=''):
    # ToDo
    #  verify IP address before running script
    if not idn:
        logs.info('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False
    VM_IDn = idn

    _network = network if network else cfg.vhi_conf['network']
    _vhidom = vdom if vdom else cfg.vhi_conf['vinfra_domain']
    _vhiproj = vproj if vproj else cfg.vhi_conf['vinfra_project']

    _spaces = Helper.SPACES.value
    _cm_msg = 'COLD MIGRATION -- '
    logs.info(f'{_spaces}-- {_cm_msg}', header=True)

    # -- STEP 1 --
    logs.info(f"{_spaces}{_cm_msg}STEP #1 -- OnApp: Get source VM properties --", header=True)
    _vm_properties = get_vm_source_properties(vm_idn=VM_IDn)
    _vm_hv_ip = _vm_properties['hv_ip']
    vhi = vhi_obj
    _on_app_flavor = get_onapp_vm_flavor(vm_idn=VM_IDn)
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
    _onapp_nics = get_onapp_vm_nics(idn)

    # -- STEP 3 --
    logs.info(f"{_spaces}{_cm_msg}STEP #3 -- OnApp: get VM's disk info --", header=True)
    _onapp_disks = get_onapp_vm_disks(idn)

    # -- STEP 4 --
    logs.info(f"{_spaces}{_cm_msg}STEP #4 -- OnApp: check if VM [{VM_IDn}] is running on HV [{_vm_hv_ip}] --",
              header=True)
    _hv_ssh = SSH(**{'host': _vm_hv_ip})
    exit_status, output = _hv_ssh.execute(f"virsh list | grep {VM_IDn}")
    if output:
        logs.warn("VM IS RUNNING.\n PLEASE, STOP THE VM BEFORE ITS OFFLINE MIGRATION.")
        return False

    # -- STEP 5 --
    logs.info(f"{_spaces}{_cm_msg}STEP #5 -- VHI: create similar to OnApp VM [{VM_IDn}] on VHI side --",
              separator=True)
    onappvm_pri_ip = _onapp_nics[0]['ips'][0]
    onappvm_pri_mac = _onapp_nics[0]['mac']

    # Here we generate vinfra access to create VM
    vinfra_access = f"{cfg.ADMIN_AUTH} --vinfra-domain='{_vhidom}' --vinfra-project='{_vhiproj}'"
    if cfg.vhi_conf['vinfra_domain'] != 'Default':
        vinfra_access = f"{cfg.DOMAIN_AUTH}  --vinfra-domain='{_vhidom}' --vinfra-project='{_vhiproj}'"
    _vhi_ssh = SSH(**{'host': cfg.vhi_conf['cp_ip'], 'port': cfg.vhi_conf['cloud_ssh_port']})
    exit_status, output = _vhi_ssh.execute(f"{cfg.ADMIN_AUTH} service compute server list --long -f json")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[cold_migrate.py | STEP 5] Compute server list command failed. Output:\n\t{output}"
    ):
        return False

    vhi_vms = json.loads(output)
    _error_msg = ''
    vm_created = False
    for _vm in vhi_vms:
        _vm_id = _vm['id']
        _error_msg = (f"VM with [IP: {onappvm_pri_ip} | MAC: {onappvm_pri_mac}] ALREADY EXISTS on VHI side.\n"
                      f"VM: {cfg.vhi_conf['url']}/compute/servers/instances/{_vm_id}/")
        if not _vm['networks'] and _vm['name'] == f'vm_{_vm_properties["hostname"].lower()}_{VM_IDn}':
            vm_created = True
            break

        if onappvm_pri_mac == _vm['networks'][0]['mac_addr'] or onappvm_pri_ip in _vm['networks'][0]['ips']:
            vm_created = True
            break

    _vhi_vm_id = ''
    _network = get_network_configuration(virtual_server_identifier=VM_IDn, vinfra_project=_vhiproj)
    if not _network:
        logs.error("The network issue is hit. Could you please check logs.")
        return False

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

    # -- STEP 6 --
    logs.info(f"{_spaces}{_cm_msg}STEP #6 -- VHI: define VHI VM's hypervisor and disks --", header=True)
    exit_status, output = _vhi_ssh.execute(f"host `{cfg.ADMIN_AUTH} service compute server show {_vhi_vm_id} -f json"
                                           f" | jq -r .host` 2>/dev/null | awk '/ has address /{{print $NF}}'")
    if re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', output):
        _vhi_hv_ip = output.strip("\n")
        logs.info(f"VMs HV IP: {_vhi_hv_ip}")
    else:
        logs.error("Error: Destination Appliance network is not configured properly:")
        return False

    _vhi_hv_ssh = SSH(**{'host': _vhi_hv_ip})
    exit_status, output = _vhi_hv_ssh.execute(f"{vinfra_access} service compute server volume list"
                                              f" --server {_vhi_vm_id} -f json | jq -c 2>/dev/null")
    vhivm_disks = json.loads(output)
    _vhi_vm_disks = {str(x['device'].split('/')[2]): str(x['id']) for x in vhivm_disks}
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
        activate_disk(vm_idn=VM_IDn, vm_ohv_ip=_vm_hv_ip, multiply_disks=True, disk=ovm_dsk)
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
            f"qemu-img convert -p -n -t directsync -o cluster_size=1048576,lazy_refcounts=on"
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
        deactivate_result = deactivate_disk(vm_idn='', vm_ohv_ip=_vm_hv_ip, **_deactivation_props)
        if not deactivate_result:
            return False

    logs.info(f"The virtual server ``COLD MIGRATION`` has completed successfully:"
              f" {cfg.vhi_conf.url}/compute/servers/instances/{_vhi_vm_id}")
    return True
