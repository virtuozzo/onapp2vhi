import os

from inc.helper import Helper
from inc.vhi_ssh_keys import VhiSshKeys
from inc.vhi_helpers import Vhi
from inc.logger import logs
from inc.onapp_helpers import (
    prepare_vhi_migration_data,
    get_user_ssh_keys,
    check_user_role,
    VmHandler
)
from onapp2vhi.utility.config import OnApp2VHIConfig

cfg = OnApp2VHIConfig()


def migrate_all_impl(user='', network='', vm='', project=''):
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
    :param project: project
    :return:
    """
    # Arrange
    logs.info(f"{Helper.EQUAL.value} VHI: Starting Migration Session {Helper.EQUAL.value}", header=True)
    _path = os.getcwd()
    _file_name = os.path.join(_path, 'migration_logs/migration')
    user_idn = ''
    if not network:
        _network = cfg.vhi_conf['network']
    else:
        _network = network
    if user:
        if not user.isdigit():
            logs.error("Please specify User ID as integer: --user=7")
            exit(1)
        user_idn = int(user)
    _custom_project = project
    # --Step 1--#
    # --OnApp: Get User, VM's information--#
    vhi_users_data = prepare_vhi_migration_data(user_idn=user_idn)
    if not vhi_users_data:
        logs.error(msg='Collecting user data failed. Please take a look into logs.')
        return False

    # Here we create service user for specified domain in cfg/config.cfg
    Vhi().clean_up_cache()
    service_user = Vhi().create_service_user()
    if not service_user:
        logs.info('Stopped migration process due to above failure.')

    logs.info("\n\n")

    # --Step 2--#
    # --OnApp: Start migration user by user--#
    for user in vhi_users_data:
        _ssh_result = False
        full_name = f"{user['first_name']} { user['last_name']}"
        msg = 'Login: "{}"\nPassword: "{}"\nSSH Keys Migrated: {}\nMIGRATED VIRTUAL MACHINES:\n{}'
        vhi = Vhi()

        # --Step 3--#
        # --OnApp: Start migration USER by USER--#
        logs.info(f"{Helper.EQUAL.value} VHI: Migrate User ({full_name}) --", separator=True)
        # If we specified custom project via --project=my_project, then creation projects step will be missed
        if not _custom_project:
            if not check_user_role(user):
                result = vhi.create_project(user_data=user)
                if not result:
                    continue
                user.update({"project_name": vhi.project_name})
            else:
                _default_project = vhi.check_default_project()
                if not _default_project:
                    continue
                user.update({"project_name": vhi.project_name})
        else:
            logs.warn(msg=f'You have specified CUSTOM Project name [{_custom_project}]'
                          f' please be ensure such project exist on VHI side in Domain. Otherwise command will fail!')
            user.update({"project_name": _custom_project})

        result, user_pwd = vhi.create_user(user_data=user)
        if not result:
            continue

        user.update({'password': user_pwd})
        _ssh_key = VhiSshKeys(user_obj=user, ssh_keys=get_user_ssh_keys(user))
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
                                   vdom=cfg.vhi_conf['vinfra_domain'],
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
