#!/usr/bin/env python2

import os
import re
import sys
import xml
import json
import click
import xml.etree.ElementTree as KVMxml
from click_default_group import DefaultGroup

plug_path = os.getcwd()
# print plug_path
sys.path.append(plug_path)
sys.path.append(plug_path + '/cfg')
sys.path.append(plug_path + '/inc')

from o2v_config import *
from functions import *
from onapp_helpers import *
from vhi_helpers import Vhi

@click.group(cls=DefaultGroup, default='vm', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--vdom', '--vhi-domain', default='', help="VHI Domain.")
@click.option('--vproj', '--vhi-project', default='', help="VHI Project.")
@click.option('--vuser', '--vhi-user', default='', help="VHI User.")
@click.option('--vpass', '--vhi-pass', '--vhi-password', default='', help="VHI Password.")
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
@click.option('--vhip', '--vhi-ip', '--vhi-hypervisor-ip', default='', help="VHI destination HV IP address.")
@click.option('--snc', '--save-n-copy', is_flag=True, default=False, help="User Save-and-Copy mode.")
@click.option('--verb', '-v', '--v', '--verbosity', default='', help="Verbolity level of values between 0 and 8")
# click.argument('name',default='') - not used
def vm(vdom='', flavor='', vproj='', vuser='', vpass='', idn='', vhip='', snc='', verb=''):
    if idn == '':
        print ('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        exit(17)
    #    if vhip == '':
    #       print ('You need to pass VHI hypervisor IP address through --vhi-ip=? parameter ')
    #       exit(18)

    if vdom == '':
        VHIDOM = VINFRA_DOMAIN
    else:
        VHIDOM = vdom
    if vproj == '':
        VHIPROJ = VINFRA_PROJECT
    else:
        VHIPROJ = vproj
    if vuser == '':
        VHIUSER = VINFRA_USER
    else:
        VHIUSER = vuser
    if vpass == '':
        VHIPASS = VINFRA_PASS
    else:
        VHIPASS = vpass

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

    click.echo('...VM migration from OnApp to VHI...')

    VM_IDn = idn

    # --step_1--#
    # --OnApp: get source VM parameters--#
    logs.info('-------')
    logs.info("-- OnApp: get source VM parameters --")
    URL = ONAPP_CP_URL + "/virtual_machines.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -r -c --arg vm_idn {vm_idn} '.[] | select(.virtual_machine.identifier==$vm_idn) | [ .virtual_machine.identifier, .virtual_machine.hypervisor_id, .virtual_machine.ip_addresses[0][\"ip_address\"][\"address\"], .virtual_machine.operating_system ] '".format(
        user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL, vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD, verbosity, 0)
    vhi = Vhi()
    _on_app_flavor = get_onapp_vm_flavor(ou[0])
    vhi.create_object(_on_app_flavor, 'flavor')
    _flavour = vhi.flavor_name
    OVM_IDENTIFIER = str(json.loads(ou)[0]).encode('ascii')
    OVM_HV_ID = int(json.loads(ou)[1])
    OVM_OS = str(json.loads(ou)[3]).encode('ascii')
    # --OVM_HV_ID--#

    # --step_2--#
    # --OnApp: get source VM hypervisor IP address --#
    logs.info('-------')
    logs.info("-- OnApp: get VM's {hypervisor_ip} by {hypervisor_id} --")
    URL = ONAPP_CP_URL + "/hypervisors.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -r -c '.[] | select(.hypervisor.id=={hv_id}) | .hypervisor.ip_address '".format(
        user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL, hv_id=OVM_HV_ID)
    (rc, ou) = run_command(CMD, verbosity, 0)
    VM_OHV_IP = str(ou).strip("\n")
    # --VM_OHV_IP--#

    # --step_3--#
    # --OnApp: get source VM NICs' params --#
    logs.info('-------')
    logs.info("-- OnApp: get VM's NICs' params --")

    ONAPPVM_NICS = get_onapp_vm_nics(idn, verbosity)

    logs.info("OnApp_VM_NICs: ")
    for nic in ONAPPVM_NICS:
        logs.info(nic)
    logs.info("\n")

    # --ONAPPVM_NICS--#

    # --step_4--#
    # --OnApp: get OnApp VM disk info --#
    logs.info('-------')
    logs.info("-- OnApp: get VM's disk info --")

    ONAPPVM_DISKS = get_onapp_vm_disks(idn, verbosity)

    print ("OnApp_VM_DISKS:")
    for disk_data in ONAPPVM_DISKS:
        logs.info(str(disk_data))
    logs.info("")

    # --ONAPPVM_DISKS--#

    # --step_5--#
    # --OnApp: Check if VM is running at OnApp hypervisor --#
    logs.info('-------')
    logs.info("-- OnApp: check if VM [{vm_idn}] is running on HV [{hv_ip}] --".format(vm_idn=VM_IDn, hv_ip=VM_OHV_IP))
    CMD = "ssh -p{ssh_port} {sshopt} root@{hv_ip} 'virsh list | grep {vm_idn}' 2>/dev/null ".format(hv_ip=VM_OHV_IP,
                                                                                                    ssh_port=ONAPP_SSH_PORT,
                                                                                                    sshopt=SSH_OPTS,
                                                                                                    vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD, verbosity, 0)
    if ou != "":
        logs.info("VM IS RUNNING.\n PLEASE, STOP THE VM BEFORE ITS OFFLINE MIGRATION.")
        exit(11)

    # --is_VM_Offline--#

    # --step_8--#
    # --OnApp: create similar VM on VHI side --#
    logs.info('-------')
    logs.info("-- VHI: create similar to OnApp VM [{vm_idn}] on VHI side --".format(vm_idn=VM_IDn))
    logs.info('---')
    ONAPPVM_PRI_IP = ONAPPVM_NICS[0]['ips'][0]
    ONAPPVM_PRI_MAC = ONAPPVM_NICS[0]['mac']
    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'for vmid in `vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server list -f json | jq -r \".[] | .id \"`; do echo \"[\\\"$vmid\\\",\" `vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server iface list --server $vmid -f json | jq -c \".[] | [ .fixed_ips, .mac_addr ]\"` \"]\" | egrep -e \"{vm_ip}|{vm_mac}\"; done' 2>/dev/null ".format(
        ssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER, vhipass=VHIPASS,
        vhi_cp=VHI_CP_IP, vm_ip=ONAPPVM_PRI_IP, vm_mac=ONAPPVM_PRI_MAC)
    (rc, ou) = run_command(CMD, verbosity, 0)

    VHI_VM_ID = ''

    if OVM_OS == 'windows':
        VHI_IMAGE = VHI_WINDOWS_IMAGE
    else:
        VHI_IMAGE = VHI_LINUX_IMAGE

    if ou == '':
        # logs.info("LETS CREATE TARGET VM: ")
        CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server create onapp2vhi_vm_{vm_idn} --description 'onapp_vm_{vm_idn}' --network id=public,fixed-ip={vm_ip},mac={vm_mac},spoofing-protection-disable --volume source=image,id={image},size={disk_size} --flavor {vhi_flavor} -f json | jq -r \".id\"' 2>/dev/null ".format(
            ssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER, vhipass=VHIPASS,
            vhi_cp=VHI_CP_IP, vm_idn=VM_IDn, vm_ip=ONAPPVM_PRI_IP, vm_mac=ONAPPVM_PRI_MAC, vhi_sg=VHI_SG_ID,
            image=VHI_IMAGE, disk_size=ONAPPVM_DISKS[0]['size'], vhi_flavor=_flavour)
        (rc, ou) = run_command(CMD, verbosity, 0)
        if rc == 0 and ou != '':
            VHI_VM_ID = str(ou).strip("\n")
            logs.info("NEW VHI VM CREATED: " + VHI_CP_URL + "/compute/servers/instances/" + VHI_VM_ID)
            logs.info("...STOPPING VM BEFORE MIGRATION...")
            CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'while true; do vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server stop {vm_id} --hard --wait --timeout 15 -f json | jq -r -c [.name,.id,.vm_state,.power_state,.status] ;  pwstate=\"`vinfra service compute server show {vm_id} -f json | jq -r .power_state `\" ; echo \"$pwstate\" ; if [[ \"$pwstate\" == \"SHUTDOWN\" ]]; then break; fi ; sleep 1; done' 2>/dev/null ".format(
                ssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                vhipass=VHIPASS, vhi_cp=VHI_CP_IP, vm_id=VHI_VM_ID)
            run_command(CMD, verbosity, 1)
        # ---
        logs.info('-------')
        logs.info("-- VHI: create and attach extra VHI VM's disks --")
        logs.info('---')
        if len(ONAPPVM_DISKS) > 1:
            for idx, dsk in enumerate(ONAPPVM_DISKS):
                if idx >= 1:
                    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute volume create --size {disk_size} onapp-{vm_id} --storage-policy default -f json | jq -c -r \".id\"' 2>/dev/null ".format(
                        ssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                        vhipass=VHIPASS, vhi_cp=VHI_CP_IP, disk_size=dsk['size'], vm_id=VHI_VM_ID)
                    (rc, ou) = run_command(CMD, verbosity, 0)
                    new_disk_id = str(ou).strip().encode('ascii')
                    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server volume attach --server {vm_id} {disk_id} -f json | jq -c ' 2>/dev/null".format(
                        ssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                        vhipass=VHIPASS, vhi_cp=VHI_CP_IP, vm_id=VHI_VM_ID, disk_id=new_disk_id)
                    (rc, ou) = run_command(CMD, verbosity, 0)
        # ---
        logs.info('-------')
        logs.info("-- VHI: allocate and assign extra VHI VM's IP addresses to primary NIC--")
        logs.info('---')
        if len(ONAPPVM_NICS[0]['ips']) > 1:
            IPS_PARAMS = ''
            for ip in ONAPPVM_NICS[0]['ips']:
                IPS_PARAMS += "--fixed-ip ip-address={} ".format(ip)
            CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server iface list --server {vm_id} -f json | jq -c -r .[0].id' 2>/dev/null".format(
                ssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                vhipass=VHIPASS, vhi_cp=VHI_CP_IP, vm_id=VHI_VM_ID)
            (rc, ou) = run_command(CMD, verbosity, 0)
            VHI_NIC0_ID = str(ou).strip().encode('ascii')
            CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server iface set {ip_params} --server {vm_id} {nic_id} -f json | jq -c -r .fixed_ips' 2>/dev/null".format(
                ssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER,
                vhipass=VHIPASS, vhi_cp=VHI_CP_IP, ip_params=IPS_PARAMS, vm_id=VHI_VM_ID, nic_id=VHI_NIC0_ID)
            (rc, ou) = run_command(CMD, verbosity, 0)
        # ---
    else:
        logs.info("Destination VHI VM with IP/MAC ALREADY EXISTS:")
        logs.info(ou)
        VHI_VM_ID = str(json.loads(ou)[0])
        logs.info("...please, remove the target VM on VHI or remove conflicting network interface of it...\n")
        logs.info(VHI_CP_URL + "/compute/servers/instances/" + json.loads(ou)[0] + "/ \n")
        # exit(13)

    # --step_9--#
    # --VHI: define VM's hypervisor vinfra host and disks--#
    logs.info('-------')
    logs.info("-- VHI: define VHI VM's hypervisor and disks --")
    logs.info('---')
    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'host `vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server show {vm_id} -f json | jq -r .host`' 2>/dev/null | awk '/ has address /{{print $NF}}' ".format(
        ssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER, vhipass=VHIPASS,
        vhi_cp=VHI_CP_IP, vm_id=VHI_VM_ID)
    (rc, ou) = run_command(CMD, verbosity, 0)
    if re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ou) != None:
        VHI_HV_IP = str(ou).strip("\n")
        logs.info("VMs_HV_IP: {}".format(VHI_HV_IP))
    else:
        logs.info("Error: VM's VHI hypervisor IP address is invalid: {hv_ip}".format(hv_ip=ou))
        exit(23)
    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_hv} 'vinfra --vinfra-domain=\"{vhidom}\" --vinfra-project=\"{vhiproj}\" --vinfra-username=\"{vhiuser}\" --vinfra-password=\"{vhipass}\" service compute server volume list --server {vm_id} -f json | jq -c' 2>/dev/null ".format(
        ssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhidom=VHIDOM, vhiproj=VHIPROJ, vhiuser=VHIUSER, vhipass=VHIPASS,
        vhi_hv=VHI_HV_IP, vm_id=VHI_VM_ID)
    (rc, ou) = run_command(CMD, verbosity, 0)
    vhivm_disks = json.loads(str(ou))

    VHI_VM_DISKS = {str(x['device'].split('/')[2]).encode('ascii'): str(x['id']).encode('ascii') for x in vhivm_disks}

    for disk_lb, disk_id in VHI_VM_DISKS.items():
        CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_hv} 'find /mnt/vstorage/vols/datastores/cinder/ -type f -name \"*volume-{disk_id}\"' 2>/dev/null".format(
            ssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhi_hv=VHI_HV_IP, disk_id=disk_id)
        (rc, ou) = run_command(CMD, verbosity, 0)
        VHI_VM_DISKS[disk_lb] = str(ou).strip().encode('ascii')

    logs.info("VHI_VM_DISKS: {}".format(VHI_VM_DISKS))

    # --step_10--#
    # --VHI: define VM's hypervisor XML host and disks--#
    logs.info('-------')
    logs.info("-- VHI: get VHI VM XML config parameters --")
    logs.info('---')
    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_hv} 'virsh dumpxml {vm_id} 2>/dev/null > /tmp/{vm_id}.xml ; cat /tmp/{vm_id}.xml' 2>/dev/null".format(
        ssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhi_hv=VHI_HV_IP, vm_id=VHI_VM_ID)

    if verbosity == 0:
        (rc, ou) = run_command(CMD, 0, 0)
    else:
        (rc, ou) = run_command(CMD, 1, 0)

    VM_XML_CFG = str(ou)
    vhixml = KVMxml.fromstring(VM_XML_CFG)

    logs.info("---\nResult[{}]:\n".format(rc))

    #    logs.info(KVMxml.tostring(vhixml))
    #    logs.info(VM_XML_CFG)
    logs.info('---')

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

    # --step_12--#
    # --OnApp: RUN O2V offline VM's disks migration from OnApp to VHI hypervisor --#
    logs.info('-------')
    logs.info("-- Run O2V offline VM's disks migration from OnApp to VHI hypervisor --".format(vm_idn=VM_IDn,
                                                                                               hv_ip=VM_OHV_IP))
    if IMG_SPARSING:
        sparse_opt = '-S 1M'
    else:
        sparse_opt = ''
    if snc:
        dsk_num = 0
        for ovm_dsk in ONAPPVM_DISKS:
            store_idn = ovm_dsk['datastore_idn']
            disk_idn = ovm_dsk['disk_idn']
            CMD = "ssh -p{ossh_port} {sshopt} root@{ocp_ip} 'curl -k -s -X PUT -d \"{{\\\"state\\\":3}}\" {ohv_ip}:8080/lvm/Datastore/{stor_idn}/VDisk/{dsk_idn}' 2>/dev/null".format(
                ocp_ip=ONAPP_CP_HOST, ossh_port=ONAPP_SSH_PORT, sshopt=SSH_OPTS, ohv_ip=VM_OHV_IP, stor_idn=store_idn,
                dsk_idn=disk_idn)
            (rc, ou) = run_command(CMD, 0, 0)
            CMD = "ssh -t -p{ossh_port} {sshopt} root@{ohv_ip} 'qemu-img convert -p -f raw -O qcow2 -o cluster_size=1048576,lazy_refcounts=on {sp_opt} /dev/{ostor_idn}/{odsk_idn} /onapp/backups/{odsk_idn}.qcow2' 2>/dev/null".format(
                ossh_port=ONAPP_SSH_PORT, sshopt=SSH_OPTS, ohv_ip=VM_OHV_IP, ostor_idn=store_idn, odsk_idn=disk_idn,
                sp_opt=sparse_opt)
            (rc, ou) = run_command(CMD, verbosity, 1)
            CMD = "ssh -p{ossh_port} {sshopt} root@{ocp_ip} 'curl -k -s -X PUT -d \"{{\\\"state\\\":2}}\" {ohv_ip}:8080/lvm/Datastore/{ds_idn}/VDisk/{dsk_idn}' 2>/dev/null".format(
                ocp_ip=ONAPP_CP_HOST, ossh_port=ONAPP_SSH_PORT, sshopt=SSH_OPTS, ohv_ip=VM_OHV_IP, ds_idn=store_idn,
                dsk_idn=disk_idn)
            (rc, ou) = run_command(CMD, 0, 0)
            CMD = "ssh -t -p{ossh_port} {sshopt} root@{ohv_ip} 'scp -P{vssh_port} {sshopt} /onapp/backups/{odsk_idn}.qcow2 root@{vhv_ip}:{vdsk_path}' 2>/dev/null".format(
                ossh_port=ONAPP_SSH_PORT, ohv_ip=VM_OHV_IP, vssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhv_ip=VHI_HV_IP,
                odsk_idn=disk_idn, vdsk_path=XML_VVM_DISKS[dsk_num])
            (rc, ou) = run_command(CMD, verbosity, 1)
            dsk_num += 1
    else:
        dsk_num = 0
        for ovm_dsk in ONAPPVM_DISKS:
            store_idn = ovm_dsk['datastore_idn']
            disk_idn = ovm_dsk['disk_idn']
            CMD = "ssh -p{ossh_port} {sshopt} root@{ocp_ip} 'curl -k -s -X PUT -d \"{{\\\"state\\\":3}}\" {ohv_ip}:8080/lvm/Datastore/{stor_idn}/VDisk/{dsk_idn}' 2>/dev/null".format(
                ocp_ip=ONAPP_CP_HOST, ossh_port=ONAPP_SSH_PORT, sshopt=SSH_OPTS, ohv_ip=VM_OHV_IP, stor_idn=store_idn,
                dsk_idn=disk_idn)
            (rc, ou) = run_command(CMD, 0, 0)
            CMD = "ssh -p{ossh_port} {sshopt} root@{ohv_ip} 'for port in {{2048..2064}}; do nbd=`qemu-nbd -f -t --nocache --aio=native -p $port -f raw /dev/{ostor_idn}/{odsk_idn} --fork 2>&1` ; res=$? ; if [[ $res == 0 ]] && [[ $nbd == \"\" ]]; then echo $port; break; else port=$((port+1)); fi ; done' 2>/dev/null ".format(
                ossh_port=ONAPP_SSH_PORT, sshopt=SSH_OPTS, ohv_ip=VM_OHV_IP, ostor_idn=store_idn, odsk_idn=disk_idn)
            (rc, ou) = run_command(CMD, verbosity, 0)
            nbd_port = str(ou).strip().encode('ascii')
            CMD = "ssh -t -p{vssh_port} {sshopt} root@{vhv_ip} 'qemu-img convert -p -n -t directsync -o cluster_size=1048576,lazy_refcounts=on {sp_opt} nbd://{ohv_ip}:{nbdport} -O qcow2 {vdsk_path}' 2>/dev/null".format(
                vssh_port=VHI_SSH_PORT, sshopt=SSH_OPTS, vhv_ip=VHI_HV_IP, ohv_ip=VM_OHV_IP, nbdport=nbd_port,
                vdsk_path=XML_VVM_DISKS[dsk_num], sp_opt=sparse_opt)
            (rc, ou) = run_command(CMD, verbosity, 1)
            dsk_num += 1


# --vm_migrated--#

cli.add_command(vm)
