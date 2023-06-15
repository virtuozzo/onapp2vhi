import unittest
from mock import patch, Mock

from onapp2vhi.inc.onapp_helpers import list_onapp_users, list_onapp_vms
from onapp2vhi.inc.rest_client import OnAppRequests
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.inc.utils import parse_matrix


class TestOnAppHelper(unittest.TestCase):

    def setUp(self):
        self.mock_config = Mock(spec=OnApp2VHIConfig)
        self.mock_onapprequests = Mock(spec=OnAppRequests)
        self.mock_parse_matrix = Mock(spec=parse_matrix)


class TestListOnAppUsers(TestOnAppHelper):

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
                }
            }
        ]

        mock_props = ['first_name', 'last_name', 'login', 'email', 'roles', 'id']
        expected_call = [['foo', 'bar', 'admin', 'test@test.com', 'test', '1']]

        self.mock_onapprequests.get.return_value = mock_response
        mock_onapp_request.return_value = self.mock_onapprequests
        list_onapp_users(self.mock_config)
        mock_parse_matrix.assert_called_with(mock_props, expected_call)

    @patch("onapp2vhi.inc.onapp_helpers.parse_matrix")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_list_onapp_user_with_props(self, mock_logs, mock_onapp_request, mock_parse_matrix):

        mock_response = [
            {
                'user': {
                    'first_name': 'foo',
                    'last_name': 'bar',
                    'email': 'test@test.com',
                    'roles': [{'role': {'label': 'test'}}],
                    'login': 'admin',
                    'id': '1',
                    'props_1': "test_1",
                    'props_2': "test_2",
                }
            }
        ]

        mock_props = ['first_name', 'last_name', 'login', 'email', 'roles', 'id', 'props_1', 'props_2']
        expected_call = [['foo', 'bar', 'admin', 'test@test.com', 'test', '1', 'test_1', 'test_2']]

        self.mock_onapprequests.get.return_value = mock_response
        mock_onapp_request.return_value = self.mock_onapprequests
        list_onapp_users(self.mock_config, props="props_1,props_2")
        mock_parse_matrix.assert_called_with(mock_props, expected_call)

    @patch("onapp2vhi.inc.onapp_helpers.parse_matrix")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_list_onapp_user_failed(self, mock_logs, mock_onapp_request, mock_parse_matrix):

        mock_response = []

        self.mock_onapprequests.get.return_value = mock_response
        mock_onapp_request.return_value = self.mock_onapprequests
        list_onapp_users(self.mock_config)
        mock_parse_matrix.assert_not_called()

    @patch("onapp2vhi.inc.onapp_helpers.parse_matrix")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_list_onapp_user_failed_find(self, mock_logs, mock_onapp_request, mock_parse_matrix):

        mock_response = [
            {
                'user': {
                    'first_name': 'foo',
                    'last_name': 'bar',
                    'email': 'test@test.com',
                    'roles': [{'role': {'label': 'test'}}],
                    'login': 'admin',
                    'id': '1',
                    'props_1': "test_1",
                    'props_2': "test_2",
                }
            }
        ]

        self.mock_onapprequests.get.return_value = mock_response
        mock_onapp_request.return_value = self.mock_onapprequests
        list_onapp_users(self.mock_config, find="first_name=foo1")
        mock_parse_matrix.assert_not_called()


class TestOnAppVms(TestOnAppHelper):

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
                    'props_1': "test_1",
                    'props_2': "test_2",
                }
            }
        ]

        mock_props = ['id', 'label', 'ip_address', 'identifier', 'template_label', 'booted', 'user_id', 'props_1', 'props_2']
        expected_call = [['1', 'ubuntu22', '1.2.3.4', 'test123', 'Ubuntu 22.04', 'false', '10', 'test_1', 'test_2']]

        self.mock_onapprequests.get.return_value = mock_response
        mock_onapp_request.return_value = self.mock_onapprequests
        list_onapp_vms(self.mock_config, props="props_1,props_2")
        mock_parse_matrix.assert_called_with(mock_props, expected_call)

    @patch("onapp2vhi.inc.onapp_helpers.parse_matrix")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_list_onapp_vms_with_props(self, mock_logs, mock_onapp_request, mock_parse_matrix):

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
                }
            }
        ]

        mock_props = ['id', 'label', 'ip_address', 'identifier', 'template_label', 'booted', 'user_id']
        expected_call = [['1', 'ubuntu22', '1.2.3.4', 'test123', 'Ubuntu 22.04', 'false', '10']]

        self.mock_onapprequests.get.return_value = mock_response
        mock_onapp_request.return_value = self.mock_onapprequests
        list_onapp_vms(self.mock_config)
        mock_parse_matrix.assert_called_with(mock_props, expected_call)

    @patch("onapp2vhi.inc.onapp_helpers.parse_matrix")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_list_onapp_vms_failed(self, mock_logs, mock_onapp_request, mock_parse_matrix):

        mock_response = []

        self.mock_onapprequests.get.return_value = mock_response
        mock_onapp_request.return_value = self.mock_onapprequests
        list_onapp_vms(self.mock_config)
        mock_parse_matrix.assert_not_called()

    @patch("onapp2vhi.inc.onapp_helpers.parse_matrix")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_list_onapp_vms_failed_find(self, mock_logs, mock_onapp_request, mock_parse_matrix):

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
                }
            }
        ]

        self.mock_onapprequests.get.return_value = mock_response
        mock_onapp_request.return_value = self.mock_onapprequests
        list_onapp_vms(self.mock_config, find="label=debian11")
        mock_parse_matrix.assert_not_called()
