import os

from onapp2vhi.inc.helper import Helper
from onapp2vhi.inc.vhi_ssh_keys import VhiSshKeys
from onapp2vhi.inc.vhi_helpers import Vhi
from onapp2vhi.utilities.logs.logger import OnAppVHILogger
from onapp2vhi.inc.onapp_helpers import (
    prepare_vhi_migration_data,
    get_user_ssh_keys,
    check_user_role,
    get_vm_source_properties,
    VmHandler
)
from onapp2vhi.utilities.config import OnApp2VHIConfig

logs = OnAppVHILogger()


SENTINEL = object()


def _prepare_cloud_init_msg(cloud_init_install: dict, vm_properties: dict):
    """
    Prepare appropriate message for logging whether cloud init installed or not
    :param cloud_init_install: {}
    :param vm_properties: {}
    :return:
    """
    _installed = 'Installed'
    _not_installed = 'NOT Installed'
    _user_choice = cloud_init_install['user']
    _nics = vm_properties['network_info']
    if _user_choice and cloud_init_install['install']:
        return _installed
    elif _user_choice and not cloud_init_install['install']:
        return _not_installed
    else:
        for _nic_id, _nic_addrs in _nics.items():
            if len(_nic_addrs) > 1 and not _user_choice:
                return _not_installed

        return _installed


