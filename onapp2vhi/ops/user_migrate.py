from onapp2vhi.inc.vhi_ssh_keys import VhiSshKeys
from onapp2vhi.inc.vhi_helpers import Vhi
from onapp2vhi.inc.utils import generate_random_password
from onapp2vhi.utilities.logs.logger import OnAppVHILogger
from onapp2vhi.inc.helper import Helper
from onapp2vhi.inc.onapp_helpers import (
    get_user_ssh_keys,
    get_user_data,
    get_bucket_limits,
    check_user_role
)
from onapp2vhi.utilities.config import OnApp2VHIConfig


USER_PASSWORD = generate_random_password()
logs = OnAppVHILogger()


def user_migrate_impl(cfg: OnApp2VHIConfig, idn=''):
    if not idn:
        logs.error('You need to pass OnApp User ID value through --user-identifier=? parameter ')
        exit(1)

    user_property = idn
    # OnApp URLS:
    if idn.isdigit():
        _type = 'ID'
        url_user = f"users/{user_property}"
    else:
        _type = 'OTHER'
        url_user = "users"

    # --step_1--#
    # --OnApp: get source User information--#
    _user_data = get_user_data(cfg, url_user, _type, value_to_search=user_property)
    vhi_user_data = {'user_email': _user_data['email'],
                     'first_name': _user_data['first_name'],
                     'last_name': _user_data['last_name'],
                     'password': USER_PASSWORD,
                     'roles': _user_data['roles'],
                     'user_login': '{}'.format(_user_data['login']),
                     'project_name': "project_{}".format(_user_data['email']),
                     'quotas': get_bucket_limits(cfg, bucket_id=_user_data["bucket_id"])}
    logs.info(f"USER INFO email: {vhi_user_data['user_email']}|"
              f" login: {vhi_user_data['user_login']}| first_name: {vhi_user_data['first_name']}|"
              f" last_name: {vhi_user_data['last_name']}")
    vhi = Vhi(cfg)
    if not check_user_role(vhi_user_data):
        result = vhi.create_project(vhi_user_data)
        if not result:
            return False

    result = vhi.create_user(vhi_user_data)
    if result:
        _ssh_key = VhiSshKeys(cfg, vhi_user_data, get_user_ssh_keys(cfg, _user_data))
        _ssh_key.create_vhi_ssh_keys()
        logs.info(f'{Helper.SPACES.value} -- VHI: User has been migrated successfully --')
    else:
        logs.warn('User has not been migrated.')
        return False
