import os
import click
from click_default_group import DefaultGroup
from inc.logger import logs
from inc.helper import Helper
from cfg.config_parser import ONAPP_CREDS
from inc.ssh_connector import ssh_run, SSH
from inc.onapp_helpers import get_vm_source_properties
from inc.utils import exit_status_code_handler


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


def vm_install_win_drivers(idn: str):
    if not idn:
        logs.error('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False

    VM_IDn = idn
    _spaces = Helper.SPACES.value
    _dri_msg = 'WIN DRIVERS ONLINE -- '
    logs.info(f'{_spaces}-- INSTALLING {_dri_msg}', header=True)
    
    # -- STEP 1 --
    logs.info(f'{_spaces}{_dri_msg}STEP #1 -- OnApp: get source VM properties --', header=True)
    _vm_properties = get_vm_source_properties(vm_idn=VM_IDn)
    _vm_hv_ip = _vm_properties['hv_ip']
    _vm_ip_addr = _vm_properties['vm_ip_addr']

    # -- STEP 2 --
    logs.info(f'{_spaces}{_dri_msg}STEP #2 -- OnApp: Check if VM is running on HYPERVISOR --', header=True)
    _hv_ssh = SSH(**{'host': _vm_hv_ip})
    exit_status, output = _hv_ssh.execute(f'virsh dominfo {VM_IDn}')
    if not exit_status:
        logs.info("VM IS RUNNING.\n ", separator=True)

    # -- STEP 3 --
    logs.info(f'{_spaces}{_dri_msg}STEP #3 -- OnApp: Upload drivers image to VM [{_vm_ip_addr}] --', header=True)

    # FILES TO COPY SHOULD BE LOCATED IN PROJECT FOLDER
    cloudbase_init = os.path.join(os.getcwd(), "CloudbaseInitSetup_Stable_x64.msi")
    vz_guest_tools = os.path.join(os.getcwd(), "vz-guest-tools-win.tar")
    logs.info(f'File path: {cloudbase_init}')
    logs.info(f'File path: {vz_guest_tools}')
    cmd = f'scp -P{ONAPP_CREDS["hv_ssh_port"]} {Helper.SCP_OPTS.value} {cloudbase_init}' \
          f' Administrator@{_vm_ip_addr}:C:/ 2>/dev/null'
    [exit_status, output] = ssh_run(cmd)
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"{bcolors.FAIL}[install_win_drivers.py | STEP 3] Something went wrong."
                    f" Couldn't transfer CloudbaseInitSetup into VM \n{bcolors.ENDC}"
    ):
        return False
    cmd = f'scp -P{ONAPP_CREDS["hv_ssh_port"]} {Helper.SCP_OPTS.value}' \
          f' {vz_guest_tools} Administrator@{_vm_ip_addr}:C:/ 2>/dev/null'
    [exit_status, output] = ssh_run(cmd)
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"{bcolors.FAIL}[install_win_drivers.py | STEP 3] "
                    f"Something went wrong. Couldn't transfer vz-guest-tools-win into VM \n{bcolors.ENDC}"
    ):
        return False

    # -- STEP 4 --
    logs.info(f'{_spaces}{_dri_msg}STEP #4 -- OnApp: INSTALL DRIVERS for VM --', header=True)
    _vm_ssh = SSH(**{'host': _vm_ip_addr, 'username': 'Administrator'})
    exit_status, output = _hv_ssh.execute('cd C:; msiexec /i CloudbaseInitSetup_Stable_x64.msi /qn /l*v log.txt')
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers.py | STEP 4] installation failed `CloudbaseInitSetup_Stable_x64`\n"
                    f"Output: {output}"
    ):
        return False

    exit_status, output = _hv_ssh.execute(
        "mkdir -p 'C:/vz-guest-tools-win' tar --force-local -xf 'C:/vz-guest-tools-win.tar' -C 'C:/vz-guest-tools-win'"
        " nohup 'C:/vz-guest-tools-win/setupMain.exe' 1>/dev/null &"
    )
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers.py | STEP 4] installation failed `vz-guest-tools-win.tar`"
    ):
        return False

    return True


@click.group(cls=DefaultGroup, default='windrivers', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
def windrivers(idn=''):
    vm_install_win_drivers(idn=idn)


cli.add_command(windrivers)
