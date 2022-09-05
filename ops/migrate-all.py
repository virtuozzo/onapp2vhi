#!/usr/bin/env python2
import os
import click
from click_default_group import DefaultGroup
from cfg.o2v_config import Helper, OnAppAPICredentials
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
def migrate_all(user='',):
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
    :param user:
    :return:
    """
    # Arrange
    logs.info("")
    logs.info("{} VHI: Starting Migration Session {}".format(Helper.EQUAL.value, Helper.EQUAL.value))
    logs.info("")
    _path = os.getcwd()
    _file_name = os.path.join(_path, 'migration_logs/migration')
    user_idn = ''
    url_user = "{onapp_url}/users.json".format(onapp_url=OnAppAPICredentials.ONAPP_CP_URL.value)
    if user:
        if not user.isdigit():
            logs.error("Please specify User ID as integer: --user=7")
            exit(1)
        user_idn = int(user)

    # --Step 1--#
    # --OnApp: Get User, VM's information--#
    _user_data, response = get_user_data(url_user, None, all_users=True)
    logs.info('Response [{}]'.format(response.status_code))
    _vms_dict = get_all_virtual_machines()
    vhi_users_data = []
    for _user_info in _user_data:
        user_password = generate_random_password()
        _user = _user_info['user']
        if user_idn:
            if user_idn != _user['id']:
                continue

        if _user['login'] in DEFAULT_ONAPP_USER_NAMES:
            continue

        _vhi_user_data = {'user_email': _user['email'],
                          'id': _user['id'],
                          'first_name': _user['first_name'],
                          'last_name': _user['last_name'],
                          'password': user_password,
                          'roles': _user['roles'],
                          'user_login': 'onapp_{}'.format(_user['login']),
                          'project_name': "onapp_project_{}".format(_user['email']),
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
        full_name = "{} {}".format(user['first_name'], user['last_name'])
        msg = 'Login: {}\nPassword: {}\nSSH Keys Migrated: {}\nVIRTUAL MACHINES:\n{}'
        vhi = Vhi()
        logs.info("\n\n")

        # --Step 3--#
        # --OnApp: Start migration USER by USER--#
        logs.info("{}-- VHI: Migrate User {} --".format(Helper.SPACES.value, full_name), separator=True)
        if not check_user_role(user):
            vhi.create_object(user, 'project')
            _default_project = False
        _user_result = vhi.create_object(user, 'user')
        if _user_result:
            _ssh_key = VhiSshKeys(user_obj=user, ssh_keys=get_user_ssh_keys(user), default_project=_default_project)
            _ssh_result = _ssh_key.create_vhi_ssh_keys()
        elif not _user_result:
            user['password'] = ''
        logs.info("{}-- VHI: Migrate User {} Virtual Machines--".format(Helper.SPACES.value, full_name), separator=True)

        # --Step 4 -- #
        # -- VHI: Migrate Users Virtual Machines depends on their OS and BOOTED status -- #
        vm_msg = ""
        for _num, _vm in enumerate(user['virtual_machines']):
            vh = VmHandler(**_vm)
            _idn = _vm['id']
            logs.info("{}-- VHI: Migrate VM #{} IDENTIFIER {}--".format(Helper.SPACES.value, str(_num), _idn),
                      separator=True)
            logs.info("")
            bootloader_drivers, vm_migrate = vh.vm_handler()
            bootloader_drivers(idn=_idn, vhip='', verb='')
            result_vm = vm_migrate(idn=_idn,
                                   vproj=vhi.project_name,
                                   vuser=user['user_login'],
                                   vdom='',
                                   vpass='',
                                   vhip='',
                                   snc='',
                                   verb='')
            vm_msg += "    {}. VM identifier [{}]: Migrated [{}]\n".format(str(_num+1), _idn, result_vm)

        # --Step 5 -- #
        # -- Finish Migration Session and put down logs  -- #
        logs.write_log(file_path="{}_user_{}".format(_file_name, user['id']),
                       msg=msg.format(user['user_login'],
                                      user['password'],
                                      _ssh_result,
                                      vm_msg))
    logs.info("")
    logs.info("{} VHI: Script finished successfully {}".format(Helper.EQUAL.value, Helper.EQUAL.value))
    logs.info("\n")


cli.add_command(migrate_all)
