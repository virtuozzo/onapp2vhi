import requests
import json
from cfg.o2v_config import VHICLoudDefaults, Helper
from inc.logger import logs


class VhiSshKeys:
    """
    Object is used to migrate User SSH Keys from OnApp platform to VHI platform.
    It takes as input arguments user object and list of ssh keys
    """
    _URL = "{vhi_url}{vhi_api}".format(vhi_url=VHICLoudDefaults.VHI_CP_URL.value,
                                       vhi_api=VHICLoudDefaults.VHI_API_PATH.value)
    _PANEL_URL = "{vhi_url}{vhi_api}".format(vhi_url=VHICLoudDefaults.VHI_PANEL_URL.value,
                                             vhi_api=VHICLoudDefaults.VHI_API_PATH.value)

    def __init__(self, user_obj, ssh_keys):
        self._user = user_obj
        self._login = self._user['user_login']
        self._first_name = self._user['first_name']
        self._last_name = self._user['last_name']
        self._pwd = self._user['password']
        self._proj_name = self._user['project_name']
        self._ssh_keys = ssh_keys
        self._headers = ''
        self._creds = {"domain": VHICLoudDefaults.VINFRA_DOMAIN.value,
                       "domainAdminStartPageEnabled": False,
                       "username": self._login,
                       "password": self._pwd}
        self._login_url = "{url}/login".format(url=self._URL)
        self._panel_login_url = "{url}/login".format(url=self._PANEL_URL)
        self._auth_endpoint = "{}/accounts/projects/{}/auth/"
        self._projects_url = "{url}/domains/{dom_id}/projects".format(url=self._URL,
                                                                      dom_id=VHICLoudDefaults.VHI_DOMAIN_ID.value)
        self.ssh_keys_url = "{url}/compute/keys".format(url=self._PANEL_URL)
        self._proj_auth_url = ''
        logs.info('{}-- VHI: Creating SSH keys --'.format(Helper.SPACES.value), separator=True)

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

    @staticmethod
    def _log_response(response=None, url_data=None):
        """
        :param response: response object
        :param url_data: ('GET', 'https://www.google.com', {"headers": "headers"}, {})
        :return:
        """
        if url_data:
            _method = url_data[0]
            logs.info('{} {}'.format(url_data[0], url_data[1]))
            logs.info('Headers: {}'.format(url_data[2]))
            if _method in ('POST', 'PUT', 'PATCH'):
                logs.info('Payload: {}'.format(url_data[3]))
            return

        elif response:
            if response.status_code not in (200, 201, 204):
                logs.error('Response [{}]: {}'.format(response.status_code, response.content))
                exit(1)

            logs.info('Response [{}]: {}'.format(response.status_code, response.content), separator=True)

    def _auth(self):
        """
        Get authorization cookies
        :return: headers {}
        """
        _headers = self.headers
        _headers.update({'x-session-id': '1'})
        self._log_response(url_data=('POST', self._login_url, _headers, self._creds))
        response = requests.post(self._login_url,
                                 headers=_headers,
                                 data=json.dumps(self._creds))
        self._log_response(response=response)
        _headers.update({'Cookie': 'session1={}'.format(response.cookies['session1'])})
        self._log_response(url_data=('GET', self._projects_url, _headers))
        response_2 = requests.get(self._projects_url, headers=_headers)
        self._log_response(response=response_2)
        proj_id = [proj['id'] for proj in response_2.json()['data'] if proj['name'] == self._proj_name][0]
        auth_url = self._auth_endpoint.format(self._PANEL_URL, proj_id)
        self._proj_auth_url = auth_url
        _headers.update({'x-auth-token': proj_id})
        self._log_response(url_data=('POST', auth_url, _headers, {}))
        response_3 = requests.post(auth_url, headers=_headers)
        _headers.update({'Cookie': 'session1={}'.format(response_3.cookies['session1'])})
        self._log_response(response=response_3)
        self._headers = _headers

    def _verify_ssh_keys(self):
        """
        Check whether ssh keys exists on VHI side
        :return:
        """
        self._auth()
        self._log_response(url_data=('GET', self.ssh_keys_url, self._headers))
        response = requests.get(self.ssh_keys_url, headers=self._headers)
        self._log_response(response=response)
        ssh_keys = response.json()['data']
        if not ssh_keys:
            return self._ssh_keys

        for _key in ssh_keys:
            if _key['public_key'] in self._ssh_keys:
                self._ssh_keys.remove(_key['public_key'])
                logs.warn('SSH Key {} exists on VHI side: {}'.format(_key['name'], _key['public_key']))
        return self._ssh_keys

    def _vhi_ssh_keys_payload(self, idn, ssh_data):
        """
        Prepare ssh keys payload for VHI based on OnApp response
        :param ssh_data: ssh key
        :param idn: 1, 2, 3
        :return:
        """
        return json.dumps({"name": "{}_ssh_key_{}".format(self._login, idn),
                           "description": "User {} {} SSH Key".format(self._first_name, self._last_name),
                           "public_key": ssh_data})

    def create_vhi_ssh_keys(self):
        """
        Create SSH Keys on VHI Side
        :return:
        """
        ssh_keys = self._verify_ssh_keys()
        if not ssh_keys:
            return

        self._log_response(url_data=('POST', self._proj_auth_url, self._headers, {}))

        # VHI API works strange, before each action via API we should trigger accounts/projects/{proj_id}/auth/
        requests.post(self._proj_auth_url, headers=self._headers, data={})
        if ssh_keys:
            for idn, ssh_key in enumerate(ssh_keys):
                payload = self._vhi_ssh_keys_payload(idn, ssh_key)
                self._log_response(url_data=('POST', self.ssh_keys_url, self._headers, payload))
                response = requests.post(self.ssh_keys_url, headers=self._headers, data=payload)
                self._log_response(response=response)
        logs.info('{} -- VHI: User SSH Keys has been migrated successfully --'.format(Helper.SPACES.value))
        logs.info('')
