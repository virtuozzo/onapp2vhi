import requests
import json
from cfg.o2v_config import VHICLoudDefaults, Helper
from inc.logger import logs
from functions import run_command
import time

# ToDo:
#  email notification


class Vhi:
    # VHI ROLES:
    VHI_ADMIN = "domain_admin"
    VHI_PROJECT_MEMBER = "project_admin"

    # API URL
    _URL = "{vhi_url}{vhi_api}".format(vhi_url=VHICLoudDefaults.VHI_CP_URL.value,
                                       vhi_api=VHICLoudDefaults.VHI_API_PATH.value)
    _VHI_DOMAIN_API = "{url}/domains/{domain_id}".format(url=_URL, domain_id=VHICLoudDefaults.VHI_DOMAIN_ID.value)

    def __init__(self):
        self._cookie = ""
        self.project_id = ""
        self.project_name = VHICLoudDefaults.VINFRA_PROJECT.value
        self.user_id = ""
        self.flavor_name = ""
        self.projects_url = "{url}/projects".format(url=self._VHI_DOMAIN_API)
        self.flavors_url = "{url}/compute/flavors".format(url=self._URL)
        self.users_url = "{url}/users".format(url=self._VHI_DOMAIN_API)
        self._login_url = "{url}/login".format(url=self._URL)
        self._storage_policies_url = "{url}/storage_policies".format(url=self._URL)
        self._quotas_url = "{}/compute/quotas/{}"
        self._auth_endpoint = "{}/accounts/projects/{}/auth/"
        self._storage_id = ""
        self._storage_name = ""
        self._creds = {"username": VHICLoudDefaults.VHI_LOGIN.value,
                       "password": VHICLoudDefaults.VINFRA_PASS.value}

        if not self._cookie:
            logs.info('POST {}'.format(self._login_url), separator=True)
            self._auth()

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
            _headers.update({'Cookie': 'session={}'.format(self._cookie)})
        return _headers

    def _auth(self):
        """
        Get authorization cookies
        :return:
        """
        response = requests.post(self._login_url,
                                 headers=self.headers,
                                 data=json.dumps(self._creds))
        if response.status_code != 200:
            logs.error(response.content)
            exit(1)

        self._cookie = response.cookies['session']

    def _vhi_project_payload(self, project_data):
        """
        Prepare payload for VHI project object
        :param project_data: {'project_name': 'name', . . .}
        :return: payload
        """
        logs.info('GET {}'.format(self._storage_policies_url), separator=True)
        response = requests.get(self._storage_policies_url, headers=self.headers)
        logs.info('Response [{}]: {}'.format(response.status_code, response.content))
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

    def _vhi_quotas(self, quotas):
        logs.info('{}-- VHI: Set Quotas to project "{}" --'.format(Helper.SPACES.value, self.project_id),
                  separator=True)
        _quotas_url = self._quotas_url.format(self._URL, self.project_id)
        quotas_payload = json.dumps({"compute": {"cores": {"limit": quotas['cores']},
                                                 "ram": {"limit": quotas['RAM']}},
                                     "storage": {
                                         "storage_policies": {self._storage_name: {"limit": quotas['storage']}}}})
        logs.info('POST {}'.format(_quotas_url), separator=True)
        logs.info('Payload {}'.format(quotas_payload))
        logs.info('Headers {}'.format(self.headers))
        response = requests.post(_quotas_url, headers=self.headers, data=quotas_payload)
        logs.info('Response [{}]. {}'.format(response.status_code, response.content))
        return

    def _vhi_user_payload(self, user_data):
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

            # When we have custom role, an identifier will be "aj3ht237gy2c", we need to check permissions
            elif len(role['role']['permissions']) >= 162:
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

    def _vhi_flavor_payload(self, vm_data):
        return json.dumps({"name": vm_data['name'],
                           "vcpus": vm_data['vcpus'],
                           "ram": vm_data['ram'],
                           "disk": 0})

    def _define_object_type(self, obj_data, object_type):
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

    def _get_objects_list(self, object_url):
        """
        Get projects list from VHI Domain
        :return: list object with project data
        """
        _object_name = object_url.split('/')[-1]
        logs.info("{}-- VHI: Get VHI {} --   ".format(Helper.SPACES.value, _object_name.capitalize()), separator=True)
        logs.info('GET {}'.format(object_url), separator=True)
        projects_list = requests.get(object_url, headers=self.headers)
        logs.info('Response [{}]: {}'.format(projects_list.status_code, projects_list.content))
        return projects_list.json()['data']

    def verify_object_on_vhi_side(self, object_name, key_to_check, object_url):
        """
        Verify whether object exists on VHI side or not
        :return: bool True or False
        """
        _name_object = object_url.split("/")[-1][:-1]
        objects = self._get_objects_list(object_url)
        if object_name in [obj[key_to_check] for obj in objects]:
            for _obj in objects:
                if object_name == _obj[key_to_check]:
                    logs.warn('{} with name "{}" exists on VHI side.'.format(_name_object.capitalize(),
                                                                             object_name))
                    if _name_object in self.users_url:
                        self.user_id = _obj['id']
                    elif _name_object in self.projects_url:
                        self.project_id = _obj['id']
                    elif _name_object in self.flavors_url:
                        self.flavor_name = _obj['name']
                    return True, _name_object.capitalize()

        return False, _name_object.capitalize()

    def create_object(self, proj_data, object_type):
        """
        Create new project on VHI side with provided properties
        :param proj_data: {'user_email': 'email@email.com', . . .}
        :param object_type: "user", "project", "ssh_keys"
        :return:
        """
        self._auth()
        object_properties = self._define_object_type(proj_data, object_type)
        if object_properties['exist']:
            return False

        logs.info('{}-- VHI: Create new {} --'.format(Helper.SPACES.value, object_properties['name']), separator=True)
        logs.info('POST {}'.format(object_properties['url']), separator=True)
        logs.info('Headers: {}'.format(self.headers))
        logs.info('Payload: {}'.format(object_properties['payload']))
        response = requests.post(object_properties['url'],
                                 headers=self.headers,
                                 data=object_properties['payload'])
        assert response.status_code in (200, 201), logs.error(
            'Response [{}]. {} has not been created.\nResponse: {}'.format(response.status_code,
                                                                           object_properties['name'],
                                                                           response.content), separator=True)
        logs.info('Response [{}]: {}'.format(response.status_code, response.content))
        if object_type == "user":
            self.user_id = response.json()['id']
        elif object_type == "project":
            self.project_id = response.json()['id']
            self.project_name = response.json()['name']
            self._vhi_quotas(proj_data['quotas'])
        elif object_type == "flavor":
            self.flavor_name = response.json()['name']
        return True


