import unittest
import json
from mock import patch, Mock, mock_open

from onapp2vhi.inc.onapp_helpers import (
    list_onapp_users,
    list_onapp_vms,
    get_all_virtual_machines,
    get_iface_from_specific_vs,
    attach_security_group_to_nic_and_enable_spoofing,
)
from onapp2vhi.inc.rest_client import OnAppRequests
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.inc.utils import parse_matrix
from onapp2vhi.inc.ssh_connector import SSH


TEST_CONFIG = """
[onapp]
host = dummy.onappdev.com
url = http://dummy.onappdev.com
api_key = dummy_api_key
email = unittest@virtuozzo.com
cp_ssh_port = 2222
hv_ssh_port = 22

[vhi]
url = https://vhi.onappdev.com:8888
panel_url = https://vhi-panel.onappdev.com:8800
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
vinfra_domain_user = ''
vinfra_domain_pass = ''

 Network ID for migration VM's, you can get it on VHI cloud
migration_network_id = 5afcb27b-1c92-4561-a81c-fcf4f89bd543

[key]
ssh_key = path/to/your/ssh_key/id_rsa
"""


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


class GetAllVirtualMachinesTestCase(unittest.TestCase):

    @patch("builtins.open", mock_open(read_data=TEST_CONFIG))
    def setUp(self):
        self.mock_cfg = OnApp2VHIConfig('test.ini')
        self.mock_onapprequests = Mock(spec=OnAppRequests)
        self.mock_ssh = Mock(spec=SSH)

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    def test_no_onapp_vms(self, mock_onapprequests):
        self.mock_onapprequests.get.side_effect = [[]]
        mock_onapprequests.return_value = self.mock_onapprequests

        self.assertFalse(get_all_virtual_machines(self.mock_cfg))

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    def test_with_unmigrate_onapp_vm(self, mock_onapprequests, mock_ssh):

        def onapprequestsget(param:str):
            if param == 'version':
                return {'version': '6.4.3.testbuild(1)'}
            elif param == 'virtual_machines':
                return [
                    { 'virtual_machine': {
                        'name': 'vm1',
                        'identifier': 'abcdef',
                        'ip_addresses': [
                            { 'ip_address': { 'address': '1.1.1.1', 'primary': False}, },
                            { 'ip_address': { 'address': '2.2.2.2', 'primary': True}, },
                            { 'ip_address': { 'address': '3.3.3.3', 'primary': False}, }
                        ],
                        'hostname': 'vm1',
                        'domain': 'localdomain',
                        'user_id': 11,
                        'booted': False,
                        'operating_system': 'centos7',
                        'built_from_iso': False,
                        'built_from_ova': False,
                        'label': 'testvm1',}
                      }
                ]
            else:
                raise RuntimeError('unhandled onapprequsets.get()')

        self.mock_onapprequests.get.side_effect = onapprequestsget
        self.mock_ssh.execute.side_effect = [
            (0, json.dumps([ {'name': 'vm1', 'domain_id': '58fa18b2cefc4bad8a52f11008dfbf72' } ])),
        ]
        mock_onapprequests.return_value = self.mock_onapprequests
        mock_ssh.return_value = self.mock_ssh

        expected = {
            11: [
                { 'id': 'abcdef', 'booted': False, 'ip_addr': '2.2.2.2', 'operating_system': 'centos7',
                  'hostname': 'vm1', 'domain': 'localdomain', 'built_from_iso': False,
                  'built_from_ova': False, 'label': 'testvm1' }
            ]
        }
        results = get_all_virtual_machines(self.mock_cfg)
        self.assertEquals(results, expected)

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    def test_with_old_onapp_version(self,
                                    mock_onapphelpers_onapprequests,
                                    mock_networkonapp_onapprequests,
                                    mock_ssh):

        def onapprequestsget(param:str):
            if param == 'version':
                return {'version': '5.9.9.testbuild(99)'}
            elif param == 'virtual_machines':
                return [
                    { 'virtual_machine': {
                        'name': 'vm1',
                        'identifier': 'abcdef',
                        'ip_addresses': [
                            { 'ip_address': { 'address': '1.1.1.1', 'primary': False}, },
                            { 'ip_address': { 'address': '2.2.2.2', 'primary': True}, },
                            { 'ip_address': { 'address': '3.3.3.3', 'primary': False}, }
                        ],
                        'hostname': 'vm1',
                        'domain': 'localdomain',
                        'user_id': 11,
                        'booted': False,
                        'operating_system': 'centos7',
                        'built_from_iso': False,
                        'built_from_ova': False,
                        'label': 'testvm1'}
                      }
                ]
            elif param == 'virtual_machines/abcdef/network_interfaces':
                return [
                    {
                        'network_interface': {
                            'id': 'eth0',
                            'primary': ['2.2.2.2'],
                        }
                    },
                ]
            elif param == 'virtual_machines/abcdef/ip_addresses':
                return [
                    {
                        'ip_address_join':
                        {
                            'ip_address': { 'address': '2.2.2.2'},
                            'network_interface_id': 'eth0'
                        }
                    }
                ]
            else:
                raise RuntimeError(f'unhandled onapprequsets.get({param})')

        self.mock_onapprequests.get.side_effect = onapprequestsget
        self.mock_ssh.execute.side_effect = [
            (0, json.dumps([ {'name': 'vm1', 'domain_id': '58fa18b2cefc4bad8a52f11008dfbf72' } ])),
        ]
        mock_onapphelpers_onapprequests.return_value = self.mock_onapprequests
        mock_networkonapp_onapprequests.return_value = self.mock_onapprequests
        mock_ssh.return_value = self.mock_ssh

        expected = {
            11: [
                { 'id': 'abcdef', 'booted': False, 'ip_addr': '2.2.2.2', 'operating_system': 'centos7',
                  'hostname': 'vm1', 'domain': 'localdomain', 'built_from_iso': False,
                  'built_from_ova': False, 'label': 'testvm1' }
            ]
        }
        results = get_all_virtual_machines(self.mock_cfg)
        self.assertEquals(results, expected)

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    def test_with_migrated_onapp_vm(self, mock_onapprequests, mock_ssh):

        def onapprequestsget(param:str):
            if param == 'version':
                return {'version': '6.4.3.testbuild(1)'}
            elif param == 'virtual_machines':
                return [
                    { 'virtual_machine': {
                        'name': 'vm1',
                        'identifier': 'abcdef',
                        'ip_addresses': [
                            { 'ip_address': { 'address': '1.1.1.1', 'primary': False}, },
                            { 'ip_address': { 'address': '2.2.2.2', 'primary': True}, },
                            { 'ip_address': { 'address': '3.3.3.3', 'primary': False}, }
                        ],
                        'hostname': 'vm1',
                        'domain': 'localdomain',
                        'user_id': 11,
                        'booted': False,
                        'operating_system': 'centos7',
                        'built_from_iso': False,
                        'built_from_ova': False,
                        'label': 'testvm1'}
                      }
                ]
            else:
                raise RuntimeError('unhandled onapprequsets.get()')

        self.mock_onapprequests.get.side_effect = onapprequestsget
        self.mock_ssh.execute.side_effect = [
            (0, json.dumps([ { 'name': 'vm1.localdomain',
                               'domain_id': '58fa18b2cefc4bad8a52f11008dfbf72' } ])),
        ]
        mock_onapprequests.return_value = self.mock_onapprequests
        mock_ssh.return_value = self.mock_ssh

        expected = {}
        results = get_all_virtual_machines(self.mock_cfg)
        self.assertEquals(results, expected)