def migrate_impl(cfg: OnApp2VHIConfig,
                 user='',
                 vm='',
                 project='',
                 vz_guest_tools_install='true',
                 cloud_init_install='',
                 placement='',
                 storage_policy='',
                 ):
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
    :param vm: virtual machine identifier
    :param project: project
    :param vz_guest_tools_install: project
    :param cloud_init_install: project
    :param placement: placement "name" or "id"
    :param storage_policy: storage_policy "name"
    :return:
    """
    # Arrange
    logs.info(f"{Helper.EQUAL.value} VHI: Starting Migration Session {Helper.EQUAL.value}", header=True)
    _pid = os.getpid()
    _file_name = ('migration_logs/{user}/migrated')
    user_idn = ''
    if user:
        if not user.isdigit():
            logs.error("Please specify User ID as integer: --user=7")
            exit(1)
        user_idn = int(user)
    vz_guest_tools = False if vz_guest_tools_install == 'false' else True
    _storage_policy = storage_policy if storage_policy else cfg.vhi_conf['vhi_storage_policy']
    if cloud_init_install is SENTINEL:
        cloud_init = {'user': False, 'install': True}
    elif cloud_init_install == 'false':
        cloud_init = {'user': True, 'install': False}
    else:
        cloud_init = {'user': True, 'install': True}
    warn_msg = ("There are no packages on this virtual machine: vz-guest-tools or/and cloud-init.\n\t"
                "In the future, we cannot guarantee the correct operation of the Virtual Machines.\n\t"
                "\tInstall these packages manually:\n"
                "\t\thttps://virtuozzo.atlassian.net/wiki/spaces/PROD/pages/2524741641/OnApp+-+VHI+Migration+space")
    if not vz_guest_tools or not cloud_init['install']:
        logs.warn(msg=warn_msg)
    _custom_project = project
    # --Step 1--#
    # --OnApp: Get User, VM's information--#
    vhi_users_data = prepare_vhi_migration_data(cfg, user_idn=user_idn, vm_idn=vm)
    if not vhi_users_data:
        logs.error(msg='Collecting user data failed. Please take a look into logs.')
        return False

    # Here we create service user for specified domain in cfg/config.cfg
    Vhi(cfg).clean_up_cache()
    service_user = Vhi(cfg).create_service_user()
    if not service_user:
        logs.info('Stopped migration process due to above failure.')

    logs.info("\n\n")

    # --Step 2--#
    # --OnApp: Start migration user by user--#
    for user in vhi_users_data:
        _ssh_result = False
        full_name = f"{user['first_name']} { user['last_name']}"
        msg = ('Login: "{}"\n'
               'Password: "{}"\n'
               'SSH Keys Migrated: {}\n'
               'MIGRATED VIRTUAL MACHINES:\n'
               '{}')
        vhi = Vhi(cfg)

        # --Step 3--#
        # --OnApp: Start migration USER by USER--#
        logs.info(f"{Helper.EQUAL.value} VHI: Migrate User ({full_name}) {Helper.EQUAL.value}", header=True)
        # If we specified custom project via --project=my_project, then creation projects step will be missed
        if not _custom_project:
            if not check_user_role(user):
                result = vhi.create_project(user_data=user)
                if not result:
                    continue
                user.update({"project_name": vhi.project_name})
                vhi.set_project_value(project_name=vhi.project_name)
            else:
                _default_project = vhi.check_default_project()
                if not _default_project:
                    continue
                user.update({"project_name": vhi.project_name})
                vhi.set_project_value(project_name=vhi.project_name)
        else:
            logs.warn(msg=f'You have specified CUSTOM Project name [{_custom_project}]'
                          f' please be ensure such project exist on VHI side in Domain. Otherwise command will fail!')
            vhi.project_name = _custom_project
            user.update({"project_name": _custom_project})
            vhi.set_project_value(project_name=vhi.project_name)

        create_user_result, user_pwd = vhi.create_user(user_data=user)
        if not create_user_result:
            continue

        user.update({'password': user_pwd})
        _ssh_key = VhiSshKeys(cfg, user_obj=user, ssh_keys=get_user_ssh_keys(cfg, user))
        _ssh_result = _ssh_key.create_vhi_ssh_keys()
        _specified_list = [_machine for _machine in vm.split(',') if _machine]

        # --Step 4 -- #
        # -- VHI: Migrate Users Virtual Machines depends on their OS and BOOTED status -- #
        vm_msg = ""
        specified_vms = 0
        for _num, _vm in enumerate(user['virtual_machines']):
            _idn = _vm['id']
            # Here script try to find specified Virtual Machine and migrate only it
            if _specified_list and _idn not in _specified_list:
                continue

            if _specified_list:
                specified_vms += 1
                _vm_number = specified_vms
            else:
                _num += 1
                _vm_number = _num
            vh = VmHandler(**_vm)
            vh.vz_guest_tools = vz_guest_tools
            vh.cloud_init = cloud_init
            _vm_info = f'{_idn}|{_vm["ip_addr"]}|{_vm["label"]}'
            if not _vm["ip_addr"]:
                logs.error(msg="Onapp VM has no primary IP, aborting migration")
                return False
            logs.info(f"{Helper.SPACES.value}-- VHI: Migrate VM #{_vm_number} IDENTIFIER [{_vm_info}]--", header=True)
            bootloader_drivers, vm_migrate = vh.vm_handler()
            if not bootloader_drivers and not vm_migrate:
                logs.error('Access to online VM is denied. Possible reason - No SSH key on VM')
                msg_failed = (f'SSH PORT "22" is not opened for VM ID: {_idn} | IP: {_vm["ip_addr"]}\n'
                              f'Please install GRUB/WIN_DRIVERS via these options:'
                              f' "install_bootloader_offline --vm=\'identifier\'" |'
                              f' "install_win_drivers_offline --vm=\'identifier\'"')
                logs.write_log(file_path=f"{_file_name.format(user=user['id'])}_{_pid}_user_{user['id']}_manual_migrate_vm",
                               msg=msg_failed)
                continue

            _vm_properties = get_vm_source_properties(cfg, vm_idn=_idn)
            _vm_properties['storage_policy'] = _storage_policy
            _cloud_init_log = _prepare_cloud_init_msg(cloud_init_install=cloud_init, vm_properties=_vm_properties)
            if not _vm['built_from_iso'] and not _vm['built_from_ova']:
                result = bootloader_drivers(cfg,
                                            idn=_idn,
                                            vm_properties=_vm_properties,
                                            vm_handler=vh)
            else:
                result = True
                logs.warn(msg=f'VM [{_vm_info}] built from ISO or OVA, installation GRUB,'
                              f' CLOUD-INIT, etc. step skipped.')

            if not result:
                vm_msg += (f'\t{_vm_number}. Migration Status = {result}\n'
                           f'\t\t- IP "{_vm["ip_addr"]}"\n'
                           f'\t\t- Hostname: "{_vm["hostname"]}"\n'
                           f'\t\t- Label: "{_vm["label"]}"\n'
                           f'\t\t- Identifier: "{_idn}"\n'
                           f'\t\t- Installation Cloud-init: {_cloud_init_log}\n'
                           f'\t\t- Installation bootloader: {result}\n'
                           f'\t\t- Installation vz-guest-tools : {vh.guest_tools_result}\n'
                           f'\t- - - - - - - - - - - - - - - - -\n')
                logs.write_log(file_path=f"{_file_name.format(user=user['user_login'])}_{_pid}_user_{user['id']}",
                               msg=msg.format(user['user_login'],
                                              user['password'],
                                              _ssh_result,
                                              vm_msg))
                continue

            result_vm = vm_migrate(cfg,
                                   idn=_idn,
                                   vproj=vhi.project_name,
                                   vdom=cfg.vhi_conf['vinfra_domain'],
                                   vm_properties=_vm_properties,
                                   vhi_obj=vhi,
                                   placement=placement)

            vm_msg += (f'\t{_vm_number}. Migration Status = {result_vm}\n'
                       f'\t\t- IP "{_vm["ip_addr"]}"\n'
                       f'\t\t- Hostname: "{_vm["hostname"]}"\n'
                       f'\t\t- Label: "{_vm["label"]}"\n'
                       f'\t\t- Identifier: "{_idn}"\n'
                       f'\t\t- Installation Cloud-init: {_cloud_init_log}\n'
                       f'\t\t- Installation bootloader: {result}\n'
                       f'\t\t- Installation vz-guest-tools : {vh.guest_tools_result}\n'
                       f'\t- - - - - - - - - - - - - - - - -\n')
        # --Step 5 -- #
        # -- Finish Migration Session and put down logs  -- #
        logs.write_log(file_path=f"{_file_name.format(user=user['user_login'])}_{_pid}_user_{user['id']}",
                       msg=msg.format(user['user_login'],
                                      user['password'],
                                      _ssh_result,
                                      vm_msg))
    logs.info(f"{Helper.EQUAL.value} VHI: Script finished successfully {Helper.EQUAL.value}", separator=True)
    logs.info("\n")
