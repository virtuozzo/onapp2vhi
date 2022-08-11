#!/usr/bin/env python2
import os
import sys
import click
import requests
from click_default_group import DefaultGroup

plug_path = os.getcwd()
sys.path.append(plug_path)
sys.path.append(plug_path + '/cfg')
sys.path.append(plug_path + '/inc')

from o2v_config import *
from functions import *
from onapp_helpers import *
from vhi_ssh_keys import VhiSshKeys
from vhi_helpers import Vhi
from utils import generate_random_password


AUTH = (ONAPP_USER_EMAIL, ONAPP_USER_APIKEY)
USER_PASSWORD = generate_random_password()


def get_user_ssh_keys(user_data):
    """
    Get user ssh keys and return them
    :param user_data: {"id": 3, "first_name": "Test1", "last_name": "Test2", . . .}
    :return: [ssh_key1, ssh_key2]
    """
    _url = ONAPP_CP_URL + '/settings/ssh_keys.json'
    logs.info("{}-- OnApp: Get User SSH keys --   \n".format(SPACES), separator=True)
    logs.info('GET {url}'.format(url=_url))
    _ssh_keys = []
    response = requests.get(_url, auth=AUTH)
    for ssh_key in response.json():
        if ssh_key['ssh_key']['user_id'] != user_data['id']:
            continue

        _ssh_keys.append(ssh_key['ssh_key']['key'])
    logs.info('Response [{}]: {}'.format(response.status_code, _ssh_keys))
    return _ssh_keys


def get_user_data(url, get_type, value_to_search=None):
    """
    Get users data from OnApp platform
    :param url: /users.json or /users/1.json
    :param get_type: ID or any value in user obj
    :param value_to_search: value based on what we will find user
    :return:
    """
    logs.info("{}-- OnApp: Get User information --   \n".format(SPACES), separator=True)
    logs.info('GET {url}'.format(url=url))
    response = requests.get(url, auth=AUTH)
    if response.status_code != 200:
        logs.error(response.content)
        logs.error('Credentials you are using: {creds}'.format(creds=AUTH))
        exit(1)

    if get_type == 'ID':
        return response.json()['user'], response

    for _user in response.json():
        if value_to_search in list(_user['user'].values()):
            return _user['user'], response


@click.group(cls=DefaultGroup, default='user', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn', '--user', '--email', '--user-id', '--login', default='', help="OnApp User identifier.")
def user(idn=''):
    if idn == '':
        print('You need to pass OnApp User ID value through --user-identifier=? parameter ')
        exit(17)
    user_property = idn
    # OnApp URLS:
    if idn.isdigit():
        _type = 'ID'
        url_user = "{onapp_url}/users/{user_id}.json".format(onapp_url=ONAPP_CP_URL, user_id=user_property)
    else:
        _type = 'OTHER'
        url_user = "{onapp_url}/users.json".format(onapp_url=ONAPP_CP_URL)

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
    logs.info('{} -- VHI: User has been migrated successfully --'.format(SPACES))


cli.add_command(user)