def is_vm_active(
        ssh_port=VHICLoudDefaults.VHI_SSH_PORT.value,
        ssh_opt=Helper.SSH_OPTS.value,
        vhi_cp=VHICLoudDefaults.VHI_CP_IP.value,
        vm_id=None):
    if not vm_id:
        logs.error("Virtual server identifier has not been set: {}".format(vm_id))
        return False

    logs.info("Make sure that VM has 'active' status")
    CMD = "ssh -p{ssh_port} {sshopt} root@{vhi_cp} 'vinfra service compute server show {vm_id} -f json | jq -r -c [.name,.id,.vm_state,.power_state,.status];'".format(
        ssh_port=ssh_port,
        sshopt=ssh_opt,
        vhi_cp=vhi_cp,
        vm_id=vm_id
    )
    timeout = time.time() + 60 * 5  # 5 minutes from now
    while True:
        rc, ou = run_command(CMD,  Helper.VERBOSITY.value, 0)

        if time.time() > timeout:
            logs.error("The timeout exceeded... The VM is not active")
            break
        if "building" in ou:
            logs.info("The VM is building...")
        if "active" in ou:
            logs.info("The new VM has 'active' status")
            return True
        elif "error" in ou:
            logs.error(
                "The new VM has the 'error' status on VHI side. The migrations process is terminated. " +
                "See VM: " + VHICLoudDefaults.VHI_CP_URL.value + "/compute/servers/instances/" + vm_id
            )
            return False

