import click
import time

from click_default_group import DefaultGroup
from inc.helper import Helper
from inc.ssh_connector import ssh_run, SSH
from inc.logger import logs
from inc.onapp_helpers import (
    get_onapp_vm_disks,
    GenerateXmlConfig,
    activate_disk,
    deactivate_disk,
    get_vm_source_properties
)


def vm_install_bootloader_offline(idn: str):
    if not idn:
        logs.error('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False

    _spaces = Helper.SPACES.value
    _boot_msg = 'BOOTLOADER OFFLINE -- '
    logs.info(f'{_spaces}-- INSTALLING {_boot_msg}', header=True)
    vm_idn = idn
    vm_is_running = False

    # -- STEP 1 --
    logs.info(f'{_spaces}{_boot_msg}STEP #1 --OnApp: get source VM properties--', header=True)
    _vm_properties = get_vm_source_properties(vm_idn=vm_idn)
    _vm_hv_ip = _vm_properties['hv_ip']
    _vm_ip_addr = _vm_properties['vm_ip_addr']

    # -- STEP 2 --
    logs.info(f'{_spaces}{_boot_msg}STEP #2 -- OnApp: GET OnApp VM disk info --', header=True)
    _vm_primary_disk = get_onapp_vm_disks(vm_idn=idn, primary=True)
    logs.info(f"OnApp VM PRIMARY DISK: {_vm_primary_disk}")

    # -- STEP 3 --
    logs.info(f'{_spaces}{_boot_msg}STEP #3 -- OnApp: check if VM is running on Hypervisor --', header=True)
    _hv_ssh = SSH(**{'host': _vm_hv_ip})
    exit_status, output = _hv_ssh.execute(f'virsh dominfo {vm_idn}')
    xml_config = GenerateXmlConfig(vm_idn=vm_idn, hv_ip=_vm_hv_ip)
    if not exit_status:
        vm_is_running = True
        logs.info("-- OnApp: VM IS RUNNING.\n ")
        xml_config.shut_down_vm()
        logs.warn("-- OnApp: VM has been SHUT DOWN.")

    # GENERATE .xml FILE:
    xml_config.generate_recovery_xml_config(primary_disk=_vm_primary_disk)

    # -- STEP 4 --
    logs.info(f'{_spaces}{_boot_msg}STEP #4 -- Copy scripts --', header=True)
    _cmd = f"scp -r scripts root@{_vm_hv_ip}:/onapp/tools/"
    ssh_run(command=_cmd)

    # -- STEP 5 --
    logs.info(f'{_spaces}{_boot_msg}STEP #5 -- Correct grub config --', header=True)
    _hv_ssh.execute(f"sed -i 's/identifier/{vm_idn}/g' /onapp/tools/scripts/vm_grub_install.sh"
                    f" && sed -i 's/identifier/{vm_idn}/g' /onapp/tools/scripts/recovery.xml.mg")

    # -- STEP 6 --
    logs.info(f'{_spaces}{_boot_msg}STEP #6 -- OnApp: Start VM in recovery mode --', header=True)
    if not vm_is_running:
        result = activate_disk(vm_idn=vm_idn, vm_ohv_ip=_vm_hv_ip)
        if not result:
            return False

    _hv_ssh.execute("virsh create /onapp/tools/scripts/recovery.xml.mg")

    # -- STEP 7 --
    logs.info(f'{_spaces}{_boot_msg}STEP #7 -- OnApp: Install grub for VM --', header=True)
    _hv_ssh.execute("sh -c -l '/onapp/tools/scripts/vm_grub_install.sh'")

    # -- STEP 8 --
    logs.info(f'{_spaces}{_boot_msg}STEP #8 -- OnApp: Shutdown VM on Hypervisor --', header=True)

    exit_status, output = _hv_ssh.execute(f"virsh shutdown {vm_idn}")
    while exit_status != 1:
        time.sleep(10)
        exit_status, output = _hv_ssh.execute(f"virsh dominfo {vm_idn}")

    # -- STEP 9 --
    logs.info(f'{_spaces}{_boot_msg}STEP #9 -- OnApp: HV deactivating disk --', header=True)
    if not vm_is_running:
        deactivate_disk(vm_idn=vm_idn, vm_ohv_ip=_vm_hv_ip)

    # -- STEP 10 --
    if vm_is_running:
        logs.info(f'{_spaces}{_boot_msg}STEP #10 -- OnApp: Start VM --', header=True)
        _hv_ssh.execute(f"virsh create /onapp/tools/scripts/{vm_idn}.xml")
        return True

    return True


@click.group(cls=DefaultGroup, default='bootloaderoffline', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
def bootloaderoffline(idn=''):
    vm_install_bootloader_offline(idn=idn)


cli.add_command(bootloaderoffline)
