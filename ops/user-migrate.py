#!/usr/bin/env python2
import json
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
from vhi_helpers import Vhi


@click.group(cls=DefaultGroup, default='user', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn', '--user', '--identifier', '--user-id', default='', help="OnApp VM identifier.")
def user(idn=''):
    if idn == '':
        print('You need to pass OnApp User ID value through --user-identifier=? parameter ')
        exit(17)
    vhi = Vhi()
    user_id = idn
    auth = (ONAPP_USER_EMAIL, ONAPP_USER_APIKEY)

    # OnApp URLS:
    url_single_user = "{onapp_url}/users/{user_id}.json".format(onapp_url=ONAPP_CP_URL, user_id=user_id)

    # --step_1--#
    # --OnApp: get source User information--#
    logs.info("{}-- OnApp: Get User information --   \n".format(SPACES), separator=True)
    logs.info('GET {url}'.format(url=url_single_user))
    response = requests.get(url_single_user, auth=auth)
    if response.status_code != 200:
        logs.error(response.content)
        logs.error('Credentials you are using: {creds}'.format(creds=auth))
        exit(1)

    _user_data = response.json()['user']
    vhi_user_data = {'user_email': _user_data['email'],
                     'first_name': _user_data['first_name'],
                     'last_name': _user_data['last_name'],
                     'roles': _user_data['roles'],
                     'user_login': 'onapp_{}'.format(_user_data['login']),
                     'project_name': "onapp_project_{}".format(_user_data['email'])}
    logs.info('Response [{}]: email: {} | login: {} | first_name: {} | last_name {}'.format(
        response.status_code,
        vhi_user_data['user_email'],
        vhi_user_data['user_login'],
        vhi_user_data['first_name'],
        vhi_user_data['last_name'])
    )

    vhi.create_object(vhi_user_data, 'project')
    vhi.create_object(vhi_user_data, 'user')
    logs.info('{} -- User has been migrated SUCCESSFULLY. --'.format(SPACES))


cli.add_command(user)
