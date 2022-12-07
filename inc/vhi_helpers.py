import requests
import json
from inc.helper import Helper
from cfg.config_parser import VHI_CREDS, configs, ADMIN_AUTH
from inc.logger import logs
from inc.ssh_connector import SSH
from inc.utils import generate_random_password


# ToDo:
#  email notification


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
        self.project_name = VHI_CREDS['vinfra_project']
        self.user_id = ""
        self.flavor_name = ""
        self.vinfra_domain = VHI_CREDS['vinfra_domain']
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
                                 data=self._creds)
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
        response = requests.post(_quotas_url, headers=self.headers, data=quotas_payload)
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

        elif object_type == 'flavor':
            exist, name = self.verify_object_on_vhi_side(obj_data['name'],
                                                         'name',
                                                         self.flavors_url)
            payload = self._vhi_flavor_payload(obj_data)
            return {"exist": exist,
                    "name": name,
                    "payload": payload,
                    "url": self.flavors_url}

    def _get_objects_list(self, object_url: str):
        """
        Get projects list from VHI Domain
        :return: list object with project data
        """
        _object_name = object_url.split('/')[-1]
        logs.debug(f"{self._SPACES}-- VHI: Get VHI {_object_name.capitalize()} --", separator=True)
        self._log_handler(**{'method': self.GET, 'url': object_url, 'headers': self.headers})
        projects_list = requests.get(object_url, headers=self.headers)
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
                        self.project_name = _obj['name']
                    elif _name_object in self.flavors_url:
                        self.flavor_name = _obj['name']
                    return True, _name_object.capitalize()

        return False, _name_object.capitalize()

    def update_user_password(self, user_login: str):
        _pwd = generate_random_password()
        _change_pwd = (f"echo -e '{_pwd}' | {ADMIN_AUTH} domain user set {user_login}"
                       f" --password --domain '{self.vinfra_domain}'")
        self._vhi_ssh.execute(_change_pwd)
        return _pwd

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
                                 data=object_properties['payload'])
        if not self._log_handler(response=response):
            return False

        if object_type == "user":
            self.user_id = response.json()['id']
        elif object_type == "project":
            self.project_id = response.json()['id']
            self.project_name = response.json()['name']
            self._vhi_quotas(proj_data['quotas'])
        elif object_type == "flavor":
            self.flavor_name = response.json()['name']
        return True
