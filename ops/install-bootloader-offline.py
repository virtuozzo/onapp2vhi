#!/usr/bin/env python

import os
import sys
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
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c --arg vm_idn {vm_idn} '.[] | select(.virtual_machine.identifier==$vm_idn) | [ .virtual_machine.identifier, .virtual_machine.hypervisor_id, .virtual_machine.ip_addresses[0][\"ip_address\"][\"address\"] ] '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL, vm_idn=VM_IDn)
    (rc,ou) = run_command(CMD,8,0)   
    VM_OHV_ID = int(json.loads(ou)[1])
    print("HV_ID: " + str(VM_OHV_ID))
#--VM_OHV_ID--#

#--step_2--#
#--OnApp: get source VM hypervisor IP address --#
    print('-------')
    print("-- OnApp: get VM's {hypervisor_ip} by {hypervisor_id} --")
    URL = ONAPP_CP_URL + "/hypervisors.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | select(.hypervisor.id=={hv_id}) | .hypervisor.ip_address '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL, hv_id=VM_OHV_ID)
    (rc,ou) = run_command(CMD,8,0)
    VM_OHV_IP=str(ou).strip("\n")
#--VM_OHV_IP--#

#--step_4--#
#--OnApp: get OnApp VM disk info --#
    print('-------')
    print("-- OnApp: get VM's disk info --")

    ONAPPVM_DISKS = get_onapp_vm_primary_disk(idn,8)    

    print ("OnApp_VM_PRIMARY_DISK:")
    print ONAPPVM_DISKS[0]['path']
    print("")

#--ONAPPVM_DISKS--#

#--step_5--#
#--OnApp: Check if VM is running at OnApp hypervisor --#
    print('-------')
    print("-- OnApp: check if VM [{vm_idn}] is running on HV [{hv_ip}] --".format(vm_idn=VM_IDn,hv_ip=VM_OHV_IP))
    URL = ONAPP_CP_URL + "/virtual_machines.json"
    CMD = "ssh root@{hv_ip} 'virsh dominfo {vm_idn}'".format(hv_ip=VM_OHV_IP,vm_idn=VM_IDn)
    (rc,ou) = run_command(CMD,8,0)
    if rc == 0:
       print("VM IS  RUNNING.\n ")
       CMD = "ssh root@{hv_ip} 'virsh shutdown {vm_idn}'".format(hv_ip=VM_OHV_IP,vm_idn=VM_IDn)
       (rc,ou) = run_command(CMD,8,0)


    tree = KVMxml.parse('scripts/recovery.xml')
    root = tree.getroot()
    for device in root.findall("devices"):
        for disk in device.findall("disk"):
            if disk.attrib['type'] == "block":
                for source in disk.findall('source'):
                    source.attrib['dev'] = ONAPPVM_DISKS[0]['path']
    tree.write('scripts/recovery.xml.mg')

    # --OnApp: Run scp--#
    print('-------')
    #    print("-- OnApp: check if VM [{vm_idn}] is running on HV [{hv_ip}] --".format(vm_idn=VM_IDn,hv_ip=VM_OHV_IP))
    CMD = "scp -r scripts  root@{hv_ip}:/onapp/tools/".format(hv_ip=VM_OHV_IP)
    (rc, ou) = run_command(CMD, 8, 0)

    # --step_5--#
    # --OnApp: Run sed --#
    print('-------')
    print("-- OnApp: check if VM [{vm_idn}] is running on HV [{hv_ip}] --".format(vm_idn=VM_IDn, hv_ip=VM_OHV_IP))
    URL = ONAPP_CP_URL + "/virtual_machines.json"
    CMD = "ssh root@{hv_ip} 'sed -i 's/identifier/{vm_idn}/g' /onapp/tools/scripts/grub_installation.sh && sed -i 's/identifier/{vm_idn}/g' /onapp/tools/scripts/recovery.xml.mg'".format(
        hv_ip=VM_OHV_IP, vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD, 8, 0)

    # --step_5--#
    # --OnApp: Start VM is recovery mode --#
    print('-------')
    print("-- OnApp: check if VM [{vm_idn}] is running on HV [{hv_ip}] --".format(vm_idn=VM_IDn, hv_ip=VM_OHV_IP))
    URL = ONAPP_CP_URL + "/virtual_machines.json"
    CMD = "ssh root@{hv_ip} 'virsh create /onapp/tools/scripts/recovery.xml.mg'".format(hv_ip=VM_OHV_IP, vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD, 8, 0)

    # --step_8--#
    # --OnApp: SInstall grub --#
    print('-------')
    print("-- OnApp: check if VM [{vm_idn}] is running on HV [{hv_ip}] --".format(vm_idn=VM_IDn, hv_ip=VM_OHV_IP))
    URL = ONAPP_CP_URL + "/virtual_machines.json"
    CMD = "ssh -t -t  root@{hv_ip} sh -c -l '/onapp/tools/scripts/grub_installation.sh'".format(hv_ip=VM_OHV_IP, vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD, 8, 0)

#--step_8--#




#--step_10--#
#--VM_XML--#

cli.add_command(vm)


