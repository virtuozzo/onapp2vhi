#!/usr/bin/env python
import os
import sys

from inc.onapp_helpers import get_onapp_vm_primary_disk

plug_path = os.getcwd()
sys.path.append(plug_path)
sys.path.append(plug_path+'/cfg')
sys.path.append(plug_path+'/inc')

import click
import time
import xml.etree.ElementTree as KVMxml
from click_default_group import DefaultGroup
from cfg.o2v_config import OnAppAPICredentials, Helper
from inc.functions import run_command
import json
from inc import logs


@click.group(cls=DefaultGroup, default='vm', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn','--vm','--identifier','--vm-identifier', default='', help="OnApp VM identifier.")
@click.option('--vhip','--vhi-ip','--vhi-hypervisor-ip', default='', help="VHI destination HV IP address.")
@click.option('--verb', '-v', '--v', '--verbosity', default='', help="Verbolity level of values between 0 and 8")
#click.argument('name',default='') - not used
def vm(idn='',vhip='',verb=''):
    if not idn:
        logs.info('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        exit(17)
#    if vhip == '':
#       logs.info('You need to pass VHI hypervisor IP address through --vhi-ip=? parameter ')
#       exit(18)

    if not verb:
        verb = str(Helper.VERBOSITY.value)
    if not str(verb).isdigit():
        logs.info("Effor: '--verbosity' parameter should be a number")
        exit(11)
    if int(verb) < 0 or int(verb) > 8:
        logs.info("Effor: '--verbosity' parameter should be a number between 0 and 8")
        exit(12)
    if verb:
        verbosity = int(verb)
    else:
        verbosity = int(Helper.VERBOSITY.value)

    click.echo('...VM migration from OnApp to VHI...')

    VM_IDn = idn

#--step_1--#
#--OnApp: get source VM parameters--#
    NOTE = """ -- OnApp: get source VM parameters -- """
    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/virtual_machines.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c --arg vm_idn {vm_idn} '.[] | select(.virtual_machine.identifier==$vm_idn) | [ .virtual_machine.identifier, .virtual_machine.hypervisor_id, .virtual_machine.ip_addresses[0][\"ip_address\"][\"address\"] ] '".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, full_url=URL, vm_idn=VM_IDn)
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    VM_OHV_ID = int(json.loads(ou)[1])
    logs.info("HV_ID: " + str(VM_OHV_ID))
#--VM_OHV_ID--#

#--step_2--#
#--OnApp: get source VM hypervisor IP address --#

    NOTE = """ -- OnApp: get VM's hypervisor IP by hypervisor ID -- """

    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/hypervisors.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | select(.hypervisor.id=={hv_id}) | .hypervisor.ip_address '".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, full_url=URL, hv_id=VM_OHV_ID)
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    VM_OHV_IP=str(ou).strip("\n")

#--step_3--#
#--OnApp: get OnApp VM disk info --#
    NOTE = """ -- OnApp: get VM's disk info: -- """

    ONAPPVM_DISKS = get_onapp_vm_primary_disk(idn, verbosity)
    if verbosity > 5:
        logs.info(NOTE)
        logs.info("OnApp_VM_PRIMARY_DISK:")
        logs.info(ONAPPVM_DISKS[0]['path'])
        logs.info("")

#--ONAPPVM_DISKS--#

#--step_4--#
#--OnApp: Check if VM is running at OnApp hypervisor --#
    NOTE = """ -- OnApp: check if VM is running on Hypervisor -- """
    CMD = "ssh root@{hv_ip} 'virsh dominfo {vm_idn}'".format(hv_ip=VM_OHV_IP,vm_idn=VM_IDn)
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    if rc == 0:
        logs.info("VM IS  RUNNING.\n ")
#Save original xml and remove cdrom
        CMD = "ssh root@{hv_ip} 'virsh dumpxml {vm_idn} 2>/dev/null > /tmp/{vm_idn}.xml ; cat /tmp/{vm_idn}.xml' 2>/dev/null".format(vm_idn=VM_IDn,hv_ip=VM_OHV_IP)
        if verbosity == 0:
            (rc,ou) = run_command(CMD,0,0)
        else:
            (rc,ou) = run_command(CMD,1,0)
        VM_XML_CFG = str(ou)
        vmxml = KVMxml.fromstring(VM_XML_CFG)
        for device in vmxml.findall("devices"):
            for disk in device.findall("disk"):
                if disk.attrib['device'] == "cdrom":
                    device.remove(disk)
        xmltree = KVMxml.ElementTree(vmxml)
        xmltree.write("scripts/{}.xml".format(VM_IDn))

        CMD = "ssh root@{hv_ip} 'virsh shutdown {vm_idn}'".format(hv_ip=VM_OHV_IP,vm_idn=VM_IDn)
        (rc,ou) = run_command(CMD,verbosity,0)
        while rc != 1:
            time.sleep(10)
            CMD = "ssh root@{hv_ip} 'virsh dominfo {vm_idn}'".format(hv_ip=VM_OHV_IP,vm_idn=VM_IDn)
            (rc,ou) = run_command(CMD,verbosity,0)

#Generate recovery config xml
    tree = KVMxml.parse('scripts/recovery.xml')
    root = tree.getroot()
    for device in root.findall("devices"):
        for disk in device.findall("disk"):
            if disk.attrib['type'] == "block":
                for source in disk.findall('source'):
                    source.attrib['dev'] = ONAPPVM_DISKS[0]['path']
    tree.write('scripts/recovery.xml.mg')

    # --OnApp: Run scp--#

    NOTE = """ -- Copy scripts -- """

    CMD = "scp -r scripts  root@{hv_ip}:/onapp/tools/".format(hv_ip=VM_OHV_IP)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)

    # --step_5--#
    # --OnApp: Run sed --#

    NOTE = """ -- Correct grub config -- """

    CMD = "ssh root@{hv_ip} 'sed -i 's/identifier/{vm_idn}/g' /onapp/tools/scripts/vm_grub_install.sh && sed -i 's/identifier/{vm_idn}/g' /onapp/tools/scripts/recovery.xml.mg'".format(
        hv_ip=VM_OHV_IP, vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)

    # --step_6--#
    # --OnApp: Start VM in recovery mode --#

    NOTE = """ -- Start VM in recovery mode -- """
    CMD = "ssh root@{hv_ip} 'virsh create /onapp/tools/scripts/recovery.xml.mg'".format(hv_ip=VM_OHV_IP, vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)
    # --step_7--#
    # --OnApp: Install grub --#

    NOTE = """ -- Install grub for VM -- """
    CMD = "ssh -t -t  root@{hv_ip} sh -c -l '/onapp/tools/scripts/vm_grub_install.sh'".format(hv_ip=VM_OHV_IP, vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)

    #--step_8--#
    # --OnApp: Shutdown VM  --#

    NOTE = """ -- OnApp: shutdown VM on Hypervisor """
    CMD = "ssh root@{hv_ip} 'virsh shutdown {vm_idn}'".format(hv_ip=VM_OHV_IP, vm_idn=VM_IDn)
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    while rc != 1:
        time.sleep(10)
        CMD = "ssh root@{hv_ip} 'virsh dominfo {vm_idn}'".format(hv_ip=VM_OHV_IP,vm_idn=VM_IDn)
        (rc,ou) = run_command(CMD,verbosity,0)

    #--step_9--#
    # --OnApp: Start VM  --#
    NOTE = """ -- OnApp: Start VM -- """
    CMD = "ssh root@{hv_ip} 'virsh create /onapp/tools/scripts/{vm_idn}.xml'".format(hv_ip=VM_OHV_IP, vm_idn=VM_IDn)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)


cli.add_command(vm)
