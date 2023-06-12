import os
import time

from onapp2vhi.inc.onapp_helpers import get_onapp_vm_disks
from onapp2vhi.utilities.logs.logger import OnAppVHILogger
from onapp2vhi.inc.helper import Helper
from onapp2vhi.inc.ssh_connector import ssh_run, SSH
from onapp2vhi.inc.utils import exit_status_code_handler
from onapp2vhi.inc.windows_network_reconfig import WindowsNetworkReconfig
from onapp2vhi.inc.onapp_helpers import (
    get_disk_type,
    activate_disk,
    deactivate_disk
)
from onapp2vhi.utilities.web import download_file
from onapp2vhi.utilities.config import OnApp2VHIConfig

logs = OnAppVHILogger()


def vm_install_win_drivers_offline(cfg: OnApp2VHIConfig, idn: str, vz_guest_tools: bool, cloud_init_install, vm_properties: dict):
    if not idn:
        logs.error('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False

    vm_idn = idn
    _spaces = Helper.SPACES.value
    _dri_msg = 'WIN DRIVERS OFFLINE -- '
    logs.info(f'{_spaces}-- INSTALLING {_dri_msg}', header=True)

    # -- STEP 1 --
    logs.info(f'{_spaces}{_dri_msg}STEP #1 -- OnApp: get source VM properties --', header=True)
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

    package_path = os.path.dirname(__file__)
    install_script = os.path.join(package_path, "scripts/onapp.bat_ci_vz")
    if not vz_guest_tools and _cloud_init:
        logs.info(msg='Installing only `CLOUD INIT`', separator=True)
        install_script = os.path.join(package_path, "scripts/onapp.bat_ci")
    elif not _cloud_init and vz_guest_tools:
        logs.info(msg='Installing only `VZ GUEST TOOLS`', separator=True)
        install_script = os.path.join(package_path, "scripts/onapp.bat_vz")
    elif not _cloud_init and not vz_guest_tools:
        logs.info(msg='Chosen nothing to install.', separator=True)
        return True

    # -- STEP 2 --
    logs.info(f"{_spaces}{_dri_msg}STEP #2 -- OnApp: Get VM primary disk info --", header=True)
    _onappvm_primary_disk = get_onapp_vm_disks(cfg, vm_idn=idn, primary=True)
    logs.info(f"OnApp VM PRIMARY DISK: {_onappvm_primary_disk}")
    disk_type = get_disk_type(cfg, vm_idn=vm_idn)
    x1 = 'X1'
    if disk_type == 'lvm':
        onappvm_disk_mapper = _onappvm_primary_disk.replace("onapp-", "onapp--").replace("/", "-").replace(
            "-dev-", "/dev/mapper/"
        )
        onappvm_disk_partition = f"{onappvm_disk_mapper}{x1}"
    else:
        # Here is for Integrated Storage Disk Type
        onappvm_disk_partition = f"/dev/mapper/{_onappvm_primary_disk.split('/')[-1]}{x1}"

    logs.info(f"ONAPPVM DISK PARTITION: {onappvm_disk_partition}")

    # -- STEP 3 --
    logs.info(f"{_spaces}{_dri_msg}STEP #3 -- OnApp: Check if VM is running on hypervisor --", header=True)
    _hv_ssh = SSH(**{'host': _vm_hv_ip, 'ssh_key': cfg.ssh_key})
    exit_status, output = _hv_ssh.execute(f'virsh dominfo {vm_idn}')
    if not exit_status:
        logs.info("VM IS RUNNING.\n ")
        exit_status, output = _hv_ssh.execute(f'virsh shutdown {vm_idn}')
        while exit_status != 1:
            time.sleep(60)
            exit_status, output = _hv_ssh.execute(f'virsh dominfo {vm_idn}')

    # -- STEP 4 --
    logs.info(f"{_spaces}{_dri_msg}STEP #4 -- OnApp: Activate VM disk --", header=True)
    if not activate_disk(cfg, vm_idn=vm_idn, vm_ohv_ip=_vm_hv_ip):
        logs.error('Disk ACTIVATION failed.')
        return False

    # -- STEP 5 --
    logs.info(f"{_spaces}{_dri_msg}STEP #5 -- OnApp: Add partition devmappings and mount disk --", header=True)
    exit_status, output = _hv_ssh.execute(f"kpartx -av -p X {_onappvm_primary_disk}")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 5] kpartx failed. Output\n\t{output}"
    ):
        return False
    exit_status, output = _hv_ssh.execute(
        f"mkdir -p /mnt/{vm_idn}; mount -t ntfs-3g {onappvm_disk_partition} /mnt/{vm_idn}"
    )
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 5]  mount -t ntfs-3g "
                    f"{onappvm_disk_partition} /mnt/{vm_idn} failed. Output\n\t{output}"
    ):
        return False

    # -- STEP 6 --
    logs.info(f"{_spaces}{_dri_msg}STEP #6 -- OnApp: Copy drivers and scripts --", header=True)

    # FILES TO COPY SHOULD BE LOCATED IN PROJECT FOLDER /scripts
    cloudbase_init_path = os.path.join(package_path, "scripts/CloudbaseInitSetup_Stable_x64.msi")
    vz_guest_tool_path = os.path.join(package_path, "scripts/vz-guest-tools-win.tar")
    logs.info(f'File path: {cloudbase_init_path}')
    logs.info(f'File path: {vz_guest_tool_path}')

    if not os.path.exists(vz_guest_tool_path):
        download_file("http://downloads.repo.onapp.com/vz-guest-tools-win.tar",
                      os.path.join(package_path, "scripts"))

    if vz_guest_tools:
        cmd = f"scp -r {vz_guest_tool_path} root@{_vm_hv_ip}:/mnt/{vm_idn}/vz-guest-tools-win.tar"
        [exit_status, output] = ssh_run(cmd)
        if not exit_status_code_handler(
                exit_code=exit_status,
                message=f"[install_win_drivers_offline.py | STEP 6] Something went wrong. "
                        f"Couldn't transfer vz-guest-tools-win into VM. Output\n\t{output}"
        ):
            return False

    if not os.path.exists(cloudbase_init_path):
        download_file("https://cloudbase.it/downloads/CloudbaseInitSetup_Stable_x64.msi",
                      os.path.join(package_path, "scripts"))

    if _cloud_init:
        cmd = f"scp -r {cloudbase_init_path}  root@{_vm_hv_ip}:/mnt/{vm_idn}/CloudbaseInitSetup_Stable_x64.msi"
        [exit_status, output] = ssh_run(cmd)
        if not exit_status_code_handler(
                exit_code=exit_status,
                message=f"[install_win_drivers_offline.py | STEP 6]"
                        f" Something went wrong. Couldn't transfer CloudbaseInitSetup into VM\n"
                        f"\t\tPlease download file and save into scripts/\n "
                        f"\t\thttps://cloudbase.it/downloads/CloudbaseInitSetup_Stable_x64.msi\n"
                        f"\t\tOutput: {output}"
        ):
            return False

    cmd = f"scp -r {install_script} root@{_vm_hv_ip}:/mnt/{vm_idn}/onapp.bat"
    [exit_status, output] = ssh_run(cmd)
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 6]"
                    f" Something went wrong. Couldn't transfer onapp.bat into VM.\n"
                    f"\t\tPlease download file and save into scripts/\n "
                    f"\t\thttp://downloads.repo.onapp.com/vz-guest-tools-win.tar\n"
                    f"\t\tOutput: {output}"
    ):
        return False

    # -- STEP 7 --
    logs.info(f'{_spaces}{_dri_msg}STEP #7 -- OnApp: Creating File to Rebuild'
              f' Windows Networks for VM[IP:{_vm_ip_addr}|ID: {vm_idn}] --', header=True)
    windows_reconfig = WindowsNetworkReconfig(cfg, vm_identifier=vm_idn)
    result = windows_reconfig.create_file()
    if not result:
        return False

    cmd = f"scp -r {windows_reconfig.file} root@{_vm_hv_ip}:/mnt/{vm_idn}/vhi_rebuild_network.bat"
    [exit_status, output] = ssh_run(cmd)
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers.py | STEP 7] Something went wrong."
                    f" Couldn't transfer {windows_reconfig.file} into VM\n"
                    f"\t\tOutput: {output}"
    ):
        return False

    # -- STEP 8 --
    logs.info(f"{_spaces}{_dri_msg}STEP #8 -- OnApp: Run unmount and del partition devmappings --", header=True)
    exit_status, output = _hv_ssh.execute(f"umount {onappvm_disk_partition}")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 8]"
                    f" umount {onappvm_disk_partition} failed. Output\n\t{output}"
    ):
        return False

    exit_status, output = _hv_ssh.execute(f"rmdir /mnt/{vm_idn}")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 7]"
                    f" rmdir /mnt/{vm_idn}failed. Output\n\t{output}"
    ):
        return False

    exit_status, output = _hv_ssh.execute(f"kpartx -d -p X {_onappvm_primary_disk}")
    if not exit_status_code_handler(
            exit_code=exit_status,
            message=f"[install_win_drivers_offline.py | STEP 7] kpartx failed. Output\n\t{output}"
    ):
        return False

    if not deactivate_disk(cfg, vm_idn=vm_idn, vm_ohv_ip=_vm_hv_ip):
        logs.error('Disk DEACTIVATION failed.')
        return False

    return True
