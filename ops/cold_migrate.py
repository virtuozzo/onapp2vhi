#!/usr/bin/env python2
import re
import click
import json
import xml.etree.ElementTree as KVMxml
from click_default_group import DefaultGroup
from inc.vhi_helpers import Vhi
from cfg.o2v_config import OnAppAPICredentials, VHICLoudDefaults, Helper
from inc.functions import run_command
from inc.logger import logs
from inc.onapp_helpers import (
    get_onapp_vm_flavor,
    get_onapp_vm_nics,
    get_onapp_vm_disks,
    get_vm_hypervisor_ip,
    activate_disk,
)
from inc.vhi_helpers import is_vm_active

def vm_cold_migrate(vdom='', vproj='', vuser='', vpass='', idn='', verb='', network=''):
    if idn == '':
        print ('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False

    if not network:
        _network = VHICLoudDefaults.VHI_NETWORK.value
    else:
        _network = network
    if not vdom:
        VHIDOM = VHICLoudDefaults.VINFRA_DOMAIN.value
    else:
        VHIDOM = vdom

    if not vproj:
        VHIPROJ = VHICLoudDefaults.VINFRA_PROJECT.value
    else:
        VHIPROJ = vproj

    if not vuser:
        VHIUSER = VHICLoudDefaults.VINFRA_USER.value
    else:
        VHIUSER = vuser

    if not vpass:
        VHIPASS = VHICLoudDefaults.VINFRA_PASS.value
    else:
        VHIPASS = vpass

    if not verb:
        verb = str(Helper.VERBOSITY.value)

    if not str(verb).isdigit():
        logs.info("Error: '--verbosity' parameter should be a number")
        return False

    if int(verb) < 0 or int(verb) > 8:
        logs.info("Error: '--verbosity' parameter should be a number between 0 and 8")
        return False

    if verb:
        verbosity = int(verb)
    else:
        verbosity = int(Helper.VERBOSITY.value)

    VM_IDn = idn
    # --step_1--#
    # --OnApp: get source VM parameters--#
    _onapp_hv_ip = get_vm_hypervisor_ip(vm_idn=VM_IDn)
    logs.info("-- STEP 1 -- OnApp: get source VM parameters --", separator=True)
    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/virtual_machines.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -r -c --arg vm_idn {vm_idn} '.[] | select(.virtual_machine.identifier==$vm_idn) | [ .virtual_machine.identifier, .virtual_machine.hypervisor_id, .virtual_machine.ip_addresses[0][\"ip_address\"][\"address\"], .virtual_machine.operating_system ] '".format(
        user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value,
        user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value,
        full_url=URL, vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD, verbosity, 0)
    vm_list = [a.replace('[', '').replace(']', '').replace('\"', '').split(',') for a in ou.splitlines()][0]
    vhi = Vhi()
    _on_app_flavor = get_onapp_vm_flavor(vm_list[0])
    vhi.create_object(_on_app_flavor, 'flavor')
    _flavour = vhi.flavor_name
    OVM_HV_ID = int(json.loads(ou)[1])
    OVM_OS = str(json.loads(ou)[3]).encode('ascii')
    # --OVM_HV_ID--#

    # --step_2--#
    # --OnApp: get source VM hypervisor IP address --#
    logs.info("-- STEP 2 -- OnApp: get VM's {hypervisor_ip} by {hypervisor_id} --", separator=True)
    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/hypervisors.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -r -c '.[] | select(.hypervisor.id=={hv_id}) | .hypervisor.ip_address '".format(
        user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value,
        user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value,
        full_url=URL, hv_id=OVM_HV_ID)
    (rc, ou) = run_command(CMD, verbosity, 0)
    VM_OHV_IP = str(ou).strip("\n")
    # --VM_OHV_IP--#

    # --step_3--#
    # --OnApp: get source VM NICs' params --#
    logs.info("-- STEP 3 -- OnApp: get VM's NICs' params --", separator=True)
    _onapp_nics = get_onapp_vm_nics(idn, verbosity)
    logs.info("OnApp_VM_NICs: ")
    for nic in _onapp_nics:
        logs.info(nic)
    logs.info("\n")

    # --step_4--#
    # --OnApp: get OnApp VM disk info --#
    logs.info("-- STEP 4 -- OnApp: get VM's disk info --", separator=True)
    _onapp_disks = get_onapp_vm_disks(idn)

    # --step_5--#
    # --OnApp: Check if VM is running at OnApp hypervisor --#
    logs.info("-- STEP 5 -- OnApp: check if VM [{vm_idn}] is running on HV [{hv_ip}] --".format(
        vm_idn=VM_IDn,
        hv_ip=VM_OHV_IP), separator=True)
    CMD = "ssh -p{ssh_port} {sshopt} root@{hv_ip} 'virsh list | grep {vm_idn}' 2>/dev/null ".format(
        hv_ip=VM_OHV_IP,
        ssh_port=OnAppAPICredentials.ONAPP_SSH_PORT_HV.value,
        sshopt=Helper.SSH_OPTS.value,
        vm_idn=VM_IDn
    )
    (rc, ou) = run_command(CMD, verbosity, 0)
    if ou:
        logs.warn("VM IS RUNNING.\n PLEASE, STOP THE VM BEFORE ITS OFFLINE MIGRATION.", separator=True)
        return False

    # --step_6--#
    # --OnApp: create similar VM on VHI side --#
    logs.info("-- STEP 6 -- VHI: create similar to OnApp VM [{vm_idn}] on VHI side --".format(vm_idn=VM_IDn),
              separator=True)
    onappvm_pri_ip = _onapp_nics[0]['ips'][0]
    onappvm_pri_mac = _onapp_nics[0]['mac']
    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'for vmid in `vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server list -f json | jq -r \".[] | .id \"`; do echo \"[\\\"$vmid\\\",\" `vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server iface list --server $vmid -f json | jq -c \".[] | [ .fixed_ips, .mac_addr ]\"` \"]\" | egrep -e \"{vm_ip}|{vm_mac}\"; done' 2>/dev/null ".format(
        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM,
        vhiproj=VHIPROJ, vhiuser=VHIUSER, vhipass=VHIPASS,
        vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, vm_ip=onappvm_pri_ip, vm_mac=onappvm_pri_mac)
    (rc, ou) = run_command(CMD, verbosity, 0)
    VHI_VM_ID = ''
    if OVM_OS == 'windows':
        VHI_IMAGE = VHICLoudDefaults.VHI_WINDOWS_IMAGE.value
    else:
        VHI_IMAGE = VHICLoudDefaults.VHI_LINUX_IMAGE.value

    if not ou:
        CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server create onapp2vhi_vm_{vm_idn} --description 'onapp_vm_{vm_idn}' --network id={network},fixed-ip={vm_ip},mac={vm_mac},spoofing-protection-disable --volume source=image,id={image},size={disk_size} --flavor {vhi_flavor} -f json | jq -r \".id\"' 2>/dev/null ".format(
            ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM, vhiproj=VHIPROJ,
            vhiuser=VHIUSER, vhipass=VHIPASS, vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, vm_idn=VM_IDn,
            vm_ip=onappvm_pri_ip, vm_mac=onappvm_pri_mac, vhi_sg=VHICLoudDefaults.VHI_SG_ID.value,
            image=VHI_IMAGE, disk_size=_onapp_disks[0]['size'], vhi_flavor=_flavour, network=_network)
        (rc, ou) = run_command(CMD, verbosity, 0)
        if not rc and ou:
            VHI_VM_ID = str(ou).strip("\n")
            logs.info("NEW VHI VM CREATED: " + VHICLoudDefaults.VHI_CP_URL.value + "/compute/servers/instances/" + VHI_VM_ID)
            if not is_vm_active(vm_id=VHI_VM_ID):
                exit(1)
            logs.info("...stopping VM before migration...")
            CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'for ((i=1;i<=100;i++)); do vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server stop {vm_id} --hard --wait --timeout 15 -f json | jq -r -c [.name,.id,.vm_state,.power_state,.status] ;  pwstate=\"`vinfra service compute server show {vm_id} -f json | jq -r .power_state `\" ; echo \"$pwstate\" ; if [[ \"$pwstate\" == \"SHUTDOWN\" ]]; then break; fi ; sleep 1; done' 2>/dev/null ".format(
              ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                    vhipass=VHIPASS, vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, vm_id=VHI_VM_ID)
            (rc, ou) = run_command(CMD, verbosity, 1)
        else:
            logs.error("The new vm was not created on VHI side. The migrations process is terminated".upper()+"\n"+CMD)
            exit(1)
        # ---
        logs.info('-------')
        logs.info("-- VHI: create and attach extra VHI VM's disks --")
        logs.info('---')
        if len(_onapp_disks) > 1:
            for idx, dsk in enumerate(_onapp_disks):
                if idx >= 1:
                    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute volume create --size {disk_size} onapp-{vm_id} --storage-policy default -f json | jq -c -r \".id\"' 2>/dev/null ".format(
                        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                        vhipass=VHIPASS, vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, disk_size=dsk['size'], vm_id=VHI_VM_ID)
                    (rc, ou) = run_command(CMD, verbosity, 0)
                    new_disk_id = str(ou).strip().encode('ascii')
                    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server volume attach --server {vm_id} {disk_id} -f json | jq -c ' 2>/dev/null".format(
                        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value,
                        vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER, vhipass=VHIPASS,
                        vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, vm_id=VHI_VM_ID, disk_id=new_disk_id)
                    (rc, ou) = run_command(CMD, verbosity, 0)
        # ---
        logs.info('-------')
        logs.info("-- VHI: allocate and assign extra VHI VM's IP addresses to primary NIC--")
        logs.info('---')
        if len(_onapp_nics[0]['ips']) > 1:
            IPS_PARAMS = ''
            for ip in _onapp_nics[0]['ips']:
                IPS_PARAMS += "--fixed-ip ip-address={} ".format(ip)
            CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server iface list --server {vm_id} -f json | jq -c -r .[0].id' 2>/dev/null".format(
                ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value,
                vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                vhipass=VHIPASS, vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, vm_id=VHI_VM_ID)
            (rc, ou) = run_command(CMD, verbosity, 0)
            VHI_NIC0_ID = str(ou).strip().encode('ascii')
            CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server iface set {ip_params} --server {vm_id} {nic_id} -f json | jq -c -r .fixed_ips' 2>/dev/null".format(
                ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value,
                vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                vhipass=VHIPASS, vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, ip_params=IPS_PARAMS,
                vm_id=VHI_VM_ID, nic_id=VHI_NIC0_ID)
            (rc, ou) = run_command(CMD, verbosity, 0)
        # ---
    else:
        logs.error("Destination VHI VM with IP/MAC ALREADY EXISTS:")
        logs.error(ou)
        VHI_VM_ID = str(json.loads(ou)[0])
        logs.error("...please, remove the target VM on VHI or remove conflicting network interface of it...\n")
        logs.error(VHICLoudDefaults.VHI_CP_URL.value + "/compute/servers/instances/" + str(VHI_VM_ID) + "/ \n")
        return False

    # --step_7--#
    # --VHI: define VM's hypervisor vinfra host and disks--#
    logs.info("-- STEP 7 -- VHI: define VHI VM's hypervisor and disks --", separator=True)
    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'host `vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server show {vm_id} -f json | jq -r .host`' 2>/dev/null | awk '/ has address /{{print $NF}}' ".format(
        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value,
        vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER, vhipass=VHIPASS,
        vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, vm_id=VHI_VM_ID)
    (rc, ou) = run_command(CMD, verbosity, 0)
    if re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ou) is not None:
        VHI_HV_IP = str(ou).strip("\n")
        logs.info("VMs_HV_IP: {}".format(VHI_HV_IP))
    else:
        logs.error("VM's VHI hypervisor IP address is invalid: {hv_ip}".format(hv_ip=ou), separator=True)
        return False
    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_hv} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server volume list --server {vm_id} -f json | jq -c' 2>/dev/null ".format(
        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value,
        vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER, vhipass=VHIPASS,
        vhi_hv=VHI_HV_IP, vm_id=VHI_VM_ID)
    (rc, ou) = run_command(CMD, verbosity, 0)
    vhivm_disks = json.loads(str(ou))
    VHI_VM_DISKS = {str(x['device'].split('/')[2]).encode('ascii'): str(x['id']).encode('ascii') for x in vhivm_disks}
    for disk_lb, disk_id in VHI_VM_DISKS.items():
        CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_hv} 'find /mnt/vstorage/vols/datastores/cinder/ -type f -name \"*volume-{disk_id}\"' 2>/dev/null".format(
            ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhi_hv=VHI_HV_IP, disk_id=disk_id)
        (rc, ou) = run_command(CMD, verbosity, 0)
        VHI_VM_DISKS[disk_lb] = str(ou).strip().encode('ascii')

    logs.info("VHI_VM_DISKS: {}".format(VHI_VM_DISKS))

    # --step_8--#
    # --VHI: define VM's hypervisor XML host and disks--#
    logs.info("-- STEP 8 -- VHI: get VHI VM XML config parameters --", separator=True)
    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_hv} 'virsh dumpxml {vm_id} 2>/dev/null > /tmp/{vm_id}.xml ; cat /tmp/{vm_id}.xml' 2>/dev/null".format(
        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhi_hv=VHI_HV_IP, vm_id=VHI_VM_ID)

    if not verbosity:
        (rc, ou) = run_command(CMD, 0, 0)
    else:
        (rc, ou) = run_command(CMD, 1, 0)

    VM_XML_CFG = str(ou)
    vhixml = KVMxml.fromstring(VM_XML_CFG)
    logs.info("---\nResult[{}]:\n".format(rc))
    XML_VVM_DISKS = []
    XML_VVM_NICS = []
    vvm_mac = vvm_nic_id = vvm_tap = ''

    for device in vhixml.findall("devices"):
        for disk in device.findall("disk"):
            if disk.attrib['device'] == "disk":
                XML_VVM_DISKS.append(disk.find('source').attrib['file'])

        for nic in device.findall("interface"):
            vvm_mac = nic.find('mac').attrib['address']
            vvm_nic_id = nic.find('virtualport').find('parameters').attrib['interfaceid']
            vvm_tap = nic.find('target').attrib['dev']
            XML_VVM_NICS.append({'mac': vvm_mac, 'id': vvm_nic_id, 'tap': vvm_tap})

    logs.info("XML_VVM_DISKS: " + str(XML_VVM_DISKS) + "\n")
    logs.info("XML_VVM_NICS: " + str(XML_VVM_NICS) + "\n")

    # --step_9--#
    # --OnApp: RUN O2V offline VM's disks migration from OnApp to VHI hypervisor --#
    logs.info("-- STEP 9 -- Run O2V offline VM's disks migration from OnApp to VHI hypervisor --".format(
        vm_idn=VM_IDn,
        hv_ip=VM_OHV_IP))
    if Helper.IMG_SPARSING.value:
        sparse_opt = '-S 1M'
    else:
        sparse_opt = ''

    dsk_num = 0
    for ovm_dsk in _onapp_disks:
        store_idn = ovm_dsk['datastore_idn']
        disk_idn = ovm_dsk['disk_idn']
        activate_disk(vm_idn=VM_IDn, vm_ohv_ip=_onapp_hv_ip, multiply_disks=True, disk=ovm_dsk)

        CMD = "ssh -p {ossh_port} {sshopt} root@{ohv_ip} 'for port in {{2048..2064}}; do nbd=`qemu-nbd -f -t --nocache --aio=native -p $port -f raw /dev/{ostor_idn}/{odsk_idn} --fork 2>&1` ; res=$? ; if [[ $res == 0 ]] && [[ $nbd == \"\" ]]; then echo $port; break; else port=$((port+1)); fi ; done' 2>/dev/null ".format(
            ossh_port=OnAppAPICredentials.ONAPP_SSH_PORT_HV.value, sshopt=Helper.SSH_OPTS.value, ohv_ip=VM_OHV_IP,
            ostor_idn=store_idn, odsk_idn=disk_idn)
        (rc, ou) = run_command(CMD, verbosity, 0)
        nbd_port = str(ou).strip().encode('ascii')
        CMD = "ssh -t -p {vssh_port} {sshopt} root@{vhv_ip} 'qemu-img convert -p -n -t directsync -o cluster_size=1048576,lazy_refcounts=on {sp_opt} nbd://{ohv_ip}:{nbdport} -O qcow2 {vdsk_path}' 2>/dev/null".format(
            vssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhv_ip=VHI_HV_IP,
            ohv_ip=VM_OHV_IP, nbdport=nbd_port,
            vdsk_path=XML_VVM_DISKS[dsk_num], sp_opt=sparse_opt)
        (rc, ou) = run_command(CMD, verbosity, 1)
        dsk_num += 1
    return True


@click.group(cls=DefaultGroup, default='coldmigrate', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--vdom', '--vhi-domain', default='', help="VHI Domain.")
@click.option('--vproj', '--vhi-project', default='', help="VHI Project.")
@click.option('--vuser', '--vhi-user', default='', help="VHI User.")
@click.option('--vpass', '--vhi-pass', '--vhi-password', default='', help="VHI Password.")
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
@click.option('--verb', '-v', '--v', '--verbosity', default='', help="Verbosity level of values between 0 and 8")
@click.option('--network', default='', help="Set network id")
# click.argument('name',default='') - not used
def coldmigrate(vdom='', vproj='', vuser='', vpass='', idn='', vhip='', verb='', network=''):
    vm_cold_migrate(vdom=vdom,
                    vproj=vproj,
                    vuser=vuser,
                    vpass=vpass,
                    idn=idn,
                    verb=verb,
                    network=network)


cli.add_command(coldmigrate)
