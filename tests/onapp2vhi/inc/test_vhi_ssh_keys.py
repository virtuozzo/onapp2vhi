import unittest

import requests_mock
from mock import Mock, mock_open, patch
from onapp2vhi.inc.vhi_ssh_keys import VhiSshKeys
from onapp2vhi.utilities.config import OnApp2VHIConfig

TEST_CFG = """
[onapp]
host = 69.168.239.170
url = http://onapp
api_key = here_is_yours_admin_api_key
email = onapp@gmail.com
cp_ssh_port = 2222
hv_ssh_port = 22

[vhi]
url = https://vhi
panel_url = https://cvhi.onappdev.com:8800
api_path = /api/v2
login = admin
admin_ui_pwd = ui_admin_password
hv_ip = 10.63.0.64
cp_ip = 10.63.0.63
network = public2
cloud_ssh_port = 2222
hv_ssh_port = 22
linux_image = debian-10-openstack-amd64.qcow2
windows_image = windows2012
domain_id = 58fa18b2cefc4bad8a52f11008dfbf72
vinfra_domain = Migration
vinfra_project = migproj
vinfra_user = user_login
vinfra_pass = user_pwd
vinfra_domain_user = domain_user
vinfra_domain_pass = domain_pass

[key]
ssh_key = path/to/your/ssh_key/id_rsa
"""


