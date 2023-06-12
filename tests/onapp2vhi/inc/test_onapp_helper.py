import unittest
from mock import patch, Mock

from onapp2vhi.inc.onapp_helpers import list_onapp_users, list_onapp_vms
from onapp2vhi.inc.rest_client import OnAppRequests
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.inc.utils import parse_matrix


class TestListOnApp(unittest.TestCase):

    def setUp(self):
        self.mock_config = Mock(spec=OnApp2VHIConfig)
        self.mock_onapprequests = Mock(spec=OnAppRequests)
        self.mock_parse_matrix = Mock(spec=parse_matrix)
        self.list_user = list_onapp_users
        self.list_vms = list_onapp_vms

    @patch("onapp2vhi.inc.onapp_helpers.parse_matrix")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_list_onapp_user_ok(self, mock_logs, mock_onapp_request, mock_parse_matrix):

        mock_response = [
            {
              'user': {
                'first_name': 'foo',
                'last_name': 'bar',
                'email': 'test@test.com',
                'roles': [{'role': {'label': 'test'}}],
                'login': 'admin',
                'id': '1',
            }}
        ]

        mock_props = ['first_name', 'last_name', 'login', 'email', 'roles', 'id']
        expected_call = [['foo', 'bar', 'admin', 'test@test.com', 'test', '1']]

        self.mock_onapprequests.get.return_value = mock_response
        mock_onapp_request.return_value = self.mock_onapprequests
        self.list_user(self.mock_config)
        mock_parse_matrix.assert_called_with(mock_props, expected_call)


    @patch("onapp2vhi.inc.onapp_helpers.parse_matrix")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_list_onapp_user_failed(self, mock_logs, mock_onapp_request, mock_parse_matrix):

        mock_response = []

        self.mock_onapprequests.get.return_value = mock_response
        mock_onapp_request.return_value = self.mock_onapprequests
        self.list_user(self.mock_config)
        mock_parse_matrix.assert_not_called()


    @patch("onapp2vhi.inc.onapp_helpers.parse_matrix")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_list_onapp_vms_ok(self, mock_logs, mock_onapp_request, mock_parse_matrix):

        mock_response = [
            {
              'virtual_machine': {
                'label': 'ubuntu22',
                'ip_addresses': [{'ip_address': {'address': '1.2.3.4'}}],
                'identifier': 'test123',
                'template_label': 'Ubuntu 22.04',
                'booted': 'false',
                'user_id': '10',
                'id': '1',
            }}
        ]

        mock_props = ['id', 'label', 'ip_address', 'identifier', 'template_label', 'booted', 'user_id']
        expected_call = [['1', 'ubuntu22', '1.2.3.4', 'test123', 'Ubuntu 22.04', 'false', '10']]

        self.mock_onapprequests.get.return_value = mock_response
        mock_onapp_request.return_value = self.mock_onapprequests
        self.list_vms(self.mock_config)
        mock_parse_matrix.assert_called_with(mock_props, expected_call)


    @patch("onapp2vhi.inc.onapp_helpers.parse_matrix")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_list_onapp_vms_failed(self, mock_logs, mock_onapp_request, mock_parse_matrix):

        mock_response = []

        self.mock_onapprequests.get.return_value = mock_response
        mock_onapp_request.return_value = self.mock_onapprequests
        self.list_vms(self.mock_config)
        mock_parse_matrix.assert_not_called()
