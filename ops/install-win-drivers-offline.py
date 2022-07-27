#!/usr/bin/env python

import os
import sys
import json
import click
import time
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
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


@click.group(cls=DefaultGroup, default='vm', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass

@click.command()
@click.option('--idn','--vm','--identifier','--vm-identifier', default='', help="OnApp VM identifier.")
@click.option('--vhip','--vhi-ip','--vhi-hypervisor-ip', default='', help="VHI destination HV IP address.")
@click.option('--verb', '-v', '--v', '--verbosity', default='', help="Verbolity level of values between 0 and 8")
#click.argument('name',default='') - not used
def vm(idn='',vhip='',verb=''):
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
    NOTE = """ -- OnApp: get VM's hypervisor IP by hypervisor ID -- """

    URL = ONAPP_CP_URL + "/hypervisors.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | select(.hypervisor.id=={hv_id}) | .hypervisor.ip_address '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL, hv_id=VM_OHV_ID)
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    VM_OHV_IP=str(ou).strip("\n")


#--step_3--#
#--OnApp: get OnApp VM primary disk info --#
    NOTE = """ -- OnApp: get VM's disk info: -- """

    ONAPPVM_PRIMARY_DISK = get_onapp_vm_primary_disk(idn,verbosity)    
    
    if verbosity > 5:
       print(NOTE)
       print("OnApp_VM_PRIMARY_DISK:")
       print(ONAPPVM_PRIMARY_DISK[0]['path'])
       print("")

    ONAPPVM_DISK_MAPPER = ONAPPVM_PRIMARY_DISK[0]['path'].replace("onapp-", "onapp--")
    ONAPPVM_DISK_MAPPER = ONAPPVM_DISK_MAPPER.replace("/", "-")
    ONAPPVM_DISK_MAPPER = ONAPPVM_DISK_MAPPER.replace("-dev-", "/dev/mapper/")
    ONAPPVM_DISK_PARTITION = ONAPPVM_DISK_MAPPER + 'X1'
    print("ONAPPVM_DISK_MAPPER:")
    print(ONAPPVM_DISK_MAPPER) 
    print("ONAPPVM_DISK_PARTITION:")
    print(ONAPPVM_DISK_PARTITION)


#--step_4--#
#--OnApp: Check if VM is running at OnApp hypervisor --#   
    NOTE = """ -- OnApp: check if VM is running on Hypervisor -- """
    
    CMD = "ssh root@{hv_ip} 'virsh dominfo {vm_idn}'".format(hv_ip=VM_OHV_IP,vm_idn=VM_IDn)
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    if rc == 0:
       print("VM IS  RUNNING.\n ")
       CMD = "ssh root@{hv_ip} 'virsh shutdown {vm_idn}'".format(hv_ip=VM_OHV_IP,vm_idn=VM_IDn)
       (rc,ou) = run_command(CMD,verbosity,0)
       while rc != 1:
           time.sleep(60)
           CMD = "ssh root@{hv_ip} 'virsh dominfo {vm_idn}'".format(hv_ip=VM_OHV_IP,vm_idn=VM_IDn)
           (rc,ou) = run_command(CMD,verbosity,0)

# --step_5--#
# --OnApp: Activate VM disk --#
    NOTE = """ -- Activate VM disk -- """

    CMD = "ssh root@{hv_ip} 'lvchange -ay {primary_disk}'".format(hv_ip=VM_OHV_IP, primary_disk=ONAPPVM_PRIMARY_DISK[0]['path'])
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)


 # --step_6--#
 # --OnApp: Add partition devmappings and mount disk --#
    NOTE = """ -- Add partition devmappings and mount disk -- """

    CMD = "ssh root@{hv_ip} 'kpartx -av -p X {primary_disk}'".format(hv_ip=VM_OHV_IP, primary_disk=ONAPPVM_PRIMARY_DISK[0]['path'])
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)
    CMD = "ssh root@{hv_ip} 'mkdir -p /mnt/prepare_win; mount {primary_disk_partition} /mnt/prepare_win'".format(hv_ip=VM_OHV_IP, primary_disk_partition=ONAPPVM_DISK_PARTITION)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)

# --step_7--#
# --OnApp: Run scp--#
    NOTE = """ -- Copy drivers and scripts -- """

    CMD = "scp -r  ~/vz-guest-tools-win.tar  root@{hv_ip}:/mnt/prepare_win/vz-guest-tools-win.tar".format(hv_ip=VM_OHV_IP)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)
    if  rc != 0:
       print (bcolors.FAIL + "Something went wrong. Couldn't transfer vz-guest-tools-win into VM \n" + bcolors.ENDC)

    CMD = "scp -r  ~/CloudbaseInitSetup_1_1_2_x64.msi  root@{hv_ip}:/mnt/prepare_win/CloudbaseInitSetup_1_1_2_x64.msi".format(hv_ip=VM_OHV_IP)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)
    if  rc != 0:
       print (bcolors.FAIL + "Something went wrong. Couldn't transfer CloudbaseInitSetup into VM \n" + bcolors.ENDC)

    CMD = "scp -r  scripts/onapp.bat  root@{hv_ip}:/mnt/prepare_win/onapp.bat".format(hv_ip=VM_OHV_IP)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)
    if  rc != 0:
       print (bcolors.FAIL + "Something went wrong. Couldn't transfer onapp.bat into VM \n" + bcolors.ENDC)

# --step_8--#
# --OnApp: Run kpartx and mount disk --#
    NOTE = """ -- Run unmount and del partition devmappings -- """

    CMD = "ssh root@{hv_ip} 'umount {primary_disk_partition} '".format(hv_ip=VM_OHV_IP, primary_disk_partition=ONAPPVM_DISK_PARTITION)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)
    CMD = "ssh root@{hv_ip} 'kpartx -d -p X {primary_disk}'".format(hv_ip=VM_OHV_IP, primary_disk=ONAPPVM_PRIMARY_DISK[0]['path'])
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)



cli.add_command(vm)


