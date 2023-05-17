import time
from unittest import TestCase
from mock import patch, Mock, call

from onapp2vhi.inc.rest_client import OnAppRequests
from onapp2vhi.utilities.config import OnApp2VHIConfig


# TODO! remove global inc.logger.logs references
class OnAppRequestTest(TestCase):

    @patch("onapp2vhi.inc.logger.logs")
    def setUp(self, mock_logs):
        mock_config = Mock(spec=OnApp2VHIConfig)
        mock_config._config = Mock()
        mock_config.onapp_conf = {
            "url": "https://onapp2vhi.unittest.test",
            "email": "unittest@onapp2vhi.unittest.test",
            "api_key": "dummy_api_key",
        }

        self.onapp_api = OnAppRequests(mock_config)

    @patch("requests.get")
    def test_onapprequests_get_not_authorized(self, mock_requests_get):
        mock_auth_response = Mock(name="mock_response",
                                  status_code=200,
                                  text="{'result': 'OK'}",
                                  cookies={'_session_id': 'dummy'},
                                  headers={'X-Request-Id': '123'})
        mock_command1_response = Mock(name="mock_response",
                                      status_code=200,
                                      text="{'result': 'OK'}",
                                      cookies={'_session_id': 'dummy'})
        mock_requests_get.side_effect = [
            mock_auth_response,
            mock_command1_response
        ]

        result = self.onapp_api.get('command1')

        mock_requests_get.assert_has_calls([
            call('https://onapp2vhi.unittest.test/version.json',
                 auth=('unittest@onapp2vhi.unittest.test', 'dummy_api_key')),
            call('https://onapp2vhi.unittest.test/command1.json',
                 auth=('unittest@onapp2vhi.unittest.test', 'dummy_api_key'),
                 headers={'Accept': 'application/json',
                          'Content-type': 'application/json; charset=utf-8',
                          'Connection': 'keep-alive',
                          'Cookie': '_session_id=dummy',
                          'X-Request-Id': '123'})
        ])
        self.assertIsNotNone(result)

    @patch("onapp2vhi.inc.rest_client.logs")
    @patch("requests.get")
    def test_onapprequests_get_failed_authorize(self, mock_requests_get, mock_logs):
        mock_auth_response = Mock(name="mock_response",
                                  status_code=403,
                                  text="{'result': 'Forbidden'}",
                                  cookies={'_session_id': 'dummy'},
                                  headers={'X-Request-Id': '123'})
        mock_requests_get.side_effect = [
            mock_auth_response,
        ]

        from onapp2vhi.inc.rest_client import OnAppRequestsException

        with self.assertRaises(OnAppRequestsException):
            result = self.onapp_api.get('command1')

            mock_requests_get.assert_has_calls([
                call('https://onapp2vhi.unittest.test/version.json',
                     auth=('unittest@onapp2vhi.unittest.test', 'dummy_api_key')),
            ])
            self.assertIsNotNone(result)

    @patch("requests.get")
    def test_onapprequests_get_already_authorized(self, mock_requests_get):
        mock_command1_response = Mock(name="mock_response",
                                      status_code=200,
                                      text="{'result': 'OK'}",
                                      cookies={'_session_id': 'dummy'})
        mock_requests_get.side_effect = [
            mock_command1_response
        ]

        with patch.object(self.onapp_api, "authorized") as mock_authorized:
            mock_authorized.return_value = True

            with patch.object(self.onapp_api, "_start_time", time.time()):
                result = self.onapp_api.get('command1')

        mock_requests_get.assert_has_calls([
            call('https://onapp2vhi.unittest.test/command1.json',
                 auth=('unittest@onapp2vhi.unittest.test', 'dummy_api_key'),
                 headers={'Accept': 'application/json',
                          'Content-type': 'application/json; charset=utf-8',
                          'Connection': 'keep-alive'})
        ])
        self.assertIsNotNone(result)

    @patch("requests.get")
    def test_onapprequests_get_with_params_already_authorized(self, mock_requests_get):
        mock_command1_response = Mock(name="mock_response",
                                      status_code=200,
                                      text="{'result': 'OK'}",
                                      cookies={'_session_id': 'dummy'})
        mock_requests_get.side_effect = [
            mock_command1_response
        ]

        with patch.object(self.onapp_api, "authorized") as mock_authorized:
            mock_authorized.return_value = True

            with patch.object(self.onapp_api, "_start_time", time.time()):
                result = self.onapp_api.get('command1', params="1=1")

        mock_requests_get.assert_has_calls([
            call('https://onapp2vhi.unittest.test/command1.json?1=1',
                 auth=('unittest@onapp2vhi.unittest.test', 'dummy_api_key'),
                 headers={'Accept': 'application/json',
                          'Content-type': 'application/json; charset=utf-8',
                          'Connection': 'keep-alive'})
        ])
        self.assertIsNotNone(result)

    @patch("requests.post")
    def test_onapprequests_post_already_authorized(self, mock_requests_post):
        mock_command1_response = Mock(name="mock_response",
                                      status_code=200,
                                      text="{'result': 'OK'}",
                                      cookies={'_session_id': 'dummy'})
        mock_requests_post.side_effect = [
            mock_command1_response
        ]

        with patch.object(self.onapp_api, "authorized") as mock_authorized:
            mock_authorized.return_value = True

            with patch.object(self.onapp_api, "_start_time", time.time()):
                result = self.onapp_api.post('command1', "data1")

        mock_requests_post.assert_has_calls([
            call('https://onapp2vhi.unittest.test/command1.json',
                 headers={'Accept': 'application/json',
                          'Content-type': 'application/json; charset=utf-8',
                          'Connection': 'keep-alive'},
                 json='data1',
                 auth=('unittest@onapp2vhi.unittest.test', 'dummy_api_key'))
        ])
        self.assertIsNotNone(result)

    @patch("requests.put")
    def test_onapprequests_put_already_authorized(self, mock_requests_put):
        mock_command1_response = Mock(name="mock_response",
                                      status_code=200,
                                      text="{'result': 'OK'}",
                                      cookies={'_session_id': 'dummy'})
        mock_requests_put.side_effect = [
            mock_command1_response
        ]

        with patch.object(self.onapp_api, "authorized") as mock_authorized:
            mock_authorized.return_value = True

            with patch.object(self.onapp_api, "_start_time", time.time()):
                result = self.onapp_api.put('command2', "data1")

        mock_requests_put.assert_has_calls([
            call('https://onapp2vhi.unittest.test/command2.json',
                 headers={'Accept': 'application/json',
                          'Content-type': 'application/json; charset=utf-8',
                          'Connection': 'keep-alive'},
                 json='data1',
                 auth=('unittest@onapp2vhi.unittest.test', 'dummy_api_key'))
        ])
        self.assertIsNotNone(result)

    @patch("requests.patch")
    def test_onapprequests_patch_already_authorized(self, mock_requests_patch):
        mock_command1_response = Mock(name="mock_response",
                                      status_code=200,
                                      text="{'result': 'OK'}",
                                      cookies={'_session_id': 'dummy'})
        mock_requests_patch.side_effect = [
            mock_command1_response
        ]

        with patch.object(self.onapp_api, "authorized") as mock_authorized:
            mock_authorized.return_value = True

            with patch.object(self.onapp_api, "_start_time", time.time()):
                result = self.onapp_api.patch('command2', "data1")

        mock_requests_patch.assert_has_calls([
            call('https://onapp2vhi.unittest.test/command2.json',
                 headers={'Accept': 'application/json',
                          'Content-type': 'application/json; charset=utf-8',
                          'Connection': 'keep-alive'},
                 json='data1',
                 auth=('unittest@onapp2vhi.unittest.test', 'dummy_api_key'))
        ])
        self.assertIsNotNone(result)

    @patch("requests.delete")
    def test_onapprequests_delete_already_authorized(self, mock_requests_delete):
        mock_command1_response = Mock(name="mock_response",
                                      status_code=200,
                                      text="{'result': 'OK'}",
                                      cookies={'_session_id': 'dummy'})
        mock_requests_delete.side_effect = [
            mock_command1_response
        ]

        with patch.object(self.onapp_api, "authorized") as mock_authorized:
            mock_authorized.return_value = True

            with patch.object(self.onapp_api, "_start_time", time.time()):
                result = self.onapp_api.delete('command2', "data1")

        mock_requests_delete.assert_has_calls([
            call('https://onapp2vhi.unittest.test/command2.json',
                 json='data1',
                 auth=('unittest@onapp2vhi.unittest.test', 'dummy_api_key'),
                 _headers={'Accept': 'application/json',
                           'Content-type': 'application/json; charset=utf-8',
                           'Connection': 'keep-alive'})
        ])
        self.assertIsNotNone(result)
