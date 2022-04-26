#!/usr/bin/env python2

import os
import re
import sys
import xml
import json
import click
import xml.etree.ElementTree as KVMxml
from click_default_group import DefaultGroup

plug_path=os.getcwd()
#print plug_path
sys.path.append(plug_path)
sys.path.append(plug_path+'/cfg')
sys.path.append(plug_path+'/inc')

from o2v_config import *
from functions import *
from onapp_helpers import *

verbosity=8

@click.group(cls=DefaultGroup, default='vm', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass

@click.command()
@click.option('--idn','--vm','--identifier','--vm-identifier', default='', help="OnApp VM identifier.")
@click.option('--vhip','--vhi-ip','--vhi-hypervisor-ip', default='', help="VHI destination HV IP address.")
#click.argument('name',default='') - not used
def vm(idn='',vhip=''):
    if idn == '' :
       print ('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
       exit(17)
#    if vhip == '':
#       print ('You need to pass VHI hypervisor IP address through --vhi-ip=? parameter ')
#       exit(18)

    click.echo('...VM migration from OnApp to VHI...')

    VM_IDn = idn

#--step_1--#
#--OnApp: get source VM parameters--#
    print('-------')
    print("-- OnApp: get source VM parameters --")
    URL = ONAPP_CP_URL + "/virtual_machines.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -r -c --arg vm_idn {vm_idn} '.[] | select(.virtual_machine.identifier==$vm_idn) | [ .virtual_machine.identifier, .virtual_machine.hypervisor_id, .virtual_machine.ip_addresses[0][\"ip_address\"][\"address\"] ] '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL, vm_idn=VM_IDn)
    (rc,ou) = run_command(CMD,8,0)  
    OVM_IDENTIFIER = str(json.loads(ou)[0]).encode('ascii')
    OVM_HV_ID = int(json.loads(ou)[1])
#--OVM_HV_ID--#

#--step_2--#
#--OnApp: get source VM hypervisor IP address --#
    print('-------')
    print("-- OnApp: get VM's {hypervisor_ip} by {hypervisor_id} --")
    URL = ONAPP_CP_URL + "/hypervisors.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -r -c '.[] | select(.hypervisor.id=={hv_id}) | .hypervisor.ip_address '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL, hv_id=OVM_HV_ID)
    (rc,ou) = run_command(CMD,8,0)
    VM_OHV_IP=str(ou).strip("\n")
#--VM_OHV_IP--#

#--step_3--#
#--OnApp: get source VM NICs' params --#
    print('-------')
    print("-- OnApp: get VM's NICs' params --")
   
    ONAPPVM_NICS = get_onapp_vm_nics(idn,8)

    print("OnApp_VM_NICs: ")
    for nic in ONAPPVM_NICS:
       print(nic)
    print("\n")
 
#--ONAPPVM_NICS--#

#--step_4--#
#--OnApp: get OnApp VM disk info --#
    print('-------')
    print("-- OnApp: get VM's disk info --")

    ONAPPVM_DISKS = get_onapp_vm_disks(idn,8)    

    print ("OnApp_VM_DISKS:")
    for disk_data in ONAPPVM_DISKS:
       print(str(disk_data))
    print("")

#--ONAPPVM_DISKS--#

#--step_5--#
#--OnApp: Check if VM is running at OnApp hypervisor --#
    print('-------')
    print("-- OnApp: check if VM [{vm_idn}] is running on HV [{hv_ip}] --".format(vm_idn=VM_IDn,hv_ip=VM_OHV_IP))
    CMD = "ssh -p{ssh_port} root@{hv_ip} 'virsh list | grep {vm_idn}' 2>/dev/null ".format(hv_ip=VM_OHV_IP,ssh_port=ONAPP_SSH_PORT,vm_idn=VM_IDn)
    (rc,ou) = run_command(CMD,8,0)
    if ou == "":
       print("VM IS NOT RUNNING.\n PLEASE, START VM OR USE COLD-MIGRATE OPTION.")
       exit(11)

#--is_VM_Online--#


#--step_7--#
#--OnApp: get VM's XML config from OnApp hypervisor --#
    print('-------')
    print("-- OnApp: get VM's [{vm_idn}] XML config --".format(vm_idn=VM_IDn))
    print('---')
    URL = ONAPP_CP_URL + "/virtual_machines.json"
    CMD = "ssh root@{hv_ip} 'virsh dumpxml {vm_idn} > /tmp/{vm_idn}.xml && cat /tmp/{vm_idn}.xml ' 2>/dev/null ".format(hv_ip=VM_OHV_IP,vm_idn=VM_IDn)
    (rc,ou) = run_command(CMD,1,0)
    VM_XML_CFG = str(ou)
    print('---')
    print("[...result output is too big...]\n")
    if int(rc) != 0:
       print("ERROR: Can't find VM running on Hypervisor. \n" + VM_XML_CFG)
       exit()

    vmxml = KVMxml.fromstring(VM_XML_CFG)

#    print(KVMxml.tostring(vmxml))

    XML_OVM_DISKS = []
    XML_OVM_MACS = []

    for device in vmxml.findall("devices"):
       for disk in device.findall("disk"):
           if disk.attrib['device'] == "disk":
               disk_name = disk.find('target').attrib['dev']
               disk_path =  disk.find('source').attrib['dev']
               XML_OVM_DISKS.append({'name': disk_name , 'path': disk_path })
       for nic in device.findall("interface"):
           XML_OVM_MACS.append(nic.find('mac').attrib['address'])

    print("XML_OVM_DISKS: " + str(XML_OVM_DISKS) + "\n")
    print("XML_OVM_MACS: " + str(XML_OVM_MACS) + "\n")


#--step_8--#
#--OnApp: create similar VM on VHI side --#
    print('-------')
    print("-- VHI: create similar to OnApp VM [{vm_idn}] on VHI side --".format(vm_idn=VM_IDn))
    print('---')
    ONAPPVM_PRI_IP = ONAPPVM_NICS[0]['ips'][0]
    ONAPPVM_PRI_MAC = ONAPPVM_NICS[0]['mac']
    CMD = "ssh -p{ssh_port} root@{vhi_cp} 'for vmid in `vinfra service compute server list -f json | jq -r \".[] | .id \"`; do echo \"[\\\"$vmid\\\",\" `vinfra service compute server iface list --server $vmid -f json | jq -c \".[] | [ .fixed_ips, .mac_addr ]\"` \"]\" | egrep -e \"{vm_ip}|{vm_mac}\"; done' 2>/dev/null ".format(ssh_port=VHI_SSH_PORT,vhi_cp=VHI_CP_IP,vm_ip=ONAPPVM_PRI_IP,vm_mac=ONAPPVM_PRI_MAC )
    (rc,ou) = run_command(CMD,8,0)

    VHI_VM_ID = ''

    if ou == '':
        #print("LETS CREATE TARGET VM: ")
        CMD = "ssh -p{ssh_port} root@{vhi_cp} 'vinfra service compute server create onapp2vhi_vm_{vm_idn} --description 'onapp_vm_{vm_idn}' --network id=public,fixed-ip={vm_ip},mac={vm_mac},security-group={vhi_sg} --volume source=image,id={image},size={disk_size} --flavor small -f json | jq -r \".id\"' 2>/dev/null ".format(ssh_port=VHI_SSH_PORT,vhi_cp=VHI_CP_IP,vm_idn=VM_IDn,vm_ip=ONAPPVM_PRI_IP,vm_mac=ONAPPVM_PRI_MAC,vhi_sg=VHI_SG_ID,image=VHI_IMAGE,disk_size=ONAPPVM_DISKS[0]['size'])
        (rc,ou) = run_command(CMD,8,0)
        if rc == 0 and ou != '':
            VHI_VM_ID = str(ou).strip("\n")
            print( "NEW VHI VM CREATED: " + VHI_CP_URL + "/compute/servers/instances/" + VHI_VM_ID  )
            print( "...stopping target VHI VM before migration...")
            CMD = "ssh -p{ssh_port} root@{vhi_cp} 'while true; do vinfra service compute server stop {vm_id} --hard --wait --timeout 15 -f json | jq -c [.name,.id,.vm_state,.power_state,.status] ;  pwstate=\"`vinfra service compute server show {vm_id} -f json | jq -r .power_state `\" ; echo \"$pwstate\" ; if [[ \"$pwstate\" == \"SHUTDOWN\" ]]; then break; fi ; sleep 1; done' 2>/dev/null ".format(ssh_port=VHI_SSH_PORT,vhi_cp=VHI_CP_IP,vm_id=VHI_VM_ID)
            run_command(CMD,8,1)
        #---
        print('-------')
        print("-- VHI: create and attach extra VHI VM's disks --")
        print('---')
        if len(ONAPPVM_DISKS) > 1:
            for idx,dsk in enumerate(ONAPPVM_DISKS):
                if idx >= 1:
                   CMD = "ssh -p{ssh_port} root@{vhi_cp} 'vinfra service compute volume create --size {disk_size} onapp-{vm_id} --storage-policy default -f json | jq -c -r \".id\"'".format(ssh_port=VHI_SSH_PORT,vhi_cp=VHI_CP_IP,disk_size=dsk['size'],vm_id=VHI_VM_ID)
                   (rc,ou) = run_command(CMD,8,0)
                   new_disk_id = str(ou).strip().encode('ascii') 
                   CMD = "ssh -p{ssh_port} root@{vhi_cp} 'vinfra service compute server volume attach --server {vm_id} {disk_id} -f json | jq -c ' 2>/dev/null".format(ssh_port=VHI_SSH_PORT,vhi_cp=VHI_CP_IP,vm_id=VHI_VM_ID,disk_id=new_disk_id)
                   (rc,ou) = run_command(CMD,8,0)
        #---
        print('-------')
        print("-- VHI: allocate and assign extra VHI VM's IP addresses to primary NIC--")
        print('---')
        if len(ONAPPVM_NICS[0]['ips']) > 1:
           IPS_PARAMS = ''
           for ip in ONAPPVM_NICS[0]['ips']:
              IPS_PARAMS += "--fixed-ip ip-address={} ".format(ip)
           CMD = "ssh -p{ssh_port} root@{vhi_cp} 'vinfra service compute server iface list --server {vm_id} -f json | jq -c -r .[0].id' 2>/dev/null".format(ssh_port=VHI_SSH_PORT,vhi_cp=VHI_CP_IP,vm_id=VHI_VM_ID)
           (rc,ou) = run_command(CMD,8,0)
           VHI_NIC0_ID= str(ou).strip().encode('ascii')
           CMD = "ssh -p{ssh_port} root@{vhi_cp} 'vinfra service compute server iface set {ip_params} --server {vm_id} {nic_id} -f json | jq -c -r .fixed_ips' 2>/dev/null".format(ssh_port=VHI_SSH_PORT,vhi_cp=VHI_CP_IP,ip_params=IPS_PARAMS,vm_id=VHI_VM_ID,nic_id=VHI_NIC0_ID)
           (rc,ou) = run_command(CMD,8,0)
        #---
    else:
        print("Destination VHI VM with IP/MAC ALREADY EXISTS:")
        print(ou)
        VHI_VM_ID = str(json.loads(ou)[0])
        print("...please, remove the target VM on VHI or remove conflicting network interface of it...\n")
        print(VHI_CP_URL + "/compute/servers/instances/" + json.loads(ou)[0] + "/ \n")
        #exit(13) 

#--step_9--#
#--VHI: define VM's hypervisor vinfra host and disks--#
    print('-------')
    print("-- VHI: define VHI VM's hypervisor and disks --")
    print('---')
    CMD = "ssh -p{ssh_port} root@{vhi_cp} 'host `vinfra service compute server show {vm_id} -f json | jq -r .host`' | awk '/ has address /{{print $NF}}' 2>/dev/null ".format(ssh_port=VHI_SSH_PORT,vhi_cp=VHI_CP_IP,vm_id=VHI_VM_ID)
    (rc,ou) = run_command(CMD,8,0)
    if re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',ou) != None:
        VHI_HV_IP = str(ou).strip("\n")
        print("VMs_HV_IP: {}".format(VHI_HV_IP))
    else:
        print("Error: VM's VHI hypervisor IP address is invalid: {hv_ip}".format(hv_ip=ou))
        exit(23)
    CMD = "ssh -p{ssh_port} root@{vhi_hv} 'vinfra service compute server volume list --server {vm_id} -f json | jq -c' 2>/dev/null ".format(ssh_port=VHI_SSH_PORT,vhi_hv=VHI_HV_IP,vm_id=VHI_VM_ID)
    (rc,ou) = run_command(CMD,8,0)
    vhivm_disks = json.loads(str(ou)) 
    
    VHI_VM_DISKS = { str(x['device'].split('/')[2]).encode('ascii') : str(x['id']).encode('ascii') for x in vhivm_disks }

    for disk_lb,disk_id in VHI_VM_DISKS.items():
        CMD = "ssh -p{ssh_port} root@{vhi_hv} 'find /mnt/vstorage/vols/datastores/cinder/ -type f -name \"*volume-{disk_id}\"' 2>/dev/null".format(ssh_port=VHI_SSH_PORT,vhi_hv=VHI_HV_IP,disk_id=disk_id)
        (rc,ou) = run_command(CMD,8,0)
        VHI_VM_DISKS[disk_lb] = str(ou).strip().encode('ascii')

    print("VHI_VM_DISKS: {}".format(VHI_VM_DISKS))

#--step_10--#
#--VHI: define VM's hypervisor XML host and disks--#
    print('-------')
    print("-- VHI: get VHI VM XML config parameters --")
    print('---')
    CMD = "ssh -p{ssh_port} root@{vhi_hv} 'virsh dumpxml {vm_id} 2>/dev/null > /tmp/{vm_id}.xml ; cat /tmp/{vm_id}.xml' 2>/dev/null".format(ssh_port=VHI_SSH_PORT,vhi_hv=VHI_HV_IP,vm_id=VHI_VM_ID)
    (rc,ou) = run_command(CMD,1,0)
    
    VM_XML_CFG = str(ou) 
    vhixml = KVMxml.fromstring(VM_XML_CFG)

    print("---\nResult[{}]:\n".format(rc))

#    print(KVMxml.tostring(vhixml))
#    print(VM_XML_CFG)
    print('---')

    XML_VVM_DISKS = []
    XML_VVM_NICS = []
    vvm_mac = vvm_nic_id = vvm_tap = ''

    for device in vhixml.findall("devices"):
       for disk in device.findall("disk"):
           if disk.attrib['device'] == "disk":
               XML_VVM_DISKS.append(disk.find('source').attrib['file'])

       for nic in device.findall("interface"):
           vvm_mac = nic.find('mac').attrib['address' ]
           vvm_nic_id = nic.find('virtualport').find('parameters').attrib['interfaceid']
           vvm_tap = nic.find('target').attrib['dev' ]
           XML_VVM_NICS.append( { 'mac': vvm_mac, 'id': vvm_nic_id, 'tap': vvm_tap } )

    print("XML_VVM_DISKS: " + str(XML_VVM_DISKS) + "\n")
    print("XML_VVM_NICS: " + str(XML_VVM_NICS) + "\n")
    

#--step_10--#
#--OnApp: edit VM's XML config for VHI --#
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
               #device.remove(disk)
               cdrom_file = disk.find('source').attrib['file']
               disk.find('source').attrib['file'] = '/tmp/grub2.img'
               CMD = "ssh -p{ssh_port} root@{ohv_ip} 'scp -P{ssh_port} {cd_file} root@{vhv_ip}:/tmp/' ; ssh -p{ssh_port} root@{vhv_ip} 'ls /tmp/grub2*'".format(ohv_ip=VM_OHV_IP,vhv_ip=VHI_HV_IP,ssh_port=ONAPP_SSH_PORT,cd_file=cdrom_file,vm_idn=VM_IDn)
               (rc,ou) = run_command(CMD,8,0)
       nic_num = 0
       for nic in device.findall("interface"):
           if nic_num == 0:
              for src in nic.findall('source'):
                  src.attrib['bridge'] = 'br-int'
              vport = nic.findall('virtualport')
              if not vport:
                  vp = KVMxml.Element('virtualport', type='openvswitch')
                  prm = KVMxml.Element('parameters', interfaceid=XML_VVM_NICS[0]['id'])
                  vp.text = "\n\t"
                  vp.tail = "\n      "
                  prm.tail = "\n      "
                  nic.insert(2,vp)
                  vp.append(prm)
              for tgt in nic.findall('target'):
                  tgt.attrib['dev'] = XML_VVM_NICS[0]['tap']
           elif nic_num > 0:
               device.remove(nic)
           nic_num += 1
           
#    print(KVMxml.tostring(vmxml))

    xmltree = KVMxml.ElementTree(vmxml)
    xmltree.write("/tmp/{}.xml".format(OVM_IDENTIFIER))  

#--vvm_xml_created--#

#--step_11--#
#--OnApp: Upload O2V migration XML to OnApp hypervisor --#
    print('-------')
    print("-- Upload OnApp2VHI VM {vm_idn} migration XML to OnApp HV [{hv_ip}] --".format(vm_idn=VM_IDn,hv_ip=VM_OHV_IP))
    CMD = "scp -P{ssh_port} /tmp/{vm_idn}.xml root@{hv_ip}:/tmp/ ; ssh -p{ssh_port} root@{hv_ip} 'ls /tmp/{vm_idn}.xml'".format(hv_ip=VM_OHV_IP,ssh_port=ONAPP_SSH_PORT,vm_idn=VM_IDn)
    (rc,ou) = run_command(CMD,8,0)
#--xml_config_uploaded--#

#--step_12--#
#--OnApp: RUN O2V migration from OnApp to VHI hypervisor --#
    print('-------')
    print("-- Run OnApp2VHI VM {vm_idn} migration from OnApp to VHI hypervisor {hv_ip} --".format(vm_idn=VM_IDn,hv_ip=VM_OHV_IP))
    onappvm_disks = ",".join([str(dsk['name']) for dsk in XML_OVM_DISKS]) 
    CMD = "ssh -p{ossh_port} root@{ohv_ip} 'virsh migrate --live --auto-converge --unsafe --copy-storage-all --migrate-disks {vm_disks} --xml /tmp/{vm_idn}.xml --verbose {vm_idn} qemu+ssh://{vhv_ip}:{vssh_port}/system?no_verify=1 tcp:{vhv_ip} '".format(ohv_ip=VM_OHV_IP,vhv_ip=VHI_HV_IP,ossh_port=ONAPP_SSH_PORT,vssh_port=VHI_SSH_PORT,vm_disks=onappvm_disks,vm_idn=VM_IDn)
    #print(CMD)
    (rc,ou) = run_command(CMD,8,1)
#--vm_migrated--#

#--step_12--#
#--OnApp: STOP just migrated OnApp VM on VHI hypervisor --#
    print('-------')
    print("-- Stop just migrate OnApp VM {vm_idn} on VHI hypervisor {hv_ip} --".format(vm_idn=VM_IDn,hv_ip=VHI_HV_IP))
    CMD = "ssh -p{vssh_port} root@{vhi_hv} 'virsh destroy {vm_idn} '".format(vhi_hv=VHI_HV_IP,vssh_port=VHI_SSH_PORT,vm_idn=VM_IDn)
    #print(CMD)
    (rc,ou) = run_command(CMD,8,0)
#--onapp_vhi_vm_stopped--#

#--step_13--#
#--OnApp: START origina pre-created VHI VM on VHI hypervisor --#
    print('-------')
    print("-- Start original pre-created VHI VM {vhi_vm_id} on VHI hypervisor {hv_ip} --".format(vhi_vm_id=VM_IDn,hv_ip=VHI_HV_IP))
    CMD = "ssh -p{ssh_port} root@{vhi_hv} 'vinfra service compute server start {vm_id} -f json | jq -c -r \"[ .id , .power_state ]\" ' 2>/dev/null ".format(ssh_port=VHI_SSH_PORT,vhi_hv=VHI_HV_IP,vm_id=VHI_VM_ID)
    #print(CMD)
    (rc,ou) = run_command(CMD,8,0)
#--migration_finished--# 

cli.add_command(vm)