class TestVhiSshKeys(unittest.TestCase):
    @patch("builtins.open", mock_open(read_data=TEST_CFG))
    def setUp(self):
        self.cfg = OnApp2VHIConfig.load_config("test.ini")

        self.user_obj = {
            "user_login": "test_login",
            "first_name": "test_first_name",
            "last_name": "test_last_name",
            "password": "test_password",
            "project_name": "test_project_name",
            "roles": [{"role": {"identifier": "user", "permissions": "1234"}}],
        }

        self.admin_obj = {
            "user_login": "test_login",
            "first_name": "test_first_name",
            "last_name": "test_last_name",
            "password": "test_password",
            "project_name": "test_project_name",
            "roles": [
                {"role": {"identifier": "admin", "permissions": "1234"}}
            ],
        }

        self.ssh_keys = ["testkeys1", "testkeys2"]

    @patch("onapp2vhi.inc.vhi_ssh_keys.logs")
    def test_headers(self, mock_logs):
        vhi_ssh_keys = VhiSshKeys(self.cfg, self.user_obj, self.ssh_keys)
        result = {
            "Content-type": "application/json",
            "x-requested-with": "XMLHttpRequest",
            "Authorization": "access_token myToken",
            "accept": "application/json, text/plain, */*",
            "sec-fetch-mode": "cors",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "sec-fetch-site": "same-origin",
            "User-Agent": "Mozilla/5.0",
        }
        self.assertEqual(vhi_ssh_keys.headers, result)

    @patch("onapp2vhi.inc.vhi_ssh_keys.logs", autospec=True)
    def test_log_handler_url_data(self, mock_logs):
        vhi_ssh_keys = VhiSshKeys(self.cfg, self.user_obj, self.ssh_keys)
        url_data = {
            "method": "POST",
            "headers": "Cache-Control: public",
            "body": "touch_my_body",
        }

        self.assertTrue(vhi_ssh_keys._log_handler(**url_data))
        mock_logs.debug.assert_any_call("POST ", separator=True)
        mock_logs.debug.assert_any_call("Headers: Cache-Control: public")
        mock_logs.debug.assert_any_call("Payload: touch_my_body")

    @patch("onapp2vhi.inc.vhi_ssh_keys.logs", autospec=True)
    def test_log_handler_response(self, mock_logs):
        vhi_ssh_keys = VhiSshKeys(self.cfg, self.user_obj, self.ssh_keys)

        response = Mock()
        response.status_code = 200
        response.content = "test_content"

        self.assertTrue(vhi_ssh_keys._log_handler(response=response))
        mock_logs.debug.assert_called_once_with("Response [200]: test_content")

    @patch("onapp2vhi.inc.vhi_ssh_keys.logs", autospec=True)
    def test_log_handler_error_response(self, mock_logs):
        vhi_ssh_keys = VhiSshKeys(self.cfg, self.user_obj, self.ssh_keys)

        response = Mock()
        response.status_code = 400
        response.content = "error_content"

        self.assertFalse(vhi_ssh_keys._log_handler(response=response))
        mock_logs.error.assert_called_once_with(
            "Response [400]: error_content"
        )

    @requests_mock.Mocker()
    @patch("onapp2vhi.inc.vhi_ssh_keys.logs", autospec=True)
    def test_auth_user(self, mock_requests, mock_logs):
        mock_requests.post(
            "https://vhi/api/v2/login",
            status_code=200,
            content=b"test_content",
            cookies={"session1": "test_cookies"},
        )

        mock_requests.get(
            "https://vhi/api/v2/accounts/projects",
            json={"data": [{"id": "69", "name": "test_project_name"}]},
        )

        mock_requests.post(
            "https://cvhi.onappdev.com:8800/api/v2/accounts/projects/69/auth/",
            cookies={"session1": "test_cookies"},
        )

        vhi_ssh_keys = VhiSshKeys(self.cfg, self.user_obj, self.ssh_keys)
        self.assertTrue(vhi_ssh_keys._auth())

    @requests_mock.Mocker()
    @patch("onapp2vhi.inc.vhi_ssh_keys.logs", autospec=True)
    def test_auth_admin(self, mock_requests, mock_logs):
        mock_requests.post(
            "https://vhi/api/v2/login",
            status_code=200,
            content=b"test_content",
            cookies={"session1": "test_cookies"},
        )

        mock_requests.get(
            (
                "https://vhi/api/v2/domains/"
                "58fa18b2cefc4bad8a52f11008dfbf72/projects"
            ),
            json={"data": [{"id": "69", "name": "test_project_name"}]},
        )

        mock_requests.post(
            "https://cvhi.onappdev.com:8800/api/v2/accounts/projects/69/auth/",
            cookies={"session1": "test_cookies"},
        )

        vhi_ssh_keys = VhiSshKeys(self.cfg, self.admin_obj, self.ssh_keys)
        self.assertTrue(vhi_ssh_keys._auth())

    @requests_mock.Mocker()
    @patch("onapp2vhi.inc.vhi_ssh_keys.logs", autospec=True)
    def test_auth_error(self, mock_requests, mock_logs):
        mock_requests.post(
            "https://vhi/api/v2/login",
            status_code=400,
            content=b"test_content",
            cookies={"session1": "test_cookies"},
        )

        vhi_ssh_keys = VhiSshKeys(self.cfg, self.user_obj, self.ssh_keys)
        self.assertFalse(vhi_ssh_keys._auth())

    @requests_mock.Mocker()
    @patch("onapp2vhi.inc.vhi_ssh_keys.logs", autospec=True)
    def test_verify_ssh_keys_exists(self, mock_requests, mock_logs):
        mock_requests.post(
            "https://vhi/api/v2/login",
            status_code=200,
            content=b"test_content",
            cookies={"session1": "test_cookies"},
        )

        mock_requests.get(
            "https://vhi/api/v2/accounts/projects",
            json={"data": [{"id": "69", "name": "test_project_name"}]},
        )

        mock_requests.post(
            "https://cvhi.onappdev.com:8800/api/v2/accounts/projects/69/auth/",
            cookies={"session1": "test_cookies"},
        )

        mock_requests.get(
            "https://cvhi.onappdev.com:8800/api/v2/compute/keys",
            json={
                "data": [{"name": "name_ofk_key", "public_key": "testkeys1"}]
            },
        )

        vhi_ssh_keys = VhiSshKeys(self.cfg, self.user_obj, self.ssh_keys)
        self.assertEquals(vhi_ssh_keys._verify_ssh_keys(), ["testkeys2"])

    @requests_mock.Mocker()
    @patch("onapp2vhi.inc.vhi_ssh_keys.logs", autospec=True)
    def test_verify_ssh_keys_dont_exists(self, mock_requests, mock_logs):
        mock_requests.post(
            "https://vhi/api/v2/login",
            status_code=200,
            content=b"test_content",
            cookies={"session1": "test_cookies"},
        )

        mock_requests.get(
            "https://vhi/api/v2/accounts/projects",
            json={"data": [{"id": "69", "name": "test_project_name"}]},
        )

        mock_requests.post(
            "https://cvhi.onappdev.com:8800/api/v2/accounts/projects/69/auth/",
            cookies={"session1": "test_cookies"},
        )

        mock_requests.get(
            "https://cvhi.onappdev.com:8800/api/v2/compute/keys",
            json={"data": {}},
        )

        vhi_ssh_keys = VhiSshKeys(self.cfg, self.user_obj, self.ssh_keys)
        self.assertEquals(
            vhi_ssh_keys._verify_ssh_keys(), ["testkeys1", "testkeys2"]
        )

    @patch("onapp2vhi.inc.vhi_ssh_keys.logs", autospec=True)
    def test_ssh_key_payload(self, mock_logs):
        vhi_ssh_keys = VhiSshKeys(self.cfg, self.user_obj, self.ssh_keys)

        self.assertEquals(
            vhi_ssh_keys._vhi_ssh_keys_payload("1", "testkey"),
            (
                '{"name": "test_first_name_test_last_name_ssh_key_1", '
                '"description": "User test_first_name test_last_name '
                'SSH Key", "public_key": "testkey"}'
            ),
        )

    @patch("onapp2vhi.inc.vhi_ssh_keys.logs", autospec=True)
    def test_create_vhi_ssh_key_no_key(self, mock_logs):
        vhi_ssh_keys = VhiSshKeys(self.cfg, self.user_obj, "")
        vhi_ssh_keys.create_vhi_ssh_keys()
        mock_logs.warn.assert_called_once()

    @requests_mock.Mocker()
    @patch("onapp2vhi.inc.vhi_ssh_keys.logs", autospec=True)
    def test_create_vhi_ssh_key_with_key(self, mock_requests, mock_logs):
        vhi_ssh_keys = VhiSshKeys(self.cfg, self.user_obj, self.ssh_keys)

        mock_requests.post(
            "https://vhi/api/v2/login",
            status_code=200,
            content=b"test_content",
            cookies={"session1": "test_cookies"},
        )

        mock_requests.get(
            "https://vhi/api/v2/accounts/projects",
            json={"data": [{"id": "69", "name": "test_project_name"}]},
        )

        mock_requests.post(
            "https://cvhi.onappdev.com:8800/api/v2/accounts/projects/69/auth/",
            cookies={"session1": "test_cookies"},
        )

        mock_requests.get(
            "https://cvhi.onappdev.com:8800/api/v2/compute/keys",
            json={
                "data": [{"name": "name_ofk_key", "public_key": "testkeys1"}]
            },
        )

        mock_requests.post(
            "https://cvhi.onappdev.com:8800/api/v2/compute/keys",
        )

        self.assertTrue(vhi_ssh_keys.create_vhi_ssh_keys())
