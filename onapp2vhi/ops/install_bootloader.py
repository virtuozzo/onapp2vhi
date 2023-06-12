from onapp2vhi.utilities.logs.logger import OnAppVHILogger
from os.path import join, dirname, exists
from onapp2vhi.inc.helper import Helper
from onapp2vhi.inc.ssh_connector import ssh_run, SSH
from onapp2vhi.inc.utils import exit_status_code_handler
from onapp2vhi.utilities.web import download_file
from onapp2vhi.utilities.config import OnApp2VHIConfig

logs = OnAppVHILogger()


def vm_install_bootloader(cfg: OnApp2VHIConfig, idn: str, vz_guest_tools: bool, cloud_init_install, vm_properties: dict):
    VM_IDn = idn
    if not idn:
        logs.error('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False

    _spaces = Helper.SPACES.value
    _scp_opts = Helper.SCP_OPTS.value
    _boot_msg = 'BOOTLOADER ONLINE -- '
    logs.info(f'{_spaces}-- INSTALLING {_boot_msg}', header=True)

    # -- STEP 1 --
    logs.info(f'{_spaces}{_boot_msg}STEP #1 -- OnApp: get source VM properties --', header=True)
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
    _vm_ssh = SSH(**{'host': _vm_ip_addr, 'connect_timeout': 10, 'channel_timeout': 10, 'ssh_key': cfg.ssh_key})
    logs.info(f'{_spaces}{_boot_msg}STEP #2 -- OnApp: Check if VM is running at OnApp hypervisor --', header=True)
    _hv_ssh = SSH(**{'host': _vm_hv_ip, 'ssh_key': cfg.ssh_key})
    exit_status, output = _hv_ssh.execute(f'virsh list | grep {VM_IDn}')
    if not 'running' and VM_IDn in output:
        logs.warn(f'VM {VM_IDn} is not running on the HV side. Please turn it ON and restart script.')
        return False

    # -- STEP 3 --
    logs.info(f'{_spaces}{_boot_msg}STEP #3 -- OnApp: Copy cloud-install into VM [{VM_IDn}] --', header=True)
    package_path = dirname(__file__)
    scripts_info = {
        join(package_path, 'scripts/cron-cloud-install'): '/etc/cron.d/cron-cloud-install',
        join(package_path, 'scripts/cloud-install'): '/usr/bin/cloud-install',
        join(package_path, 'scripts/vz-guest-tools-lin.tar'): '/opt/vz-guest-tools-lin.tar',
        join(package_path, 'scripts/vz-guest-tools'): '/usr/bin/vz-guest-tools',
        join(package_path, 'scripts/PrepareVM.sh'): '/opt/PrepareVM.sh'
    }
    if not vz_guest_tools:
        del scripts_info[join(package_path, 'scripts/vz-guest-tools-lin.tar')]
        del scripts_info[join(package_path, 'scripts/vz-guest-tools')]
    if not _cloud_init:
        del scripts_info[join(package_path, 'scripts/cloud-install')]
        del scripts_info[join(package_path, 'scripts/cron-cloud-install')]

    # check guess tools downloaded
    linux_guest_tools_source_path = join(package_path, 'scripts/vz-guest-tools-lin.tar')
    if not exists(linux_guest_tools_source_path):
        download_file('http://downloads.repo.onapp.com/vz-guest-tools-lin.tar',
                      join(package_path, 'scripts'))

    for file, path in scripts_info.items():
        [exit_status, output] = ssh_run(
            command=f'scp {_scp_opts} {file} root@{_vm_ip_addr}:{path}'
        )
        if not exit_status_code_handler(
                exit_code=exit_status,
                message=f'[install_bootloader.py | STEP 3] Copy {file} failed.'
                        f'Please download next file:\n'
                        f'\t\thttp://downloads.repo.onapp.com/vz-guest-tools-lin.tar'
                        f' Output:\n\t{output}'
        ):
            return False

    # -- STEP 4 --
    if vz_guest_tools:
        logs.info(f'{_spaces}{_boot_msg}STEP #4 -- OnApp: Install `vz-guest-tools` inside VM [{VM_IDn}] --',
                  header=True)
        _vm_ssh.connect_timeout = 10
        _vm_ssh.channel_timeout = 10
        exit_status, output = _vm_ssh.execute("nohup bash /usr/bin/vz-guest-tools 1>/var/log/vz-guest-tools.log 2>&1")

        # NOTE: here we removed validation for `vz-guest-tools` failure
        exit_status_code_handler(
            exit_code=exit_status,
            message=f'[install_bootloader.py | STEP 4] Install vz-guest-tools inside VM failed. Output:\n\t{output}'
        )

    # -- STEP 5 --
    logs.info(f'{_spaces}{_boot_msg}STEP #5 -- OnApp: Install `PrepareVM.sh` inside VM [{VM_IDn}] --', header=True)
    exit_status, output = _vm_ssh.execute("bash /opt/PrepareVM.sh 1>/var/log/PrepareVM.log 2>&1")
    exit_status_code_handler(
        exit_code=exit_status,
        message=f'[install_bootloader.py | STEP 5] Install `PrepareVM.sh` inside VM failed. Output:\n\t{output}'
    )

    return True
