import click
from inc.logger import logs
from click_default_group import DefaultGroup
from inc.helper import Helper
from inc.ssh_connector import ssh_run, SSH
from inc.onapp_helpers import get_vm_source_properties


def vm_install_bootloader(idn: str):
    VM_IDn = idn
    if not idn:
        logs.error('You need to pass OnApp VM identifier value through --vm-identifier=? parameter ')
        return False

    _spaces = Helper.SPACES.value
    _boot_msg = 'BOOTLOADER ONLINE -- '
    logs.info(f'{_spaces}-- INSTALLING {_boot_msg}', header=True)

    # -- STEP 1 --
    logs.info(f'{_spaces}{_boot_msg}STEP #1 -- OnApp: get source VM properties --', header=True)
    _vm_properties = get_vm_source_properties(vm_idn=VM_IDn)
    _vm_hv_ip = _vm_properties['hv_ip']
    _vm_ip_addr = _vm_properties['vm_ip_addr']

    # -- STEP 2 --
    logs.info(f'{_spaces}{_boot_msg}STEP #2 -- OnApp: Check if VM is running at OnApp hypervisor --', header=True)
    _hv_ssh = SSH(**{'host': _vm_hv_ip})
    exit_status, output = _hv_ssh.execute(f'virsh list | grep {VM_IDn}')
    if not 'running' and VM_IDn in output:
        logs.warn(f'VM {VM_IDn} is not running on the HV side. Please turn it ON and restart script.')
        return False

    # -- STEP 3 --
    logs.info(f'{_spaces}{_boot_msg}STEP #3 -- OnApp: GRUB_DISABLE_LINUX_UUID and GRUB_DISABLE_UUID set to false --',
              header=True)
    _vm_ssh = SSH(**{'host': _vm_ip_addr})
    _vm_ssh.execute("sed -i 's/^GRUB_DISABLE_LINUX_UUID=true/#GRUB_DISABLE_LINUX_UUID=true/' /etc/default/grub")
    _vm_ssh.execute("sed -i 's/^GRUB_DISABLE_UUID=true/#GRUB_DISABLE_UUID=true/' /etc/default/grub")

    # -- STEP 4 --
    logs.info(f'{_spaces}{_boot_msg}STEP #4 -- OnApp: INSTALL GRUB for VM --', header=True)
    _vm_ssh.execute("grub-install --recheck /dev/vda || grub2-install --recheck /dev/vda")

    # -- STEP 5 --
    logs.info(f'{_spaces}{_boot_msg}STEP #5 -- OnApp: Generate grub config for VM [{VM_IDn}] --', header=True)
    _vm_ssh.execute("grub-mkconfig -o /boot/grub/grub.cfg || grub2-mkconfig -o /boot/grub2/grub.cfg")

    # -- STEP 6 --
    logs.info(f'{_spaces}{_boot_msg}STEP #6 -- OnApp: Copy cloud-install into VM [{VM_IDn}] --', header=True)
    ssh_run(command=f'scp scripts/cron-cloud-install root@{_vm_ip_addr}:/etc/cron.d/cron-cloud-install')
    ssh_run(command=f'scp scripts/cloud-install root@{_vm_ip_addr}:/usr/bin/cloud-install')
    return True


@click.group(cls=DefaultGroup, default='installbootloader', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
def installbootloader(idn=''):
    vm_install_bootloader(idn=idn)


cli.add_command(installbootloader)
