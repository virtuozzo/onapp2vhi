import os
import click
from click_default_group import DefaultGroup
from inc.logger import logs
from inc.windows_network_reconfig import WindowsNetworkReconfig
from inc.helper import Helper
from cfg.config_parser import ONAPP_CREDS
from inc.ssh_connector import ssh_run, SSH
from inc.onapp_helpers import get_vm_source_properties
from inc.utils import exit_status_code_handler


def vm_install_win_drivers(idn: str, vz_guest_tools: bool, cloud_init_install: bool):
    if not idn:
        logs.error('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False

    vm_idn = idn
    _spaces = Helper.SPACES.value
    _dri_msg = 'WIN DRIVERS ONLINE -- '
    logs.info(f'{_spaces}-- INSTALLING {_dri_msg}', header=True)

    if not cloud_init_install and not vz_guest_tools:
        logs.info(msg='Chosen nothing to install.', separator=True)
        return True
    
    # -- STEP 1 --
    logs.info(f'{_spaces}{_dri_msg}STEP #1 -- OnApp: get source VM properties --', header=True)
    _vm_properties = get_vm_source_properties(vm_idn=vm_idn)
    _vm_hv_ip = _vm_properties['hv_ip']
    _vm_ip_addr = _vm_properties['vm_ip_addr']

    # -- STEP 2 --
    logs.info(f'{_spaces}{_dri_msg}STEP #2 -- OnApp: Check if VM is running on HYPERVISOR --', header=True)
    _hv_ssh = SSH(**{'host': _vm_hv_ip})
    exit_status, output = _hv_ssh.execute(f'virsh dominfo {vm_idn}')
    if exit_status:
        logs.error("VM is NOT running!")
        return False

    logs.info("VM IS RUNNING.\n ", separator=True)

    # -- STEP 3 --
    logs.info(f'{_spaces}{_dri_msg}STEP #3 -- OnApp: Upload drivers image to VM [{_vm_ip_addr}] --', header=True)

    # FILES TO COPY SHOULD BE LOCATED IN PROJECT FOLDER
    cloudbase_init_path = os.path.join(os.getcwd(), "scripts/CloudbaseInitSetup_Stable_x64.msi")
    vz_guest_tool_path = os.path.join(os.getcwd(), "scripts/vz-guest-tools-win.tar")
    onapp_bat = os.path.join(os.getcwd(), "scripts/onapp.bat")
    logs.info(f'File path: {cloudbase_init_path}')
    logs.info(f'File path: {vz_guest_tool_path}')
    logs.info(f'File path: {onapp_bat}')

    if cloud_init_install:
        cmd = f'scp -P{ONAPP_CREDS["hv_ssh_port"]} {Helper.SCP_OPTS.value} {cloudbase_init_path}' \
              f' Administrator@{_vm_ip_addr}:C:/ 2>/dev/null'
        [exit_status, output] = ssh_run(cmd)
        if not exit_status_code_handler(
                exit_code=exit_status,
                message=f"[install_win_drivers.py | STEP 3] Something went wrong."
                        f" Couldn't transfer CloudbaseInitSetup into VM\n"
                        f"\t\tPlease download file and save into scripts/\n "
                        f"\t\thttps://cloudbase.it/downloads/CloudbaseInitSetup_Stable_x64.msi\n"
                        f"\t\tOutput: {output}"
        ):
            return False

    if vz_guest_tools:
        cmd = f'scp -P{ONAPP_CREDS["hv_ssh_port"]} {Helper.SCP_OPTS.value}' \
              f' {vz_guest_tool_path} Administrator@{_vm_ip_addr}:C:/ 2>/dev/null'
        [exit_status, output] = ssh_run(cmd)
        if not exit_status_code_handler(
                exit_code=exit_status,
                message=f"[install_win_drivers.py | STEP 3] "
                        f"Something went wrong. Couldn't transfer vz-guest-tools-win into VM\n"
                        f"\t\tPlease download file and save into scripts/\n "
                        f"\t\thttp://downloads.repo.onapp.com/vz-guest-tools-win.tar\n"
                        f"\t\tOutput: {output}"
        ):
            return False

    # -- STEP 4 --
    logs.info(f'{_spaces}{_dri_msg}STEP #4 -- OnApp: Creating File to Rebuild'
              f' Windows Networks for VM[IP:{_vm_ip_addr}|ID: {vm_idn}] --', header=True)
    windows_reconfig = WindowsNetworkReconfig(vm_identifier=vm_idn)
    result = windows_reconfig.create_file()
    if not result:
        return False

    cmd = f'scp -P{ONAPP_CREDS["hv_ssh_port"]} {Helper.SCP_OPTS.value} {windows_reconfig.file}' \
          f' Administrator@{_vm_ip_addr}:C:/vhi_rebuild_network.bat 2>/dev/null'
    [exit_status, output] = ssh_run(cmd)
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers.py | STEP 4] Something went wrong."
                    f" Couldn't transfer {windows_reconfig.file} into VM\n"
                    f"\t\tOutput: {output}"
    ):
        return False

    cmd = f'scp -P{ONAPP_CREDS["hv_ssh_port"]} {Helper.SCP_OPTS.value} {onapp_bat}' \
          f' Administrator@{_vm_ip_addr}:C:/onapp.bat 2>/dev/null'
    [exit_status, output] = ssh_run(cmd)
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers.py | STEP 4]"
                    f" Something went wrong. Couldn't transfer onapp.bat into VM.\n"
                    f"\t\tOutput: {output}"
    ):
        return False

    # -- STEP 5 --
    logs.info(f'{_spaces}{_dri_msg}STEP #5 -- OnApp: INSTALL DRIVERS for VM[IP:{_vm_ip_addr}] --', header=True)
    _vm_ssh = SSH(**{'host': _vm_ip_addr, 'username': 'Administrator'})
    _vm_ssh.connect_timeout = 20
    _vm_ssh.channel_timeout = 20
    if cloud_init_install:
        exit_status, output = _vm_ssh.execute('cd C:; msiexec /i CloudbaseInitSetup_Stable_x64.msi /qn /l*v log.txt')
        if not exit_status_code_handler(
                exit_code=exit_status,
                message=f"[install_win_drivers.py | STEP 5] installation failed `CloudbaseInitSetup_Stable_x64`\n"
                        f"Output: {output}"
        ):
            return False

    if vz_guest_tools:
        exit_status, output = _vm_ssh.execute(
            "mkdir -p 'C:/vz-guest-tools-win'; "
            "tar --force-local -xf 'C:/vz-guest-tools-win.tar' -C 'C:/vz-guest-tools-win'; "
            "nohup 'C:/vz-guest-tools-win/setupMain.exe' 1>/dev/null &"
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
@click.option('--vz_guest_tools', default=True, help="Boolean flag, set `false` to NOT install vz_guest_tools")
@click.option('--cloud_init_install', default=True, help="Boolean flag, set `false` to NOT install cloud_init_install")
def windrivers(idn='', vz_guest_tools=True, cloud_init_install=True):
    vm_install_win_drivers(idn=idn, vz_guest_tools=vz_guest_tools, cloud_init_install=cloud_init_install)


cli.add_command(windrivers)
