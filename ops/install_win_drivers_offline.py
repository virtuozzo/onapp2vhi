import os
import click
import time

from inc.onapp_helpers import get_onapp_vm_disks
from click_default_group import DefaultGroup
from inc.logger import logs
from inc.helper import Helper
from inc.ssh_connector import ssh_run, SSH
from inc.onapp_helpers import get_vm_source_properties
from inc.utils import exit_status_code_handler


def vm_install_win_drivers_offline(idn: str):
    if not idn:
        logs.error('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False

    VM_IDn = idn
    _spaces = Helper.SPACES.value
    _dri_msg = 'WIN DRIVERS OFFLINE -- '
    logs.info(f'{_spaces}-- INSTALLING {_dri_msg}', header=True)

    # -- STEP 1 --
    logs.info(f'{_spaces}{_dri_msg}STEP #1 -- OnApp: get source VM properties --', header=True)
    _vm_properties = get_vm_source_properties(vm_idn=VM_IDn)
    _vm_hv_ip = _vm_properties['hv_ip']

    # -- STEP 2 --
    logs.info(f"{_spaces}{_dri_msg}STEP #2 -- OnApp: Get VM primary disk info --", header=True)
    _onappvm_primary_disk = get_onapp_vm_disks(vm_idn=idn, primary=True)
    logs.info(f"OnApp VM PRIMARY DISK: {_onappvm_primary_disk}")
    ONAPPVM_DISK_MAPPER = _onappvm_primary_disk.replace("onapp-", "onapp--")
    ONAPPVM_DISK_MAPPER = ONAPPVM_DISK_MAPPER.replace("/", "-")
    ONAPPVM_DISK_MAPPER = ONAPPVM_DISK_MAPPER.replace("-dev-", "/dev/mapper/")
    ONAPPVM_DISK_PARTITION = ONAPPVM_DISK_MAPPER + 'X1'
    logs.info(f"ONAPPVM DISK MAPPER: {ONAPPVM_DISK_MAPPER}")
    logs.info(f"ONAPPVM DISK PARTITION: {ONAPPVM_DISK_PARTITION}")

    # -- STEP 3 --
    logs.info(f"{_spaces}{_dri_msg}STEP #3 -- OnApp: Check if VM is running on hypervisor --", header=True)
    _hv_ssh = SSH(**{'host': _vm_hv_ip})
    exit_status, output = _hv_ssh.execute(f'virsh dominfo {VM_IDn}')
    if not exit_status:
        logs.info("VM IS  RUNNING.\n ")
        exit_status, output = _hv_ssh.execute(f'virsh shutdown {VM_IDn}')
        while exit_status != 1:
            time.sleep(60)
            exit_status, output = _hv_ssh.execute(f'virsh dominfo {VM_IDn}')

    # -- STEP 4 --
    logs.info(f"{_spaces}{_dri_msg}STEP #4 -- OnApp: Activate VM disk --", header=True)
    exit_status, output = _hv_ssh.execute(f"lvchange -ay {_onappvm_primary_disk}")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 4] lvchange failed. Output\n\t{output}"
    ):
        return False

    # -- STEP 5 --
    logs.info(f"{_spaces}{_dri_msg}STEP #5 -- OnApp: Add partition devmappings and mount disk --", header=True)
    exit_status, output = _hv_ssh.execute(f"kpartx -av -p X {_onappvm_primary_disk}")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message="[install_win_drivers_offline.py | STEP 5] kpartx failed. Output\n\t{output}"
    ):
        return False
    exit_status, output = _hv_ssh.execute(f"mkdir -p /mnt/prepare_win; mount {ONAPPVM_DISK_PARTITION} /mnt/prepare_win")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 5]  mount {ONAPPVM_DISK_PARTITION} /mnt/prepare_win"
                    f" failed. Output\n\t{output}"
    ):
        return False

    # -- STEP 6 --
    logs.info(f"{_spaces}{_dri_msg}STEP #6 -- OnApp: Copy drivers and scripts --", header=True)

    # FILES TO COPY SHOULD BE LOCATED IN PROJECT FOLDER
    cloudbase_init = os.path.join(os.getcwd(), "CloudbaseInitSetup_Stable_x64.msi")
    vz_guest_tools = os.path.join(os.getcwd(), "vz-guest-tools-win.tar")
    logs.info(f'File path: {cloudbase_init}')
    logs.info(f'File path: {vz_guest_tools}')

    cmd = f"scp -r {vz_guest_tools} root@{_vm_hv_ip}:/mnt/prepare_win/vz-guest-tools-win.tar"
    [exit_status, output] = ssh_run(cmd)
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 6] Something went wrong. "
                    f"Couldn't transfer vz-guest-tools-win into VM. Output\n\t{output}"
    ):
        return False

    cmd = f"scp -r {cloudbase_init}  root@{_vm_hv_ip}:/mnt/prepare_win/CloudbaseInitSetup_Stable_x64.msi"
    [exit_status, output] = ssh_run(cmd)
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 6]"
                    f" Something went wrong. Couldn't transfer CloudbaseInitSetup into VM. Output\n\t{output}"
    ):
        return False

    cmd = f"scp -r scripts/onapp.bat root@{_vm_hv_ip}:/mnt/prepare_win/onapp.bat"
    [exit_status, output] = ssh_run(cmd)
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 6]"
                    f" Something went wrong. Couldn't transfer onapp.bat into VM. Output\n\t{output}"
    ):
        return False

    # -- STEP 7 --
    logs.info(f"{_spaces}{_dri_msg}STEP #7 -- OnApp: Run unmount and del partition devmappings --", header=True)
    exit_status, output = _hv_ssh.execute(f"umount {ONAPPVM_DISK_PARTITION}")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 7]"
                    f" umount {ONAPPVM_DISK_PARTITION} failed. Output\n\t{output}"
    ):
        return False

    exit_status, output = _hv_ssh.execute(f"kpartx -d -p X {_onappvm_primary_disk}")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 7] kpartx failed. Output\n\t{output}"
    ):
        return False

    return True


@click.group(cls=DefaultGroup, default='driversoffline', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
def driversoffline(idn=''):
    vm_install_win_drivers_offline(idn=idn)


cli.add_command(driversoffline)
