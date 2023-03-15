import time

import requests
import urllib3
import json

from inc.helper import Helper
from cfg.config_parser import VHI_CREDS, configs, ADMIN_AUTH
from inc.logger import logs
from inc.ssh_connector import SSH
from inc.utils import generate_random_password, exit_status_code_handler
from inc.vinfra_wrapper import (
    VinfraFlavor,
    VinfraUser,
    VinfraNode,
    VinfraImage
)


# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Vhi:
    # VHI ROLES:
    VHI_ADMIN = "domain_admin"
    VHI_PROJECT_MEMBER = "project_admin"

    # API URL
    _URL = f"{VHI_CREDS['url']}{VHI_CREDS['api_path']}"
    _VHI_DOMAIN_API = f"{_URL}/domains/{VHI_CREDS['domain_id']}"
    _SPACES = Helper.SPACES.value
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'
    PATCH = 'PATCH'

    def __init__(self):
        self._cookie = ""
        self.project_id = ""
        self.project_name = ""
        self.user_id = ""
        self.flavor_name = ""
        self.vinfra_domain = VHI_CREDS['vinfra_domain']
        self.domain_id = VHI_CREDS['domain_id']
        self.projects_url = f"{self._VHI_DOMAIN_API}/projects"
        self.flavors_url = f"{self._URL}/compute/flavors"
        self.users_url = f"{self._VHI_DOMAIN_API}/users"
        self._login_url = f"{self._URL}/login"
        self._storage_policies_url = f"{self._URL}/storage_policies"
        self._quotas_url = "{}/compute/quotas/{}"
        self._auth_endpoint = "{}/accounts/projects/{}/auth/"
        self._storage_id = ""
        self._storage_name = ""

        self._vhi_ssh = SSH(**{'host': VHI_CREDS['cp_ip'], 'port': VHI_CREDS['cloud_ssh_port']})
        self._creds = json.dumps({"username": VHI_CREDS['login'],
                                  "password": VHI_CREDS['admin_ui_pwd']})

        if not self._cookie:
            self._auth()

    def _log_handler(self, response=None, **url_data):
        """
        :param response: response object
        :param url_data: {'method': 'GET',
                           'headers': {},
                            'body': {},
                            'url': 'https://www.google.com'}
        :return:
        """
        if url_data:
            _method = url_data.get('method', '')
            _headers = url_data.get('headers', '')
            _body = url_data.get('body', '')
            _url = url_data.get('url', '')
            logs.debug(f'{_method} {_url}', separator=True)
            logs.debug(f'Headers: {_headers}')
            if _method in (self.POST, self.PUT, self.PATCH):
                logs.debug(f'Payload: {_body}')
            return True

        elif response:
            if response.status_code not in (200, 201, 204):
                logs.error(f'Response [{response.status_code}]: {response.content}')
                return False

            logs.debug(f'Response [{response.status_code}]: {response.content}')
            return True

        else:
            return False

    @property
    def headers(self):
        """
        Prepare headers for VHI API
        :return:
        """
        _headers = {'Content-type': 'application/json',
                    'x-requested-with': 'XMLHttpRequest',
                    'accept': 'application/json, text/plain, */*',
                    'User-Agent': 'Mozilla/5.0',
                    'Connection': 'keep-alive'}
        if self._cookie:
            _headers.update({'Cookie': f'session={self._cookie}'})
        return _headers

    def _auth(self):
        """
        Get authorization cookies
        :return:
        """
        self._log_handler(**{'method': self.POST,
                             'url': self._login_url,
                             'headers': self.headers,
                             'body': self._creds})
        response = requests.post(self._login_url,
                                 headers=self.headers,
                                 data=self._creds,
                                 verify=False)
        if response.status_code != 200:
            self._log_handler(response=response)
            return False

        self._cookie = response.cookies['session']
        return True

    def check_default_project(self):
        """
        We had situation when we do not have "Default" project for migrations.
        This function is checking whether we have such project otherwise create new one and set values into
         `config.cfg` file
        :return:
        """
        _default_name = VHI_CREDS['vinfra_project']
        _create_project = (f"{ADMIN_AUTH} domain project create '{_default_name}' "
                           f"--domain='{self.vinfra_domain}' --enable "
                           f"--description='Default project for migrations.' -f json")
        _projects_cmd = f"{ADMIN_AUTH} domain project list --domain='{self.vinfra_domain}' -f json"
        exit_status, output_proj = self._vhi_ssh.execute(_projects_cmd)
        if _default_name.lower() not in [proj['name'].lower() for proj in json.loads(output_proj)]:
            # Create new `Default project` and set name into config file
            logs.warn(f'*** "{_default_name}" project was not found on VHI side. Creating new one. . .')
            exit_status, output = self._vhi_ssh.execute(_create_project)
            configs.set_new_value(configs.VHI, "vinfra_project", json.loads(output)['name'])
            return
        else:
            # Set the name of Default project into `config.cfg` file
            for proj in json.loads(output_proj):
                if proj['name'].lower() == _default_name:
                    configs.set_new_value(configs.VHI, "vinfra_project", _default_name)
                    return

    def _vhi_project_payload(self, project_data: dict):
        """
        Prepare payload for VHI project object
        :param project_data: {'project_name': 'name', . . .}
        :return: payload
        """
        self._log_handler(**{'method': self.GET, 'url': self._storage_policies_url, 'headers': self.headers})
        response = requests.get(self._storage_policies_url, headers=self.headers)
        if not self._log_handler(response=response):
            return False

        _storage = response.json()['data'][0]
        self._storage_id = _storage['id']
        self._storage_name = _storage['name']
        return json.dumps({"name": project_data['project_name'],
                           "description": "OnApp User {first_name} {last_name}".format(
                               first_name=project_data['first_name'],
                               last_name=project_data['last_name']),
                           "enabled": True,
                           "policiesEnabled": ["default", "default"],
                           "traitsEnabled": [],
                           "compute": {"cores": {"limit": -1},
                                       "ram": {"limit": -1},
                                       "network": {"floatingip": {"limit": -1}, "ipsec_site_connection": {"limit": -1}},
                                       "storage": {"storage_policies": {self._storage_id: {
                                           "name": self._storage_name,
                                           "limit": -1}}},
                                       "lbaas": {"loadbalancer": {"limit": -1}},
                                       "k8saas": {"cluster": {"limit": 20}},
                                       "placement": {}}})

    def _vhi_quotas(self, quotas: dict):
        logs.debug(f'{self._SPACES}-- VHI: Set Quotas to project "{self.project_id}" --', separator=True)
        _quotas_url = self._quotas_url.format(self._URL, self.project_id)
        quotas_payload = json.dumps({"compute": {"cores": {"limit": quotas['cores']},
                                                 "ram": {"limit": quotas['RAM']}},
                                     "storage": {
                                         "storage_policies": {self._storage_name: {"limit": quotas['storage']}}}})
        self._log_handler(**{'method': self.POST, 'url': _quotas_url, 'headers': self.headers, 'body': quotas_payload})
        response = requests.post(_quotas_url,
                                 headers=self.headers,
                                 data=quotas_payload,
                                 verify=False)
        self._log_handler(response=response)
        return

    def _vhi_user_payload(self, user_data: dict):
        """
        Prepare user payload for VHI based on OnApp role
        :param user_data: {'login': 'test', . . .}
        :return:
        """
        _user_role = ''
        for role in user_data['roles']:
            if role['role']['identifier'] == "admin":
                _user_role = self.VHI_ADMIN
                break

            _user_role = self.VHI_PROJECT_MEMBER
        vhi_user = {"name": user_data['user_login'],
                    "password": user_data['password'],
                    "system_permissions": [],
                    "email": user_data['user_email'],
                    "enabled": True}
        if _user_role == self.VHI_ADMIN:
            vhi_user.update({"domain_permissions": ["domain_admin"]})
            return json.dumps(vhi_user)

        vhi_user.update({"assigned_projects": [
            {"project_id": self.project_id, "role": self.VHI_PROJECT_MEMBER}
        ]})
        return json.dumps(vhi_user)

    def _vhi_flavor_payload(self, vm_data: dict):
        return json.dumps({"name": vm_data['name'],
                           "vcpus": vm_data['vcpus'],
                           "ram": vm_data['ram'],
                           "disk": 0})

    def _define_object_type(self, obj_data: dict, object_type: str):
        if object_type == 'user':
            exist, name = self.verify_object_on_vhi_side(obj_data['user_email'],
                                                         'email',
                                                         self.users_url)
            payload = self._vhi_user_payload(obj_data)
            return {"exist": exist,
                    "name": name,
                    "payload": payload,
                    "url": self.users_url}

        elif object_type == 'project':
            exist, name = self.verify_object_on_vhi_side(obj_data['project_name'],
                                                         'name',
                                                         self.projects_url)
            payload = self._vhi_project_payload(obj_data)
            return {"exist": exist,
                    "name": name,
                    "payload": payload,
                    "url": self.projects_url}
        else:
            return {}

    def _get_objects_list(self, object_url: str):
        """
        Get projects list from VHI Domain
        :return: list object with project data
        """
        _object_name = object_url.split('/')[-1]
        logs.debug(f"{self._SPACES}-- VHI: Get VHI {_object_name.capitalize()} --", separator=True)
        self._log_handler(**{'method': self.GET, 'url': object_url, 'headers': self.headers})
        projects_list = requests.get(object_url, headers=self.headers, verify=False)
        if not self._log_handler(response=projects_list):
            return []

        return projects_list.json()['data']

    def verify_object_on_vhi_side(self, object_name: str, key_to_check: str, object_url: str):
        """
        Verify whether object exists on VHI side or not
        :return: bool True or False
        """
        _name_object = object_url.split("/")[-1][:-1]
        objects = self._get_objects_list(object_url)
        if not objects:
            return False, ""

        if object_name in [obj[key_to_check] for obj in objects]:
            for _obj in objects:
                if object_name == _obj[key_to_check]:
                    logs.warn(f'{_name_object.capitalize()} with name "{object_name}" exists on VHI side.')
                    if _name_object in self.users_url:
                        self.user_id = _obj['id']
                    elif _name_object in self.projects_url:
                        self.project_id = _obj['id']
                    return True, _name_object.capitalize()

        return False, _name_object.capitalize()

    def update_user_password(self, user_login: str):
        _pwd = generate_random_password()
        _change_pwd = (f"echo -e '{_pwd}' | {ADMIN_AUTH} domain user set {user_login}"
                       f" --password --domain {self.vinfra_domain}")
        self._vhi_ssh.execute(_change_pwd)
        return _pwd

    def flavor_handler(self, onapp_flavor: dict):
        """
        Method purpose is to verify flavor on VHI side and check whether it exists or not and create new one
        :param onapp_flavor:
        :return:
        """
        _flavor_name = onapp_flavor['name']
        _payload = self._vhi_flavor_payload(vm_data=onapp_flavor)
        _vinfra = VinfraFlavor(service_user=True)
        exit_status, output = _vinfra.flavor_list()
        if not exit_status_code_handler(exit_code=exit_status,
                                        message=f'Impossible to get Flavor list. Output:\n\t{output}'):
            return False

        _vhi_flavors = [_flavor['name'] for _flavor in json.loads(output)]
        logs.debug(f'VHI existing flavors: {_vhi_flavors}')
        if _flavor_name in _vhi_flavors:
            self.flavor_name = _flavor_name
            return True

        exit_status, output = _vinfra.create(flavor_name=_flavor_name,
                                             vcpus=onapp_flavor['vcpus'],
                                             ram=onapp_flavor['ram'])
        if not exit_status_code_handler(exit_code=exit_status,
                                        message=f'Flavor has NOT been created. Output:\n\t{output}'):
            return False

        self.flavor_name = json.loads(output)['name']
        return True

    def _verify_user_exists(self, user_email: str, domain: str):
        """
        Verify whether user exists on VHI side or not
        :param user_email:
        :return:
        """
        v_user = VinfraUser()

        # Get List of users
        exit_status, output = v_user.user_list(domain=domain)
        _user_emails = [_user['email'] for _user in json.loads(output)]
        if user_email in _user_emails:
            return True

        return False

    def _create_domain_service_user(self):
        """
        Create Domain Service User for specified Domain:
            - echo -e "123456789@" | vinfra --vinfra-username='admin' --vinfra-password='4OnApp13777'
                 domain user create test123 --email "migration_helper@user.com" --domain-permissions domain_admin
                    --domain "MultiDomain"  --enable -f json
        Set Compute role to new user or to an existing one
            - vinfra domain user set test123 --assign-domain MultiDomain compute --domain=MultiDomain
        :return:
        """
        v_user = VinfraUser(cp_ip=True)
        _pwd = generate_random_password()
        _domain_service_user = {"email": f"{self.vinfra_domain}@user.com",
                                "name": f"dom_migration_user_{self.vinfra_domain.lower()}",
                                "enable": True,
                                "domain-permissions": 'domain_admin',
                                "domain": self.vinfra_domain}
        result = self._verify_user_exists(user_email=_domain_service_user['email'],
                                          domain=self.vinfra_domain)
        if result:
            v_image = VinfraImage(channel_timeout=5)
            exit_status, output = v_image.images()
            if not exit_status_code_handler(exit_code=exit_status,
                                            message=f'Domain Service User password is wrong. Output:\n\t{output}'):
                _new_pwd = self.update_user_password(user_login=_domain_service_user['name'])
                logs.warn(msg='Changed password to the new one for Domain Service User')
                configs.set_new_value(section=configs.VHI, option="vinfra_domain_pass", value=_new_pwd)
                domain_auth = configs.reset_domain_auth()
                import inc.vinfra_wrapper as wrapper
                wrapper.DOMAIN_AUTH = domain_auth
            return True

        exit_status, output = v_user.create(user_data=_domain_service_user, pwd=_pwd)
        if not exit_status_code_handler(exit_code=exit_status,
                                        message=f'Domain Service User has not been created. Output:\n\t{output}'):
            return False

        v_user.set(user_name=_domain_service_user['name'],
                   domain=self.vinfra_domain,
                   assign_domain=[self.vinfra_domain, 'compute'])
        configs.set_new_value(section=configs.VHI, option="vinfra_domain_user", value=_domain_service_user['name'])
        configs.set_new_value(section=configs.VHI, option="vinfra_domain_pass", value=_pwd)
        domain_auth = configs.reset_domain_auth()
        import inc.vinfra_wrapper as wrapper
        wrapper.DOMAIN_AUTH = domain_auth
        return True

    def create_service_user(self):
        """
        Creates new user and assign to him Service User role to be able
        to do any manipulations with compute resources within Domain
        If such user is created it will just take it creds from cfg/config.cfg file
        Manually command:
        `vinfra domain user set migration_user@onapp.test.com --assign-domain Default compute --domain=Default`
        :return:
        """
        v_user = VinfraUser(cp_ip=True)
        _pwd = generate_random_password()
        _service_user_payload = {"email": "migration_helper@user.com",
                                 "system-permissions": 'compute',
                                 "name": "migration_user",
                                 "enable": True,
                                 "assign-domain": ('Default', 'compute'),
                                 "domain": 'Default'}

        # Get List of users
        if VHI_CREDS['vinfra_user'] != _service_user_payload['name']:
            configs.set_new_value(section=configs.VHI, option="vinfra_user", value=_service_user_payload['name'])
            vinfra_auth = configs.reset_auth()
            import inc.vinfra_wrapper as wrapper
            wrapper.VINFRA_AUTH = vinfra_auth

        if self.vinfra_domain != 'Default':
            domain_user = self._create_domain_service_user()
            if not domain_user:
                return False

        result = self._verify_user_exists(user_email=_service_user_payload['email'],
                                          domain='Default')
        if result:
            _msg = (f'``Service User`` with Email: {_service_user_payload["email"]} exists on VHI side.'
                    f' Checking ``Service User`` credentials. . .')
            logs.info(msg=_msg, header=True)
            vinfra_node = VinfraNode(channel_timeout=5)
            exit_status, output = vinfra_node.list_node()
            if not exit_status_code_handler(exit_code=exit_status,
                                            message=f'Service User creds are not valid. Output:\n\t{output}'):
                logs.debug('Updating credentials for SERVICE USER and save them into `cfg/config.cfg`')

                # Generating new pwd for Service User and save it into config file, after check credentials again
                self.vinfra_domain = 'Default'
                new_pwd = self.update_user_password(user_login=_service_user_payload['name'])
                self.vinfra_domain = VHI_CREDS['vinfra_domain']
                configs.set_new_value(section=configs.VHI, option="vinfra_pass", value=new_pwd)
                vinfra_auth = configs.reset_auth()
                import inc.vinfra_wrapper as wrapper
                wrapper.VINFRA_AUTH = vinfra_auth
                v_node = VinfraNode(channel_timeout=5)
                exit_status, output = v_node.list_node()
                if not exit_status_code_handler(exit_code=exit_status,
                                                message=f'Updating Service User creds failed. Output:\n\t{output}'):
                    return False

                try:
                    assert type(json.loads(output)) == list
                except AssertionError:
                    logs.error(f'Service User password has NOT been changed. Output from getting node list:\n{output}')
                    return False
                logs.info(msg=f'SERVICE USER password has been updated,'
                              f' credentials saved into `cfg/config.cfg`')
                return True

            logs.info(msg=f'SERVICE USER credentials are valid and stored in `cfg/config.cfg`')
            return True

        exit_status, output = v_user.create(user_data=_service_user_payload, pwd=_pwd)
        if not exit_status_code_handler(exit_code=exit_status,
                                        message=f'Service User has not been created. Output:\n\t{output}'):
            return False

        user_response = json.loads(output)
        try:
            assert _service_user_payload['system-permissions'] in user_response['system_permissions']
            assert _service_user_payload['email'] == user_response['email']
            assert _service_user_payload['name'] == user_response['name']
        except AssertionError:
            logs.error(f'Service User has NOT been created. Output: {user_response}')
            return False

        # Save password to cfg/config.cfg file and after that verify ability to get list of nodes
        configs.set_new_value(section=configs.VHI, option="vinfra_pass", value=_pwd)
        vinfra_auth = configs.reset_auth()
        import inc.vinfra_wrapper as wrapper
        wrapper.VINFRA_AUTH = vinfra_auth
        time.sleep(1)
        v_node = VinfraNode(channel_timeout=5)
        exit_status, output = v_node.list_node()
        try:
            assert exit_status_code_handler(exit_code=exit_status)
            assert type(json.loads(output)) == list
        except AssertionError:
            logs.error(f'Service User password has NOT been changed. Output from getting node list:\n{output}')
            return False

        logs.info(msg=f'Service user has been created, credentials saved into `cfg/config.cfg`')
        return True

    def create_object(self, proj_data: dict, object_type: str):
        """
        Create new project on VHI side with provided properties
        :param proj_data: {'user_email': 'email@email.com', . . .}
        :param object_type: "user", "project", "ssh_keys"
        :return:
        """
        if not self._auth():
            return False

        object_properties = self._define_object_type(proj_data, object_type)
        if not object_properties:
            return False

        if object_properties['exist']:
            return False

        if not object_properties['name']:
            return False

        logs.debug(f'{self._SPACES}-- VHI: Create new {object_properties["name"]} --', separator=True)
        self._log_handler(**{'method': self.POST,
                             'url': object_properties['url'],
                             'headers': self.headers,
                             'body': object_properties['payload']})
        response = requests.post(object_properties['url'],
                                 headers=self.headers,
                                 data=object_properties['payload'],
                                 verify=False)
        if not self._log_handler(response=response):
            return False

        if object_type == "user":
            self.user_id = response.json()['id']
        elif object_type == "project":
            self.project_id = response.json()['id']
            self.project_name = response.json()['name']
            self._vhi_quotas(proj_data['quotas'])
        return True
