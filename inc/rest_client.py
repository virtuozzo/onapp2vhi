import requests
import time

from inc.logger import logs
from cfg.config_parser import ONAPP_CREDS


class OnAppRequestsException(Exception):
    pass


def _response_handler(response: requests.Response):
    """
    Response handler manage response according to response status code
    :param response:
    :return: response as a json
    """
    allowed_status = [200, 201, 204]
    code = response.status_code
    text = response.text
    if code not in allowed_status:
        message = f"Status - [{code}] | Response: {text}"
        logs.error(message)
        raise OnAppRequestsException(message)

    if len(text) < 2500:
        logs.debug(f"Status - [{code}] | Response: {text}")
    else:
        logs.debug(f"Status - [{code}] | Response: . . . OUTPUT is TOO BIG [{len(text)}]. . .  ")
    return response.json()


class OnAppRequests:
    """
    This module is used for making an API requests to OnApp
    Choose your request method and give query(route) to find something
    """

    def __init__(self):
        self._cookie = ""
        self.log = logs
        self.url = ONAPP_CREDS["url"]
        self._email = ONAPP_CREDS["email"]
        self._api_key = ONAPP_CREDS["api_key"]
        self.authorization = (self._email, self._api_key)
        self._session = ''
        self._request_id = ''
        self._10_min_duration = float(60 * 10)
        self._start_time = None
        self.authorized = False

    @property
    def headers(self) -> dict:
        _session_time = time.time()
        _renew_session = round((_session_time - self._start_time), 1)
        if _renew_session >= self._10_min_duration:
            logs.debug('Renew SESSION_ID . . .')
            self._auth()
        _headers = {
            'Accept': 'application/json',
            'Content-type': 'application/json; charset=utf-8',
            'Connection': 'keep-alive',
        }
        if self._session:
            _headers.update({'Cookie': f'_session_id={self._session}'})
        if self._request_id:
            _headers.update({'X-Request-Id': self._request_id})
        return _headers

    def _auth(self):
        self._start_time = time.time()
        url = f"{self.url}/version.json"
        response = requests.get(url, auth=self.authorization)
        try:
            _response_handler(response)
            self._session = response.cookies['_session_id']
            self._request_id = response.headers['X-Request-Id']
            self.authorized = True
        except OnAppRequestsException as e:
            logs.error('Authorization failed. Please check out your credentials in "config.cfg" file')
            raise

    def _ensure_authorized(self):
        """
        Ensure session has been authorized
        """
        if not self.authorized:
            self._auth()

    def get(self, route: str, params: str = None):
        """
        :param route: users
        :param params: search_filter[user_id]=4
        :return: dict response
        """
        self._ensure_authorized()

        url = f"{self.url}/{route}.json"
        if params:
            url += f'?{params}'
        _headers = self.headers
        response = requests.get(url, auth=self.authorization, headers=_headers)
        self.log.debug(f"GET - {url}", separator=True)
        return _response_handler(response)

    def post(self, route: str, data: dict):
        """
        :param route: users/5
        :param data: {}
        :return: dict response
        """
        self._ensure_authorized()

        url = f"{self.url}/{route}.json"
        _headers = self.headers
        response = requests.post(url, headers=_headers, json=data, auth=self.authorization)
        self.log.debug(f"POST - {url} | data - {data}")
        return _response_handler(response)

    def put(self, route: str, data: dict):
        """
        :param route: users/5
        :param data: {}
        :return: dict response
        """
        self._ensure_authorized()

        url = f"{self.url}/{route}.json"
        _headers = self.headers
        response = requests.put(url, headers=_headers, json=data, auth=self.authorization)
        self.log.debug(f"PUT - {url} | data - {data}")
        return _response_handler(response)

    def patch(self, route: str, data: dict):
        """
        :param route: users/5
        :param data: {}
        :return: dict response
        """
        self._ensure_authorized()

        url = f"{self.url}/{route}.json"
        _headers = self.headers
        response = requests.patch(url, headers=_headers, json=data, auth=self.authorization)
        self.log.debug(f"PATCH - {url} | data - {data}")
        return _response_handler(response)

    def delete(self, route: str, data=None):
        """
        :param route: users/5.json
        :param data:{}
        :return: dict response
        """
        self._ensure_authorized()

        url = f"{self.url}/{route}.json"
        _headers = self.headers
        response = requests.delete(url, json=data, auth=self.authorization, _headers=_headers)
        self.log.debug(f"DELETE - {url} | data - {data}")
        return _response_handler(response)
