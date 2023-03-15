import os
import click

from click_default_group import DefaultGroup
from inc.helper import Helper
from cfg.config_parser import VHI_CREDS
from inc.vhi_ssh_keys import VhiSshKeys
from inc.vhi_helpers import Vhi
from inc.utils import generate_random_password
from inc.logger import logs
from inc.onapp_helpers import (
    get_user_data,
    get_all_virtual_machines,
    get_bucket_limits,
    get_user_ssh_keys,
    check_user_role,
    VmHandler
)


@click.group(cls=DefaultGroup, default='migrate-all', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


DEFAULT_ONAPP_USER_NAMES = ('system_owner', 'cloud_locations_manager')


@click.command()
@click.option('--user', default='', help="OnApp User, VM identifier.")
@click.option('--network', default='', help="Network to be used")
@click.option('--vm', default='', help="VM to be migrated")
def migrate_all(user='', network='', vm=''):
    """
    Migrate all resources from OnApp to VHI:
        - OnApp Users to VHI users
        - OnApp User ssh keys to VHI ssh keys
        - OnApp User Roles to VHI User Roles
        - OnApp User Access Controls to VHI Project Quotas
        - OnApp VM CPU, RAM, Data Store to VHI Flavors
        - OnApp User VM's to VHI VM's

        Step 1:
            Collect needed information from OnApp side
        Step 2:
            Parsing OnApp data
        Step 3:
            Start migration process:
                Objects(Users, Flavors, Projects)
            3.1 Verify whether object exists on VHI side
            3.2 Create new object on VHI side in case object doesn't exist there
        Step 4:
            Migrate User Virtual Machines depends on Booted Status and OS
        Step 5:
            Finishing script and write down logs into files
    :param user: 4
    :param network: public2
    :param vm: virtual machine identifier
    :return:
    """
    # Arrange
    logs.info(f"{Helper.EQUAL.value} VHI: Starting Migration Session {Helper.EQUAL.value}", header=True)
    _path = os.getcwd()
    _file_name = os.path.join(_path, 'migration_logs/migration')
    user_idn = ''
    if not network:
        _network = VHI_CREDS['network']
    else:
        _network = network
    if user:
        if not user.isdigit():
            logs.error("Please specify User ID as integer: --user=7")
            exit(1)
        user_idn = int(user)

    # --Step 1--#
    # --OnApp: Get User, VM's information--#
    _user_data = get_user_data('users', None, all_users=True)
    _vms_dict = get_all_virtual_machines()
    vhi_users_data = []
    for _user_info in _user_data:
        user_password = generate_random_password()
        _user = _user_info['user']
        login = _user['login']
        if user_idn:
            if user_idn != _user['id']:
                continue

        if login in DEFAULT_ONAPP_USER_NAMES:
            continue

        if '.' in login:
            login = login.replace('.', '_')

        elif 'admin' == login:
            login = 'onapp_admin'

        _vhi_user_data = {'user_email': _user['email'],
                          'id': _user['id'],
                          'first_name': _user['first_name'],
                          'last_name': _user['last_name'],
                          'password': user_password,
                          'roles': _user['roles'],
                          'user_login': f'{login}',
                          'project_name': f"project_{_user['email']}",
                          'quotas': get_bucket_limits(bucket_id=_user['bucket_id']),
                          'virtual_machines': []}
        for user_id, vms_list in _vms_dict.items():
            if _vhi_user_data['id'] != user_id:
                continue

            _vhi_user_data['virtual_machines'] = vms_list
        vhi_users_data.append(_vhi_user_data)
    # --Step 2--#
    # --OnApp: Start migration user by user--#
    for user in vhi_users_data:
        _ssh_result = False
        _default_project = True
        full_name = f"{user['first_name']} { user['last_name']}"
        msg = 'Login: "{}"\nPassword: "{}"\nSSH Keys Migrated: {}\nMIGRATED VIRTUAL MACHINES:\n{}'
        vhi = Vhi()
        vhi.check_default_project()
        # Here we create service user for specified domain in cfg/config.cfg
        service_user = vhi.create_service_user()
        if not service_user:
            logs.info('Stopped migration process due to above failure.')
            continue

        logs.info("\n\n")

        # --Step 3--#
        # --OnApp: Start migration USER by USER--#
        logs.info(f"{Helper.EQUAL.value} VHI: Migrate User ({full_name}) --", separator=True)
        if not check_user_role(user):
            vhi.create_object(user, 'project')
            _default_project = False
        _user_result = vhi.create_object(user, 'user')
        if not _user_result:
            user['password'] = vhi.update_user_password(user_login=user['user_login'])

        _ssh_key = VhiSshKeys(user_obj=user, ssh_keys=get_user_ssh_keys(user), default_project=_default_project)
        _ssh_result = _ssh_key.create_vhi_ssh_keys()

        # --Step 4 -- #
        # -- VHI: Migrate Users Virtual Machines depends on their OS and BOOTED status -- #
        vm_msg = ""
        for _num, _vm in enumerate(user['virtual_machines']):
            _vm_number = _num+1 if not vm else 1
            vh = VmHandler(**_vm)
            _idn = _vm['id']
            # Here script try to find specified Virtual Machine and migrate only it
            if vm and vm != _idn:
                continue

            _vm_info = f'{_idn}|{_vm["ip_addr"]}|{_vm["label"]}'
            logs.info(f"{Helper.SPACES.value}-- VHI: Migrate VM #{_num} IDENTIFIER [{_vm_info}]--", header=True)
            bootloader_drivers, vm_migrate = vh.vm_handler()
            if not bootloader_drivers and not vm_migrate:
                logs.error('Access to online VM is denied. Possible reason - No SSH key on VM')
                msg_failed = (f'SSH PORT "22" is not opened for VM ID: {_idn} | IP: {_vm["ip_addr"]}\n'
                              f'Please install GRUB/WIN_DRIVERS via these options:'
                              f' "install_bootloader_offline --vm=\'identifier\'" |'
                              f' "install_win_drivers_offline --vm=\'identifier\'"')
                logs.write_log(file_path=f"{_file_name}_user_{user['id']}_manual_migrate_vm",
                               msg=msg_failed)
                continue

            result = bootloader_drivers(idn=_idn)
            if not result:
                vm_msg += (f'\t{_vm_number}. VM Migrated = {result}\n'
                           f'\t\t- IP "{_vm["ip_addr"]}"\n'
                           f'\t\t- Hostname: "{_vm["hostname"]}"\n'
                           f'\t\t- Label: "{_vm["label"]}"\n'
                           f'\t\t- Identifier: "{_idn}"\n'
                           f'\t- - - - - - - - - - - - - - - - -\n')
                logs.write_log(file_path=f"{_file_name}_user_{user['id']}",
                               msg=msg.format(user['user_login'],
                                              user['password'],
                                              _ssh_result,
                                              vm_msg))
                continue

            result_vm = vm_migrate(idn=_idn,
                                   vproj=vhi.project_name,
                                   vdom=VHI_CREDS['vinfra_domain'],
                                   network=network,
                                   vhi_obj=vhi)

            vm_msg += (f'\t{_vm_number}. VM Migrated = {result_vm}\n'
                       f'\t\t- IP "{_vm["ip_addr"]}"\n'
                       f'\t\t- Hostname: "{_vm["hostname"]}"\n'
                       f'\t\t- Label: "{_vm["label"]}"\n'
                       f'\t\t- Identifier: "{_idn}"\n'
                       f'\t- - - - - - - - - - - - - - - - -\n')
        # --Step 5 -- #
        # -- Finish Migration Session and put down logs  -- #
        logs.write_log(file_path=f"{_file_name}_user_{user['id']}",
                       msg=msg.format(user['user_login'],
                                      user['password'],
                                      _ssh_result,
                                      vm_msg))
    logs.info(f"{Helper.EQUAL.value} VHI: Script finished successfully {Helper.EQUAL.value}", separator=True)
    logs.info("\n")


cli.add_command(migrate_all)
