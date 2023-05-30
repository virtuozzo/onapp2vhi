import click
import time

from inc.utils import exit_status_code_handler
from click_default_group import DefaultGroup
from inc.helper import Helper
from inc.ssh_connector import ssh_run, SSH
from inc.logger import logs
from inc.onapp_helpers import (
    get_onapp_vm_disks,
    GenerateXmlConfig,
    activate_disk,
    deactivate_disk,
)


def vm_install_bootloader_offline(idn: str, vz_guest_tools: bool, cloud_init_install, vm_properties: dict):
    if not idn:
        logs.error('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False

    _spaces = Helper.SPACES.value
    _scp_opts = Helper.SCP_OPTS.value
    _boot_msg = 'BOOTLOADER OFFLINE -- '
    logs.info(f'{_spaces}-- INSTALLING {_boot_msg}', header=True)
    vm_idn = idn
    vm_is_running = False

    # -- STEP 1 --
    logs.info(f'{_spaces}{_boot_msg}STEP #1 --OnApp: get source VM properties--', header=True)
    _vm_properties = vm_properties
    _vm_hv_ip = _vm_properties['hv_ip']
    _vm_ip_addr = _vm_properties['vm_ip_addr']
    _nics = _vm_properties['network_info']
    _user_choice = cloud_init_install['user']
    _cloud_init = True
    if _user_choice and cloud_init_install['install']:
        _cloud_init = True
    elif _user_choice and not cloud_init_install['install']:
        _cloud_init = False
    else:
        for _nic_id, _nic_addrs in _nics.items():
            if len(_nic_addrs) > 1 and not _user_choice:
                _cloud_init = False
                logs.warn(msg='The `cloud-init` will not be installed. You will need to install it manually.')
                break

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
    [exit_status, output] = ssh_run(command=f"scp {_scp_opts} -r scripts root@{_vm_hv_ip}:/onapp/tools/")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f'[install_bootloader_offline.py | STEP 4] Copy scripts failed. Output:\n\t{output}'
    ):
        return False

    # -- STEP 5 --
    logs.info(f'{_spaces}{_boot_msg}STEP #5 -- Correct grub config --', header=True)
    install_script = "/onapp/tools/scripts/vm_grub_install.sh_grub_ci_vz"
    if not vz_guest_tools and _cloud_init:
        logs.info(msg='Installing only `CLOUD INIT`', separator=True)
        install_script = "/onapp/tools/scripts/vm_grub_install.sh_grub_ci"
    elif not _cloud_init and vz_guest_tools:
        logs.info(msg='Installing only `VZ GUEST TOOLS`', separator=True)
        install_script = "/onapp/tools/scripts/vm_grub_install.sh_grub_vz"
    elif not _cloud_init and not vz_guest_tools:
        logs.info(msg='Installing only `GRUB`', separator=True)
        install_script = "/onapp/tools/scripts/vm_grub_install.sh_grub"

    _hv_ssh.execute(f"sed -i 's/identifier/{vm_idn}/g' {install_script}"
                    f" && sed -i 's/identifier/{vm_idn}/g' /onapp/tools/scripts/recovery.xml.mg")

    # -- STEP 6 --
    logs.info(f'{_spaces}{_boot_msg}STEP #6 -- OnApp: Start VM in recovery mode --', header=True)
    if not vm_is_running:
        result = activate_disk(vm_idn=vm_idn, vm_ohv_ip=_vm_hv_ip)
        if not result:
            return False

    exit_status, output = _hv_ssh.execute("virsh create /onapp/tools/scripts/recovery.xml.mg")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message='[install_bootloader_offline.py | STEP 6] Virsh create from recovery.xml failed.'
    ):
        return False

    # -- STEP 7 --
    logs.info(f'{_spaces}{_boot_msg}STEP #7 -- OnApp: Install grub for VM --', header=True)
    exit_status, output = _hv_ssh.execute(f"sh -c -l '{install_script}'")
    if not exit_status_code_handler(exit_code=exit_status,
                                    message='[install_bootloader_offline.py | STEP 7] Grub installation failed.'):
        return False

    # -- STEP 8 --
    logs.info(f'{_spaces}{_boot_msg}STEP #8 -- OnApp: Shutdown VM on Hypervisor --', header=True)

    exit_status, output = _hv_ssh.execute(f"virsh shutdown {vm_idn}")
    while exit_status != 1:
        time.sleep(10)
        exit_status, output = _hv_ssh.execute(f"virsh dominfo {vm_idn}")

    # -- STEP 9 --
    logs.info(f'{_spaces}{_boot_msg}STEP #9 -- OnApp: HV deactivating disk --', header=True)
    if not vm_is_running:
        result = deactivate_disk(vm_idn=vm_idn, vm_ohv_ip=_vm_hv_ip)
        if not result:
            return False

    # -- STEP 10 --
    if vm_is_running:
        logs.info(f'{_spaces}{_boot_msg}STEP #10 -- OnApp: Start VM --', header=True)
        exit_status, output = _hv_ssh.execute(f"virsh create /onapp/tools/scripts/{vm_idn}.xml")
        if not exit_status_code_handler(exit_code=exit_status,
                                        message='[install_bootloader_offline.py | STEP 10] Virsh create failed.'):
            return False

        return True

    return True


@click.group(cls=DefaultGroup, default='bootloaderoffline', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
@click.option('--vz_guest_tools', default=True, help="Boolean flag, set `false` to NOT install vz_guest_tools")
@click.option('--cloud_init_install', help="Option whether to install cloud-init or not")
def bootloaderoffline(idn='', vz_guest_tools=True, cloud_init_install='', vm_properties=''):
    vm_install_bootloader_offline(idn=idn,
                                  vz_guest_tools=vz_guest_tools,
                                  cloud_init_install=cloud_init_install,
                                  vm_properties=vm_properties)


cli.add_command(bootloaderoffline)
