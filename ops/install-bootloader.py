#!/usr/bin/env python2

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


@click.group(cls=DefaultGroup, default='vm', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass

@click.command()
@click.option('--idn','--vm','--identifier','--vm-identifier', default='', help="OnApp VM identifier.")
@click.option('--vhip','--vhi-ip','--vhi-hypervisor-ip', default='', help="VHI destination HV IP address.")
@click.option('--verb', '-v', '--v', '--verbosity', default='', help="Verbolity level of values between 0 and 8")
#click.argument('name',default='') - not used
def vm(idn='',vhip=''):
    if idn == '' :
       print ('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
       exit(17)
#    if vhip == '':
#       print ('You need to pass VHI hypervisor IP address through --vhi-ip=? parameter ')
#       exit(18)

    if verb == '': verb = str(VERBOSITY)
    if not str(verb).isdigit():
       print("Effor: '--verbosity' parameter should be a number")
       exit(11)
    if int(verb) < 0 or int(verb) > 8:
       print("Effor: '--verbosity' parameter should be a number between 0 and 8")
       exit(12)
    if verb != '':
       verbosity = int(verb)
    else:
       verbosity = int(VERBOSITY)

    click.echo('...VM migration from OnApp to VHI...')

    VM_IDn = idn

#--step_1--#
#--OnApp: get source VM parameters--#
    
    NOTE = """ -- OnApp: get source VM parameters -- """

    URL = ONAPP_CP_URL + "/virtual_machines.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c --arg vm_idn {vm_idn} '.[] | select(.virtual_machine.identifier==$vm_idn) | [ .virtual_machine.identifier, .virtual_machine.hypervisor_id, .virtual_machine.ip_addresses[0][\"ip_address\"][\"address\"] ] '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL, vm_idn=VM_IDn)
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)   
    VM_OHV_ID = int(json.loads(ou)[1])
    print("HV_ID: " + str(VM_OHV_ID))
#--VM_OHV_ID--#

#--step_2--#
#--OnApp: get source VM hypervisor IP address --#
    
    NOTE = """ -- OnApp: get VM's {hypervisor_ip} by {hypervisor_id} -- """

    URL = ONAPP_CP_URL + "/hypervisors.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | select(.hypervisor.id=={hv_id}) | .hypervisor.ip_address '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL, hv_id=VM_OHV_ID)
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    VM_OHV_IP=str(ou).strip("\n")
#--VM_OHV_IP--#

#--step_3--#
#--OnApp: get source VM IP address --#
    
    NOTE = """ -- OnApp: get VM's {ip_address} by {identifier} -- """

    URL = ONAPP_CP_URL + "/virtual_machines/{}/ip_addresses.json".format(VM_IDn)
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[0] | .ip_address_join.ip_address.address' ".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL )
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    VM_SRC_IP=str(ou).strip("\n")
#--VM_SRC_IP--#

#--step_4--#
#--OnApp: Check if VM is running at OnApp hypervisor --#
    
    NOTE = """ -- OnApp: check if VM is running on HV -- """

    CMD = "ssh root@{hv_ip} 'virsh list | grep {vm_idn}'".format(hv_ip=VM_OHV_IP,vm_idn=VM_IDn)
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    #if vm not booted -> then EXIT
#--is_VM_Online--#

# --step_5--#
# --OnApp: GRUB_DISABLE_LINUX_UUID set to false --#
    
    NOTE = """ -- OnApp: GRUB_DISABLE_LINUX_UUID set to false for VM -- """
    
    CMD = "ssh  root@{vm_ip} -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' 'sed -i 's/^GRUB_DISABLE_LINUX_UUID=true/#GRUB_DISABLE_LINUX_UUID=true/' /etc/default/grub'".format(
        vm_ip=VM_SRC_IP)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)
    # if vm not booted -> then EXIT
    # --is_VM_Online--#

# --step_6--#
# --OnApp: GRUB_DISABLE_UUID set to false --#
    
    NOTE = """ -- OnApp: GRUB_DISABLE_UUID set to falsefor VM -- """
    
    CMD = "ssh  root@{vm_ip} -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' 'sed -i 's/^GRUB_DISABLE_UUID=true/#GRUB_DISABLE_UUID=true/' /etc/default/grub'".format(
        vm_ip=VM_SRC_IP)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)
    # if vm not booted -> then EXIT
    # --is_VM_Online--#

#--step_7--#
#--OnApp: install grub --#
    
    NOTE = """ -- OnApp: install grub for VM -- """

    CMD = "ssh root@{vm_ip} -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' 'grub-install --recheck /dev/vda || grub2-install --recheck /dev/vda'".format(vm_ip=VM_SRC_IP)
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    #if vm not booted -> then EXIT
#--is_VM_Online--#

#--step_8--#
#--OnApp: Generate grub config --#
    
    NOTE = """ -- OnApp: Generate grub config for VM [{vm_idn}] -- """

    CMD = "ssh root@{vm_ip} -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' 'grub-mkconfig -o /boot/grub/grub.cfg || grub2-mkconfig -o /boot/grub2/grub.cfg'".format(vm_ip=VM_SRC_IP)
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    #if vm not booted -> then EXIT
#--is_VM_Online--#

cli.add_command(vm)

