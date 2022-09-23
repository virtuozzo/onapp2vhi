#!/usr/bin/env python
import click
import time
import json

from click_default_group import DefaultGroup
from cfg.o2v_config import OnAppAPICredentials, Helper
from inc.functions import run_command
from inc.logger import logs
from inc.onapp_helpers import (
    get_onapp_vm_primary_disk,
    GenerateXmlConfig,
    activate_disk,
    deactivate_disk
)


def vm_install_bootloader_offline(idn, vhip, verb):
    if not idn:
        logs.info('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        exit(17)
    #    if vhip == '':
    #       logs.info('You need to pass VHI hypervisor IP address through --vhi-ip=? parameter ')
    #       exit(18)

    if not verb:
        verb = str(Helper.VERBOSITY.value)
    if not str(verb).isdigit():
        logs.error("'--verbosity' parameter should be a number")
        exit(11)
    if int(verb) < 0 or int(verb) > 8:
        logs.error("'--verbosity' parameter should be a number between 0 and 8")
        exit(12)
    if verb:
        verbosity = int(verb)
    else:
        verbosity = int(Helper.VERBOSITY.value)

    vm_idn = idn
    vm_is_running = False
    # --step_1--#
    # --OnApp: get source VM parameters--#
    NOTE = """ -- OnApp: get source VM parameters -- """
    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/virtual_machines.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c --arg vm_idn {vm_idn} '.[] | select(.virtual_machine.identifier==$vm_idn) | [ .virtual_machine.identifier, .virtual_machine.hypervisor_id, .virtual_machine.ip_addresses[0][\"ip_address\"][\"address\"] ] '".format(
        user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value,
        full_url=URL, vm_idn=vm_idn)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    VM_OHV_ID = int(json.loads(ou)[1])
    logs.info("HV_ID: " + str(VM_OHV_ID))
    # --VM_OHV_ID--#

    # --step_2--#
    # --OnApp: get source VM hypervisor IP address --#

    NOTE = """ -- OnApp: get VM's hypervisor IP by hypervisor ID -- """
    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/hypervisors.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | select(.hypervisor.id=={hv_id}) | .hypervisor.ip_address '".format(
        user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value,
        full_url=URL, hv_id=VM_OHV_ID)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    # OnApp Hypervisor IP
    vm_ohv_ip = ou.strip("\n")

    # --step_3--#
    # --OnApp: get OnApp VM disk info --#
    # --ONAPPVM_DISKS--#
    ONAPPVM_DISKS = get_onapp_vm_primary_disk(idn, verbosity)
    logs.info(""" -- OnApp: get VM's disk info: -- """)
    logs.info("OnApp_VM_PRIMARY_DISK: {}".format(ONAPPVM_DISKS[0]['path']))

    # --step_4--#
    # --OnApp: Check if VM is running at OnApp hypervisor --#
    NOTE = " -- OnApp: check if VM is running on Hypervisor -- "
    CMD = "ssh root@{hv_ip} 'virsh dominfo {vm_idn}'".format(hv_ip=vm_ohv_ip, vm_idn=vm_idn)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    xml_config = GenerateXmlConfig(vm_idn=vm_idn, hv_ip=vm_ohv_ip)
    if not rc:
        vm_is_running = True
        logs.info("VM IS  RUNNING.\n ")
        xml_config.shut_down_vm()
        logs.warn("VM has been SHUT DOWN.")

    # GENERATE .xml FILE:
    xml_config.generate_recovery_xml_config(primary_disk=ONAPPVM_DISKS[0]['path'])

    # --OnApp: Run scp--#
    NOTE = " -- Copy scripts -- "
    CMD = "scp -r scripts root@{hv_ip}:/onapp/tools/".format(hv_ip=vm_ohv_ip)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)

    # --step_5--#
    # --OnApp: Run sed --#

    NOTE = """ -- Correct grub config -- """

    CMD = "ssh root@{hv_ip} 'sed -i 's/identifier/{vm_idn}/g' /onapp/tools/scripts/vm_grub_install.sh && sed -i 's/identifier/{vm_idn}/g' /onapp/tools/scripts/recovery.xml.mg'".format(
        hv_ip=vm_ohv_ip, vm_idn=vm_idn)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)

    # --step_6--#
    # --OnApp: Start VM in recovery mode --#
    #
    if not vm_is_running:
        activate_disk(vm_idn=vm_idn, vm_ohv_ip=vm_ohv_ip)
    NOTE = """ -- Start VM in recovery mode -- """
    CMD = "ssh root@{hv_ip} 'virsh create /onapp/tools/scripts/recovery.xml.mg'".format(hv_ip=vm_ohv_ip, vm_idn=vm_idn)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    # --step_7--#
    # --OnApp: Install grub --#

    NOTE = """ -- Install grub for VM -- """
    CMD = "ssh -t -t  root@{hv_ip} sh -c -l '/onapp/tools/scripts/vm_grub_install.sh'".format(hv_ip=vm_ohv_ip,
                                                                                              vm_idn=vm_idn)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)

    # --step_8--#
    # --OnApp: Shutdown VM  --#

    NOTE = """ -- OnApp: shutdown VM on Hypervisor """
    CMD = "ssh root@{hv_ip} 'virsh shutdown {vm_idn}'".format(hv_ip=vm_ohv_ip, vm_idn=vm_idn)
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    while rc != 1:
        time.sleep(10)
        CMD = "ssh root@{hv_ip} 'virsh dominfo {vm_idn}'".format(hv_ip=vm_ohv_ip, vm_idn=vm_idn)
        (rc, ou) = run_command(CMD, verbosity, 0)

    # Deactivating disk
    if not vm_is_running:
        deactivate_disk(vm_idn=vm_idn, vm_ohv_ip=vm_ohv_ip)
    # --step_9--#
    # --OnApp: Start VM  --#
    if vm_is_running:
        NOTE = """ -- OnApp: Start VM -- """
        CMD = "ssh root@{hv_ip} 'virsh create /onapp/tools/scripts/{vm_idn}.xml'".format(hv_ip=vm_ohv_ip, vm_idn=vm_idn)
        (rc, ou) = run_command(CMD, verbosity, 0, NOTE)


@click.group(cls=DefaultGroup, default='bootloaderoffline', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn','--vm','--identifier','--vm-identifier', default='', help="OnApp VM identifier.")
@click.option('--vhip','--vhi-ip','--vhi-hypervisor-ip', default='', help="VHI destination HV IP address.")
@click.option('--verb', '-v', '--v', '--verbosity', default='', help="Verbolity level of values between 0 and 8")
def bootloaderoffline(idn='', vhip='', verb=''):
    vm_install_bootloader_offline(idn, vhip, verb)


cli.add_command(bootloaderoffline)
