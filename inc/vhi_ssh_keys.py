import requests
import json
from inc.helper import Helper
from cfg.config_parser import VHI_CREDS
from inc.logger import logs
from inc.onapp_helpers import check_user_role


class VhiSshKeys:
    """
    Object is used to migrate User SSH Keys from OnApp platform to VHI platform.
    It takes as input arguments user object and list of ssh keys
    """
    _URL = f"{VHI_CREDS['url']}{VHI_CREDS['api_path']}"
    _PANEL_URL = f"{VHI_CREDS['panel_url']}{VHI_CREDS['api_path']}"
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'
    PATCH = 'PATCH'

    def __init__(self, user_obj: dict, ssh_keys: list):
        self._user = user_obj
        self._login = self._user['user_login']
        self._first_name = self._user['first_name']
        self._last_name = self._user['last_name']
        self._pwd = self._user['password']
        self._proj_name = self._user['project_name']
        self._ssh_keys = ssh_keys
        self._headers = ''
        self._creds = {"domain": VHI_CREDS['vinfra_domain'],
                       "domainAdminStartPageEnabled": False,
                       "username": self._login,
                       "password": self._pwd}
        self._login_url = f"{self._URL}/login"
        self._panel_login_url = f"{self._PANEL_URL}/login"
        self._auth_endpoint = "{}/accounts/projects/{}/auth/"
        self._user_projects_url = f"{self._URL}/accounts/projects"
        self._projects_url = f"{self._URL}/domains/{VHI_CREDS['domain_id']}/projects"
        self.ssh_keys_url = f"{self._PANEL_URL}/compute/keys"
        self._proj_auth_url = ''
        logs.info(f'{Helper.SPACES.value}-- VHI: Creating SSH keys --', header=True)

    @property
    def headers(self):
        """
        Prepare headers for VHI API
        :return:
        """
        _headers = {'Content-type': 'application/json',
                    'x-requested-with': 'XMLHttpRequest',
                    'Authorization': 'access_token myToken',
                    'accept': 'application/json, text/plain, */*',
                    'sec-fetch-mode': 'cors',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'sec-fetch-site': 'same-origin',
                    'User-Agent': 'Mozilla/5.0'}
        return _headers

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

        else:
            if response.status_code not in (200, 201, 204):
                logs.error(f'Response [{response.status_code}]: {response.content}')
                return False

            logs.debug(f'Response [{response.status_code}]: {response.content}')
            return True

    def _auth(self):
        """
        Get authorization cookies
        :return: headers {}
        """
        _headers = self.headers
        _headers.update({'x-session-id': '1'})
        self._log_handler(**{'method': self.POST, 'url': self._login_url, 'headers': _headers, 'body': self._creds})
        response = requests.post(self._login_url,
                                 headers=_headers,
                                 data=json.dumps(self._creds),
                                 verify=False)
        if not self._log_handler(response=response):
            return False

        _headers.update({f'Cookie': f'session1={response.cookies["session1"]}'})
        _proj_url = ""
        if not check_user_role(self._user):
            _proj_url = self._user_projects_url
            self._log_handler(**{'method': self.GET, 'url': _proj_url, 'headers': _headers})
        else:
            _proj_url = self._projects_url
            self._log_handler(**{'method': self.GET, 'url': _proj_url, 'headers': _headers})
        response_2 = requests.get(_proj_url, headers=_headers, verify=False)
        if not self._log_handler(response=response_2):
            return False

        proj_id = [proj['id'] for proj in response_2.json()['data'] if proj['name'] == self._proj_name][0]
        auth_url = self._auth_endpoint.format(self._PANEL_URL, proj_id)
        self._proj_auth_url = auth_url
        _headers.update({'x-auth-token': proj_id})
        self._log_handler(**{'method': self.POST, 'url': auth_url, 'headers': _headers, 'body': {}})
        response_3 = requests.post(auth_url, headers=_headers, verify=False)
        _headers.update({'Cookie': f'session1={response_3.cookies["session1"]}'})
        if not self._log_handler(response=response_3):
            return False

        self._headers = _headers
        return True

    def _verify_ssh_keys(self):
        """
        Check whether ssh keys exists on VHI side
        :return:
        """
        if not self._auth():
            return False

        self._log_handler(**{'method': self.GET, 'url': self.ssh_keys_url, 'headers': self._headers})
        response = requests.get(self.ssh_keys_url, headers=self._headers, verify=False)
        self._log_handler(response=response)
        ssh_keys = response.json()['data']
        if not ssh_keys:
            return self._ssh_keys

        for _key in ssh_keys:
            if _key['public_key'] in self._ssh_keys:
                self._ssh_keys.remove(_key['public_key'])
                logs.warn(f"SSH Key {_key['name']} exists on VHI side: {_key['public_key']}")
        return self._ssh_keys

    def _vhi_ssh_keys_payload(self, idn: int, ssh_data: str):
        """
        Prepare ssh keys payload for VHI based on OnApp response
        :param ssh_data: ssh key
        :param idn: 1, 2, 3
        :return:
        """
        name = f"{self._first_name.lower()}_{self._last_name.lower()}_ssh_key_{idn}".replace('@', '')
        if '.' in name:
            name = name.replace('.', '_')
        return json.dumps({"name": name,
                           "description": f"User {self._first_name} {self._last_name} SSH Key",
                           "public_key": ssh_data})

    def create_vhi_ssh_keys(self):
        """
        Create SSH Keys on VHI Side
        :return:
        """
        if not self._ssh_keys:
            _msg = 'User does not have SSH keys.'
            logs.warn(_msg)
            return _msg

        ssh_keys = self._verify_ssh_keys()
        if not ssh_keys and type(ssh_keys) == list:
            return 'SSH keys had migrated before.'

        elif not ssh_keys and type(ssh_keys) == bool:
            return 'SSH keys has not been migrated. Please Check logs.'

        self._log_handler(**{'method': self.POST, 'url': self._proj_auth_url, 'headers': self._headers, 'body': {}})
        # VHI API works strange, before each action via API we should trigger accounts/projects/{proj_id}/auth/
        requests.post(self._proj_auth_url, headers=self._headers, data={}, verify=False)
        for idn, ssh_key in enumerate(ssh_keys):
            payload = self._vhi_ssh_keys_payload(idn, ssh_key)
            self._log_handler(**{'method': self.POST,
                                 'url': self.ssh_keys_url,
                                 'headers': self._headers,
                                 'body': payload})
            response = requests.post(self.ssh_keys_url, headers=self._headers, data=payload, verify=False)
            self._log_handler(response=response)
        logs.info(f'{Helper.SPACES.value} -- VHI: User SSH Keys has been migrated successfully --', header=True)
        logs.info('')
        return True
