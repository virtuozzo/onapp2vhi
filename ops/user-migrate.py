#!/usr/bin/env python2
import os
import sys
import click
from click_default_group import DefaultGroup

plug_path = os.getcwd()
sys.path.append(plug_path)
sys.path.append(plug_path + '/cfg')
sys.path.append(plug_path + '/inc')

from inc.vhi_ssh_keys import VhiSshKeys
from inc.vhi_helpers import Vhi
from inc.utils import generate_random_password
from ops import logs
from cfg.o2v_config import Helper, OnAppAPICredentials
from inc.onapp_helpers import get_user_ssh_keys, get_user_data


USER_PASSWORD = generate_random_password()


@click.group(cls=DefaultGroup, default='user', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn', '--user', '--email', '--user-id', '--login', default='', help="OnApp User identifier.")
def user(idn=''):
    if not idn:
        print('You need to pass OnApp User ID value through --user-identifier=? parameter ')
        exit(17)

    user_property = idn
    # OnApp URLS:
    if idn.isdigit():
        _type = 'ID'
        url_user = "{onapp_url}/users/{user_id}.json".format(onapp_url=OnAppAPICredentials.ONAPP_CP_URL.value,
                                                             user_id=user_property)
    else:
        _type = 'OTHER'
        url_user = "{onapp_url}/users.json".format(onapp_url=OnAppAPICredentials.ONAPP_CP_URL.value)

    # --step_1--#
    # --OnApp: get source User information--#
    _user_data, response = get_user_data(url_user, _type, value_to_search=user_property)
    vhi_user_data = {'user_email': _user_data['email'],
                     'first_name': _user_data['first_name'],
                     'last_name': _user_data['last_name'],
                     'password': USER_PASSWORD,
                     'roles': _user_data['roles'],
                     'user_login': 'onapp_{}'.format(_user_data['login']),
                     'project_name': "onapp_project_{}".format(_user_data['email'])}
    logs.info('Response [{}] email: {}| login: {}| first_name: {}| last_name: {}'.format(
        response.status_code,
        vhi_user_data['user_email'],
        vhi_user_data['user_login'],
        vhi_user_data['first_name'],
        vhi_user_data['last_name'])
    )
    vhi = Vhi()
    vhi.create_object(vhi_user_data, 'project')
    vhi.create_object(vhi_user_data, 'user')
    _ssh_key = VhiSshKeys(vhi_user_data, get_user_ssh_keys(_user_data))
    _ssh_key.create_vhi_ssh_keys()
    logs.info('{} -- VHI: User has been migrated successfully --'.format(Helper.SPACES.value))


cli.add_command(user)
