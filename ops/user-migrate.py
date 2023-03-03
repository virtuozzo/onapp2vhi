import click

from click_default_group import DefaultGroup
from inc.vhi_ssh_keys import VhiSshKeys
from inc.vhi_helpers import Vhi
from inc.utils import generate_random_password
from inc.logger import logs
from inc.helper import Helper
from inc.onapp_helpers import (
    get_user_ssh_keys,
    get_user_data,
    get_bucket_limits,
    check_user_role
)

USER_PASSWORD = generate_random_password()


@click.group(cls=DefaultGroup, default='user', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--idn', '--user', '--email', '--user-id', '--login', default='', help="OnApp User identifier.")
def user(idn=''):
    if not idn:
        logs.error('You need to pass OnApp User ID value through --user-identifier=? parameter ')
        exit(1)

    user_property = idn
    _default_project = True
    # OnApp URLS:
    if idn.isdigit():
        _type = 'ID'
        url_user = f"users/{user_property}"
    else:
        _type = 'OTHER'
        url_user = "users"

    # --step_1--#
    # --OnApp: get source User information--#
    _user_data = get_user_data(url_user, _type, value_to_search=user_property)
    vhi_user_data = {'user_email': _user_data['email'],
                     'first_name': _user_data['first_name'],
                     'last_name': _user_data['last_name'],
                     'password': USER_PASSWORD,
                     'roles': _user_data['roles'],
                     'user_login': '{}'.format(_user_data['login']),
                     'project_name': "project_{}".format(_user_data['email']),
                     'quotas': get_bucket_limits(bucket_id=_user_data["bucket_id"])}
    logs.info(f"USER INFO email: {vhi_user_data['user_email']}|"
              f" login: {vhi_user_data['user_login']}| first_name: {vhi_user_data['first_name']}|"
              f" last_name: {vhi_user_data['last_name']}")
    vhi = Vhi()
    if not check_user_role(vhi_user_data):
        result = vhi.create_object(vhi_user_data, 'project')
        if not result:
            return False

        _default_project = False
    result = vhi.create_object(vhi_user_data, 'user')
    if result:
        _ssh_key = VhiSshKeys(vhi_user_data, get_user_ssh_keys(_user_data), default_project=_default_project)
        _ssh_key.create_vhi_ssh_keys()
        logs.info(f'{Helper.SPACES.value} -- VHI: User has been migrated successfully --')
    else:
        logs.warn('User has not been migrated.')
        return False


cli.add_command(user)
