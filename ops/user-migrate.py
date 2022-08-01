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
from logger import OnAppVHILogger


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


@click.group(cls=DefaultGroup, default='user', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn', '--user', '--identifier', '--user-id', default='', help="OnApp VM identifier.")
def user(idn=''):
    _logger = OnAppVHILogger()
    if idn == '':
        print('You need to pass OnApp User ID value through --user-identifier=? parameter ')
        exit(17)

    USER_ID = idn
    AUTH = (ONAPP_USER_EMAIL, ONAPP_USER_APIKEY)

    # Temporary User Password:
    _USER_PASSWORD = "Test123$"

    # VHI ROLES
    VHI_ADMIN = "domain_admin"
    VHI_PROJECT_MEMBER = "project_admin"




    # --step_1--#
    # --OnApp: get source User information--#

    _logger.info(" -- OnApp: get source User information -- ")
    URL = ONAPP_CP_URL + "/users/{user_id}.json".format(user_id=USER_ID)
    _logger.info('GET {url}'.format(url=URL))
    response = requests.get(URL, auth=AUTH)
    if response.status_code != 200:
        if 'errors' in response.content:
            print(response['errors']['base'])
            print('Credentials you are using:\n {creds}'.format(creds=AUTH))
            exit(1)


    _user_data = response.json()['user']
    USER_EMAIL = _user_data['email']
    USER_LOGIN = _user_data['login']
    user_roles = _user_data['roles']
    USER_ROLE = ''
    for role in user_roles:
        _onapp_role = role['role']['identifier']
        if _onapp_role == "admin":
            USER_ROLE = VHI_ADMIN
            break
        else:
            USER_ROLE = VHI_PROJECT_MEMBER
    _logger.info('Parsing User data:\nemail={email} | login={login} | role={role} | password={password}'.format(email=USER_EMAIL,
                                                                                                                login=USER_LOGIN,
                                                                                                                role=USER_ROLE,
                                                                                                                password=_USER_PASSWORD))

    VHI_DOMAIN_BODY = {"name": "onapp_account_{email}".format(email=USER_EMAIL),
                       "description": "Test User Migrations",
                       "enabled": True}
    _logger.info(VHI_DOMAIN_BODY)
    _logger.info('NEXT PART WILL BE SOON ^-^\n CODE FINISHED SUCCESSFULLY (just for now. . .)')


cli.add_command(user)


