#!/usr/bin/env python2
import re
import json
import click
import xml.etree.ElementTree as KVMxml
from click_default_group import DefaultGroup
from inc.functions import run_command
from inc.onapp_helpers import get_onapp_vm_flavor, get_onapp_vm_disks, get_onapp_vm_nics
from inc.vhi_helpers import Vhi
from inc.logger import logs
from cfg.o2v_config import Helper, OnAppAPICredentials, VHICLoudDefaults


class Bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def vm_live_migrate(vdom='', vproj='', vuser='', vpass='', idn='', verb='', network=''):
    if not idn:
        logs.info('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
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
        logs.error("'--verbosity' parameter should be a number")
        return False

    if int(verb) < 0 or int(verb) > 8:
        logs.error("'--verbosity' parameter should be a number between 0 and 8")
        return False

    if verb:
        verbosity = int(verb)
    else:
        verbosity = int(Helper.VERBOSITY.value)

    VM_IDn = idn

    # --step_1--#
    # --OnApp: get source VM parameters--#

    NOTE = """ -- OnApp: get source VM parameters -- """

    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/virtual_machines.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -r -c --arg vm_idn {vm_idn} '.[] | select(.virtual_machine.identifier==$vm_idn) | [ .virtual_machine.identifier, .virtual_machine.hypervisor_id, .virtual_machine.ip_addresses[0][\"ip_address\"][\"address\"], .virtual_machine.operating_system, .virtual_machine.allowed_hot_migrate] '".format(
        user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value,
        full_url=URL, vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    vm_list = [a.replace('[', '').replace(']', '').replace('\"', '').split(',') for a in ou.splitlines()][0]
    vhi = Vhi()
    _on_app_flavor = get_onapp_vm_flavor(vm_list[0])
    vhi.create_object(_on_app_flavor, 'flavor')
    _flavour = vhi.flavor_name
    OVM_IDENTIFIER = str(json.loads(ou)[0]).encode('ascii')
    OVM_HV_ID = int(json.loads(ou)[1])
    OVM_OS = str(json.loads(ou)[3]).encode('ascii')
    OVM_HOT_MIGRATE = str(json.loads(ou)[4]).encode('ascii')

    if OVM_HOT_MIGRATE == 'False':
        logs.info(Bcolors.WARNING + "ATENTION hot_migrate is not allowed for VM \n" + Bcolors.ENDC)

    if OVM_HOT_MIGRATE == 'True':
        logs.info(Bcolors.OKGREEN + "HOT migrate is  allowed for VM \n" + Bcolors.ENDC)

    # --step_2--#
    # --OnApp: get source VM hypervisor IP address --#

    NOTE = """ -- OnApp: get VM's {hypervisor_ip} by {hypervisor_id} -- """

    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/hypervisors.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -r -c '.[] | select(.hypervisor.id=={hv_id}) | .hypervisor.ip_address '".format(
        user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value,
        full_url=URL, hv_id=OVM_HV_ID)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    VM_OHV_IP = str(ou).strip("\n")
    # --VM_OHV_IP--#

    # --step_3--#
    # --OnApp: get source VM NICs' params --#

    NOTE = """ -- OnApp: get VM's NICs' params -- """
    logs.info(NOTE)
    ONAPPVM_NICS = get_onapp_vm_nics(idn, verbosity)

    if verbosity >= 7:
        logs.info("OnApp_VM_NICs: ")
        for nic in ONAPPVM_NICS:
            logs.info(nic)

    # --step_4--#
    # --OnApp: get OnApp VM disk info --#

    NOTE = """ -- OnApp: get VM's disk info -- """
    logs.info(NOTE)
    ONAPPVM_DISKS = get_onapp_vm_disks(idn)
    logs.info("OnApp_VM_DISKS:")
    for disk_data in ONAPPVM_DISKS:
        logs.info(str(disk_data))
        logs.info("")

    # --step_5--#
    # --OnApp: Check if VM is running at OnApp hypervisor --#

    NOTE = """ -- OnApp: check if VM is running on HV -- """
    CMD = "ssh -p{ssh_port} {sshopt} root@{hv_ip} 'virsh list | grep {vm_idn}' 2>/dev/null ".format(hv_ip=VM_OHV_IP,
                                                                                                    ssh_port=OnAppAPICredentials.ONAPP_SSH_PORT_HV.value,
                                                                                                    sshopt=Helper.SSH_OPTS.value,
                                                                                                    vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    if not ou:
        logs.error("VM IS NOT RUNNING. PLEASE, START VM OR USE ``cold_migrate`` OPTION.")
        return False

    # --step_6--#
    # --OnApp: get VM's XML config from OnApp hypervisor --#

    NOTE = """ -- OnApp: get VM's XML config -- """

    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/virtual_machines.json"
    CMD = "ssh -p{ssh_port} {sshopt} root@{hv_ip} 'virsh dumpxml {vm_idn} > /tmp/{vm_idn}.xml && cat /tmp/{vm_idn}.xml ' 2>/dev/null ".format(
        ssh_port=OnAppAPICredentials.ONAPP_SSH_PORT_HV.value, sshopt=Helper.SSH_OPTS.value, hv_ip=VM_OHV_IP, vm_idn=VM_IDn)
    if not verbosity:
        (rc, ou) = run_command(CMD, 0, 0, NOTE)
    else:
        (rc, ou) = run_command(CMD, 1, 0, NOTE)
    VM_XML_CFG = str(ou)
    if verbosity >= 7:
        logs.info("[...result output is too big...]\n")
    if int(rc):
        logs.error("ERROR: Can't find VM running on Hypervisor. \n" + VM_XML_CFG)
        return False

    vmxml = KVMxml.fromstring(VM_XML_CFG)

    XML_OVM_DISKS = []
    XML_OVM_MACS = []

    for device in vmxml.findall("devices"):
        for disk in device.findall("disk"):
            if disk.attrib['device'] == "disk":
                disk_name = disk.find('target').attrib['dev']
                disk_path = disk.find('source').attrib['dev']
                XML_OVM_DISKS.append({'name': disk_name, 'path': disk_path})
        for nic in device.findall("interface"):
            XML_OVM_MACS.append(nic.find('mac').attrib['address'])

    if verbosity >= 7:
        logs.info("XML_OVM_DISKS: " + str(XML_OVM_DISKS) + "\n")
        logs.info("XML_OVM_MACS: " + str(XML_OVM_MACS) + "\n")

    # --step_7--#
    # --OnApp: create similar VM on VHI side --#

    NOTE = """ -- VHI: create similar to OnApp VM on VHI side -- """

    ONAPPVM_PRI_IP = ONAPPVM_NICS[0]['ips'][0]
    ONAPPVM_PRI_MAC = ONAPPVM_NICS[0]['mac']
    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'for vmid in `vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server list -f json | jq -r \".[] | .id \"`; do echo \"[\\\"$vmid\\\",\" `vinfra service compute server iface list --server $vmid -f json | jq -c \".[] | [ .fixed_ips, .mac_addr ]\"` \"]\" | egrep -e \"{vm_ip}|{vm_mac}\"; done' 2>/dev/null ".format(
        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER, vhipass=VHIPASS,
        vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, vm_ip=ONAPPVM_PRI_IP, vm_mac=ONAPPVM_PRI_MAC)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)

    VHI_VM_ID = ''

    if OVM_OS == 'windows':
        VHI_IMAGE = VHICLoudDefaults.VHI_WINDOWS_IMAGE.value
    else:
        VHI_IMAGE = VHICLoudDefaults.VHI_LINUX_IMAGE.value

    if not ou:
        _cmd = ""
        (rc, ou) = run_command(_cmd, verbosity, 0)

        CMD = "ssh -p {ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server create onapp2vhi_vm_{vm_idn} --description 'onapp_vm_{vm_idn}' --network id={network},fixed-ip={vm_ip},mac={vm_mac},spoofing-protection-disable --volume source=image,id={image},size={disk_size} --flavor {vhi_flavor} -f json | jq -r \".id\"' 2>/dev/null ".format(
            ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER, vhipass=VHIPASS,
            vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, vm_idn=VM_IDn, vm_ip=ONAPPVM_PRI_IP, vm_mac=ONAPPVM_PRI_MAC, vhi_sg=VHICLoudDefaults.VHI_SG_ID.value,
            image=VHI_IMAGE, disk_size=ONAPPVM_DISKS[0]['size'], vhi_flavor=_flavour, network=_network)
        (rc, ou) = run_command(CMD, verbosity, 0)
        if not rc and ou:
            VHI_VM_ID = str(ou).strip("\n")
            logs.info("NEW VHI VM CREATED: " + VHICLoudDefaults.VHI_CP_URL.value + "/compute/servers/instances/" + VHI_VM_ID)
            logs.info("...stopping target VHI VM before migration...")
            CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'while true; do vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server stop {vm_id} --hard --wait --timeout 15 -f json | jq -c [.name,.id,.vm_state,.power_state,.status] ;  pwstate=\"`vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server show {vm_id} -f json | jq -r .power_state `\" ; echo \"$pwstate\" ; if [[ \"$pwstate\" == \"SHUTDOWN\" ]]; then break; fi ; sleep 1; done' 2>/dev/null ".format(
                ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                vhipass=VHIPASS, vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, vm_id=VHI_VM_ID)
            run_command(CMD, verbosity, 1)

        NOTE = """ -- VHI: create and attach extra VHI VM's disks -- """

        if len(ONAPPVM_DISKS) > 1:
            for idx, dsk in enumerate(ONAPPVM_DISKS):
                if idx >= 1:
                    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute volume create --size {disk_size} onapp-{vm_id} --storage-policy default -f json | jq -c -r \".id\"' 2>/dev/null ".format(
                        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                        vhipass=VHIPASS, vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, disk_size=dsk['size'], vm_id=VHI_VM_ID)
                    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
                    new_disk_id = str(ou).strip().encode('ascii')
                    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server volume attach --server {vm_id} {disk_id} -f json | jq -c ' 2>/dev/null".format(
                        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                        vhipass=VHIPASS, vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, vm_id=VHI_VM_ID, disk_id=new_disk_id)
                    (rc, ou) = run_command(CMD, verbosity, 0)

        NOTE = """ -- VHI: allocate and assign extra VHI VM's IP addresses to primary NIC-- """

        if len(ONAPPVM_NICS[0]['ips']) > 1:
            IPS_PARAMS = ''
            for ip in ONAPPVM_NICS[0]['ips']:
                IPS_PARAMS += "--fixed-ip ip-address={} ".format(ip)
            CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server iface list --server {vm_id} -f json | jq -c -r .[0].id' 2>/dev/null".format(
                ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                vhipass=VHIPASS, vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, vm_id=VHI_VM_ID)
            (rc, ou) = run_command(CMD, verbosity, 0)
            VHI_NIC0_ID = str(ou).strip().encode('ascii')
            CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server iface set {ip_params} --server {vm_id} {nic_id} -f json | jq -c -r .fixed_ips' 2>/dev/null".format(
                ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                vhipass=VHIPASS, vhi_cp=VHICLoudDefaults.VHI_CP_IP.value, ip_params=IPS_PARAMS, vm_id=VHI_VM_ID, nic_id=VHI_NIC0_ID)
            (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    else:
        logs.info("Destination VHI VM with IP/MAC ALREADY EXISTS:")
        logs.info(ou)
        VHI_VM_ID = str(json.loads(ou)[0])
        logs.error("...please remove the target VM on VHI or remove conflicting network interface of it...\n")
        logs.error(VHICLoudDefaults.VHI_CP_URL.value + "/compute/servers/instances/" + VHI_VM_ID + "/ \n")
        return False

    # --step_9--#
    # --VHI: define VM's hypervisor vinfra host and DISKS --#

    NOTE = """ -- VHI: define VHI VM's hypervisor and disks -- """

    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'host `vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server show {vm_id} -f json | jq -r .host`' 2>/dev/null | awk '/ has address /{{print $NF}}' ".format(
        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value,
        sshopt=Helper.SSH_OPTS.value,
        vhidom=VHIDOM,
        vhiproj=VHIPROJ,
        vhiuser=VHIUSER,
        vhipass=VHIPASS,
        vhi_cp=VHICLoudDefaults.VHI_CP_IP.value,
        vm_id=VHI_VM_ID)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    if re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ou) is not None:
        VHI_HV_IP = str(ou).strip("\n")
        logs.info("VMs_HV_IP: {}".format(VHI_HV_IP))
    else:
        logs.error("Error: Destination Appliance network is not configured properly".format(hv_ip=ou))
        return False
    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_hv} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server volume list --server {vm_id} -f json | jq -c' 2>/dev/null ".format(
        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER, vhipass=VHIPASS,
        vhi_hv=VHI_HV_IP, vm_id=VHI_VM_ID)
    (rc, ou) = run_command(CMD, verbosity, 0)
    vhivm_disks = json.loads(str(ou))

    VHI_VM_DISKS = {str(x['device'].split('/')[2]).encode('ascii'): str(x['id']).encode('ascii') for x in vhivm_disks}

    for disk_lb, disk_id in VHI_VM_DISKS.items():
        CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_hv} 'find /mnt/vstorage/vols/datastores/cinder/ -type f -name \"*volume-{disk_id}\"' 2>/dev/null".format(
            ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhi_hv=VHI_HV_IP, disk_id=disk_id)
        (rc, ou) = run_command(CMD, verbosity, 0)
        VHI_VM_DISKS[disk_lb] = str(ou).strip().encode('ascii')

    logs.info("VHI VM DISKS: {}".format(VHI_VM_DISKS))

    # --step_10--#
    # --VHI: define VM's hypervisor XML host and disks--#

    NOTE = """ -- VHI: get VHI VM XML config parameters -- """

    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_hv} 'virsh dumpxml {vm_id} 2>/dev/null > /tmp/{vm_id}.xml ; cat /tmp/{vm_id}.xml' 2>/dev/null".format(
        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhi_hv=VHI_HV_IP, vm_id=VHI_VM_ID)
    if not verbosity:
        (rc, ou) = run_command(CMD, 0, 0, NOTE)
    else:
        (rc, ou) = run_command(CMD, 1, 0, NOTE)

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

    # --step_11--#
    # --OnApp: edit VM's XML config for VHI --#

    NOTE = """ STEP 11: Process and upload VM's XML config """

    global disk_num
    global nic_num
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
                    source.attrib['file'] = VHI_VM_DISKS[disk_label]
                    del source.attrib['dev']
            elif disk.attrib['device'] == "cdrom":
                # device.remove(disk)
                cdrom_file = disk.find('source').attrib['file']
                disk.find('source').attrib['file'] = '/tmp/grub2.img'
                CMD = "ssh -p{ssh_port} {sshopt} root@{ohv_ip} 'scp -P {ssh_port} {scpopt} {cd_file} root@{vhv_ip}:/tmp/ 2>/dev/null ' 2>/dev/null ; ssh -p{ssh_port} root@{vhv_ip} 'ls /tmp/grub2*' 2>/dev/null ".format(
                    ohv_ip=VM_OHV_IP, vhv_ip=VHI_HV_IP, ssh_port=OnAppAPICredentials.ONAPP_SSH_PORT_HV.value,
                    sshopt=Helper.SSH_OPTS.value, scpopt=Helper.SCP_OPTS.value, cd_file=cdrom_file, vm_idn=VM_IDn)
                (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
        nic_num = 0
        for nic in device.findall("interface"):
            if not nic_num:
                for src in nic.findall('source'):
                    src.attrib['bridge'] = 'br-int'
                vport = nic.findall('virtualport')
                if not vport:
                    vp = KVMxml.Element('virtualport', type='openvswitch')
                    prm = KVMxml.Element('parameters', interfaceid=XML_VVM_NICS[0]['id'])
                    vp.text = "\n\t"
                    vp.tail = "\n      "
                    prm.tail = "\n      "
                    nic.insert(2, vp)
                    vp.append(prm)
                for tgt in nic.findall('target'):
                    tgt.attrib['dev'] = XML_VVM_NICS[0]['tap']
            elif nic_num > 0:
                device.remove(nic)
            nic_num += 1

    # Debug file xml
    # logs.info(KVMxml.tostring(vmxml))
    xmltree = KVMxml.ElementTree(vmxml)
    xmltree.write("/tmp/{}.xml".format(OVM_IDENTIFIER))

    # --step_11--#
    # --OnApp: Upload O2V migration XML to OnApp hypervisor --#

    NOTE = """ -- Upload OnApp2VHI VM migration XML to OnApp HV -- """
    CMD = "scp -P{ssh_port} {scpopt} /tmp/{vm_idn}.xml root@{hv_ip}:/tmp/ 2>/dev/null ; ssh -p{ssh_port} {sshopt} root@{hv_ip} 'ls /tmp/{vm_idn}.xml' 2>/dev/null ".format(
        hv_ip=VM_OHV_IP, scpopt=Helper.SCP_OPTS.value, ssh_port=OnAppAPICredentials.ONAPP_SSH_PORT_HV.value, sshopt=Helper.SSH_OPTS.value, vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)

    # --step_12--#
    # --OnApp: RUN O2V migration from OnApp to VHI hypervisor --#

    NOTE = """ -- Run OnApp2VHI VM  migration from OnApp to VHI hypervisor -- """

    onappvm_disks = ",".join([str(dsk['name']) for dsk in XML_OVM_DISKS])
    CMD = "ssh -t -p{ossh_port} {sshopt} root@{ohv_ip} 'virsh migrate --live --auto-converge --unsafe --copy-storage-all --migrate-disks {vm_disks} --xml /tmp/{vm_idn}.xml --verbose {vm_idn} qemu+ssh://{vhv_ip}:{vssh_port}/system?no_verify=1 tcp:{vhv_ip}' 2>/dev/null ".format(
        ohv_ip=VM_OHV_IP, vhv_ip=VHI_HV_IP, ossh_port=OnAppAPICredentials.ONAPP_SSH_PORT_HV.value, vssh_port=VHICLoudDefaults.VHI_SSH_PORT_HV.value, sshopt=Helper.SSH_OPTS.value,
        vm_disks=onappvm_disks, vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD, 8, 1, NOTE)

    # --step_13--#
    # --OnApp: STOP just migrated OnApp VM on VHI hypervisor --#

    NOTE = """ -- Stop just migrate OnApp VM on VHI hypervisor -- """
    # ToDo add validation to check whether VM  is created
    #  -----
    CMD = "ssh -p{vssh_port} {sshopt} root@{vhi_hv} 'virsh destroy {vm_idn}' 2>/dev/null ".format(vhi_hv=VHI_HV_IP,
                                                                                                  vssh_port=VHICLoudDefaults.VHI_SSH_PORT_HV.value,
                                                                                                  sshopt=Helper.SSH_OPTS.value,
                                                                                                  vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)

    # --step_14--#
    # --OnApp: START origina pre-created VHI VM on VHI hypervisor --#

    NOTE = """ -- Start original pre-created VHI VM on VHI hypervisor -- """

    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_hv} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server start {vm_id} -f json | jq -c -r \"[ .id , .power_state ]\" ' 2>/dev/null ".format(
        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value, sshopt=Helper.SSH_OPTS.value, vhidom=VHIDOM,
        vhiproj=VHIPROJ, vhiuser=VHIUSER, vhipass=VHIPASS, vhi_hv=VHI_HV_IP, vm_id=VHI_VM_ID)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    return True


@click.group(cls=DefaultGroup, default='livemigrate', invoke_without_command=True, default_if_no_args=True)
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
def livemigrate(vdom='', vproj='', vuser='', vpass='', idn='', verb='', network=''):
    vm_live_migrate(vdom=vdom,
                    vproj=vproj,
                    vuser=vuser,
                    vpass=vpass,
                    idn=idn,
                    verb=verb,
                    network=network)


cli.add_command(livemigrate)