class GetIfaceFromSpecificVSTestCase(unittest.TestCase):

    @patch("builtins.open", mock_open(read_data=TEST_CONFIG))
    def setUp(self):
        self.mock_cfg = OnApp2VHIConfig('test.ini')
        self.mock_ssh = Mock(spec=SSH)

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_get_iface_ok(self, mock_ssh):
        self.mock_ssh.execute.side_effect = [
            (0, json.dumps([{'id': 'eth0'}])),
        ]
        mock_ssh.return_value = self.mock_ssh
        expected = 'eth0'

        results = get_iface_from_specific_vs(self.mock_cfg, vm_name='vm1')

        self.assertEquals(results, expected)

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_get_iface_not_ok(self, mock_ssh):
        self.mock_ssh.execute.side_effect = [
            (0, json.dumps([])),
        ]
        mock_ssh.return_value = self.mock_ssh
        expected = False

        results = get_iface_from_specific_vs(self.mock_cfg, vm_name='vm1')

        self.assertEquals(results, expected)


class AttachSecurityGroupToNicAndEnableSpoofing(unittest.TestCase):

    @patch("builtins.open", mock_open(read_data=TEST_CONFIG))
    def setUp(self):
        self.mock_cfg = OnApp2VHIConfig('test.ini')
        self.mock_ssh = Mock(spec=SSH)

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_attach_ok(self, mock_ssh):
        mock_ssh_execute_results = (0, json.dumps([]))
        self.mock_ssh.execute.return_value = mock_ssh_execute_results
        mock_ssh.return_value = self.mock_ssh

        attach_security_group_to_nic_and_enable_spoofing(self.mock_cfg,
                                                         'vm1',
                                                         'eth0',
                                                         'security_group_a')
        #TODO! fix extra whitespace
        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service compute "
            "server iface set eth0  --server vm1 --spoofing-protection-enable "
            "--security-group security_group_a  -f json")

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_attach_no_security_group(self, mock_ssh):
        mock_ssh.return_value = self.mock_ssh

        self.assertFalse(attach_security_group_to_nic_and_enable_spoofing(self.mock_cfg,
                                                                          'vm1',
                                                                          'eth0',
                                                                          ''))
        self.mock_ssh.execute.assert_not_called()

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_attach_no_iface(self, mock_ssh):
        mock_ssh.return_value = self.mock_ssh

        self.assertFalse(attach_security_group_to_nic_and_enable_spoofing(self.mock_cfg,
                                                                          'vm1',
                                                                          '',
                                                                          'security_group_a'))
        self.mock_ssh.execute.assert_not_called()
