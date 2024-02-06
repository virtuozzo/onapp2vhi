import unittest
import json
from mock import patch, Mock, mock_open, call, ANY

from onapp2vhi.inc.onapp_helpers import (
    list_onapp_users,
    list_onapp_vms,
    get_onapp_vm_nics,
    get_onapp_vm_disks,
    get_onapp_vm_flavor,
    get_user_data,
    get_user_ssh_keys,
    get_all_virtual_machines,
    get_vm_source_properties,
    get_iface_from_specific_vs,
    attach_security_group_to_nic_and_enable_spoofing,
    check_sg_exists_in_project,
    transfer_firewall_rules_to_sg,
    create_new_vhi_vm,
    prepare_vhi_migration_data,
    verify_vm_user,
    GenerateXmlConfig,
)
from onapp2vhi.inc.vinfra_wrapper import (
    VinfraServer,
)
from onapp2vhi.inc.rest_client import OnAppRequests, OnAppRequestsException
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


class TestOnAppHelpers(unittest.TestCase):

    def setUp(self):
        self.mock_config = Mock(spec=OnApp2VHIConfig)
        self.mock_onapprequests = Mock(spec=OnAppRequests)
        self.mock_parse_matrix = Mock(spec=parse_matrix)


class TestListOnAppUsers(TestOnAppHelpers):

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


class TestOnAppVms(TestOnAppHelpers):

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


class TestOnAppGetVmNics(TestOnAppHelpers):

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_get_onapp_vm_nics_ok(self, mock_logs, mock_onapp_request):

        mock_nic_res = [
            {
                "network_interface": {
                    "id": "eth0",
                    "mac_address": "aa:bb:cc:dd",
                    "primary": ["1.2.3.4"]
                }
            }
        ]

        mock_ip_address = [
            {
                "ip_address_join": {
                    "network_interface_id": "eth0",
                    "ip_address": {
                        "address": "1.2.3.4"
                    }
                }
            },
            {
                "ip_address_join": {
                    "network_interface_id": "eth1",
                    "ip_address": {
                        "address": "1.2.3.5"
                    }
                }
            }
        ]

        expected_results = [{'id': "eth0", 'mac': 'aa:bb:cc:dd', 'primary': ["1.2.3.4"], 'ips': ['1.2.3.4']}]

        self.mock_onapprequests.get.side_effect = [mock_nic_res, mock_ip_address]
        mock_onapp_request.return_value = self.mock_onapprequests
        results = get_onapp_vm_nics(self.mock_config, "testtest123")

        self.assertEqual(results, expected_results)

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_get_onapp_vm_nics_none(self, mock_logs, mock_onapp_request):

        mock_nic_res = []

        mock_ip_address = [
            {
                "ip_address_join": {
                    "network_interface_id": "eth0",
                    "ip_address": {
                        "address": "1.2.3.5"
                    }
                }
            },
        ]

        expected_results = []

        self.mock_onapprequests.get.side_effect = [mock_nic_res, mock_ip_address]
        mock_onapp_request.return_value = self.mock_onapprequests
        results = get_onapp_vm_nics(self.mock_config, "testtest123")

        self.assertEqual(results, expected_results)


class TestOnAppGetDisk(TestOnAppHelpers):

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_get_onapp_vm_disk_ok(self, mock_logs, mock_onapp_request):

        mock_data_stores = [
            {
                "data_store": {
                    "id": "test123",
                    "identifier": "test",
                    "data_store_type": "test"
                }
            }
        ]

        mock_disks = [
            {
                "disk": {
                    "data_store_id": "test123",
                    "primary": ["1.2.3.4"],
                    "id": "test123",
                    "disk_vm_number": "test321",
                    "is_swap": "true",
                    "identifier": "vms",
                    "disk_size": "1024",
                }
            }
        ]

        expected_results = [
            {
                'datastore_idn': 'test',
                'number': 'test321',
                'is_swap': 'true',
                'primary': ["1.2.3.4"],
                'path': '/dev/test/vms',
                'ds_id': 'test123',
                'disk_idn': 'vms',
                'size': '1024',
                'datastore_type': 'test'
            }
        ]

        self.mock_onapprequests.get.side_effect = [mock_data_stores, mock_disks]
        mock_onapp_request.return_value = self.mock_onapprequests
        results = get_onapp_vm_disks(self.mock_config, "abcdtest123", False)

        self.assertEqual(results, expected_results)

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_get_onapp_vm_disk_non_primary(self, mock_logs, mock_onapp_request):

        mock_data_stores = [
            {
                "data_store": {
                    "id": "test123",
                    "identifier": "test",
                    "data_store_type": "test"
                }
            }
        ]

        mock_disks = [
            {
                "disk": {
                    "data_store_id": "test123",
                    "primary": "false",
                    "identifier": "test",
                }
            }
        ]

        expected_results = "/dev/test/test"

        self.mock_onapprequests.get.side_effect = [mock_data_stores, mock_disks]
        mock_onapp_request.return_value = self.mock_onapprequests
        results = get_onapp_vm_disks(self.mock_config, "abcdtest123", True)

        self.assertEqual(results, expected_results)


class TestOnAppGetVmFlavor(TestOnAppHelpers):

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_get_onapp_flavors_ok(self, mock_logs, mock_onapp_request):

        mock_results = {
            "virtual_machine":
            {
                "cpus": "test_cpu",
                "memory": "10",
            }
        }

        expected_results = {'vcpus': 'test_cpu', 'ram': '10', 'name': 'flavor_test_cpu_10'}

        self.mock_onapprequests.get.return_value = mock_results
        mock_onapp_request.return_value = self.mock_onapprequests
        results = get_onapp_vm_flavor(self.mock_config, "aabbcctest123")

        self.assertEqual(results, expected_results)


class TestGetUserSshKeys(TestOnAppHelpers):

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_get_user_ssh_keys_ok(self, mock_logs, mock_onapp_request):

        mock_results = [
            {
                "ssh_key": {
                    "key": "aabbccddeeff"
                }
            }
        ]

        expected_results = ['aabbccddeeff']

        self.mock_onapprequests.get.return_value = mock_results
        mock_onapp_request.return_value = self.mock_onapprequests
        results = get_user_ssh_keys(self.mock_config, {"id": 3, "first_name": "test1", "last_name": "test2"})

        self.assertEqual(results, expected_results)

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_get_user_ssh_keys_none(self, mock_logs, mock_onapp_request):

        mock_results = []

        expected_results = []

        self.mock_onapprequests.get.return_value = mock_results
        mock_onapp_request.return_value = self.mock_onapprequests
        results = get_user_ssh_keys(self.mock_config, {"id": 3, "first_name": "test1", "last_name": "test2"})

        self.assertEqual(results, expected_results)


class TestGetUserData(TestOnAppHelpers):

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_get_user_data_with_type(self, mock_logs, mock_onapp_request):

        mock_results = {
            "user": {
                "id": "1",
                "first_name": "test1",
                "last_name": "test2"
            }
        }
        self.mock_onapprequests.get.return_value = mock_results
        mock_onapp_request.return_value = self.mock_onapprequests

        expected_results = [{ "user": {'id': '1', 'first_name': 'test1', 'last_name': 'test2'}}]

        results = get_user_data(self.mock_config, url="users/1", get_type="ID")

        self.assertEqual(results, expected_results)

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_get_user_data_with_all_users(self, mock_logs, mock_onapp_request):

        mock_results = [
            {"user": {"id": "1", "first_name": "test1", "last_name": "test2"}},
            {"user": {"id": "2", "first_name": "test3", "last_name": "test4"}},
        ]

        self.mock_onapprequests.get.return_value = mock_results
        mock_onapp_request.return_value = self.mock_onapprequests

        expected_results = [{"user": {'id': '1', 'first_name': 'test1', 'last_name': 'test2'}},
                            {"user": {'id': '2', 'first_name': 'test3', 'last_name': 'test4'}}]

        results = get_user_data(self.mock_config, url="users", get_type="", all_users=True)

        self.assertEqual(results, expected_results)

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_get_user_data_with_value_to_search(self, mock_logs, mock_onapp_request):

        mock_results = [
            {"user": {"id": "1", "first_name": "test1", "last_name": "test2"}},
            {"user": {"id": "2", "first_name": "test3", "last_name": "test4"}},
        ]

        self.mock_onapprequests.get.return_value = mock_results
        mock_onapp_request.return_value = self.mock_onapprequests

        expected_results = {'id': '1', 'first_name': 'test1', 'last_name': 'test2'}

        results = get_user_data(self.mock_config, url="users", get_type="", value_to_search="test1")

        self.assertEqual(results, expected_results)

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.inc.onapp_helpers.logs")
    def test_get_user_data_return_none(self, mock_logs, mock_onapp_request):

        mock_results = []

        self.mock_onapprequests.get.return_value = mock_results
        mock_onapp_request.return_value = self.mock_onapprequests

        expected_results = False

        results = get_user_data(self.mock_config, url="users", get_type="",)

        self.assertEqual(results, expected_results)


class OnAppHelpersTestCase(unittest.TestCase):

    @patch("builtins.open", mock_open(read_data=TEST_CONFIG))
    def setUp(self):
        self.mock_cfg = OnApp2VHIConfig('test.ini')


class GetAllVirtualMachinesTestCase(OnAppHelpersTestCase):

    def setUp(self):
        super().setUp()
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
                        'vip': False,
                        'suspended': False,
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
                        'vip': False,
                        'suspended': False,
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
                        'vip': False,
                        'suspended': False,
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

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    def test_with_marked_vip_onapp_vm(self, mock_onapprequests, mock_ssh):

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
                        'vip': True,
                        'suspended': False,
                        'label': 'testvm1'}
                      }
                ]
            else:
                raise RuntimeError('unhandled onapprequsets.get()')

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    def test_with_suspended_onapp_vm(self, mock_onapprequests, mock_ssh):

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
                        'vip': False,
                        'suspended': True,
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

        results = get_all_virtual_machines(self.mock_cfg)
        self.assertFalse(results)


class GetVmSourcePropertiesTestCase(OnAppHelpersTestCase):

    def setUp(self):
        super().setUp()
        self.mock_onapprequests = Mock(spec=OnAppRequests, name='mock_onapprequests')

    @patch('onapp2vhi.inc.network_onapp.OnAppRequests')
    @patch('onapp2vhi.inc.onapp_helpers.OnAppRequests')
    def test_get_ok(self, mock_onapprequests1, mock_onapprequests2):

        def onapprequestsget(param:str):
            if param == 'virtual_machines/abcdef':
                return {
                    'virtual_machine': {
                        'hypervisor_id': 'testhv1',
                        'operating_system': 'centos7',
                        'allowed_hot_migrate': True,
                        'hostname': 'test-host',
                        'domain': 'localdomain',
                    }
                }
            elif param == 'virtual_machines/abcdef/network_interfaces':
                return [
                    {
                        'network_interface': {
                            'id': 'eth0',
                        }
                    },
                ]
            elif param == 'virtual_machines/abcdef/ip_addresses':
                return [
                    {
                        'ip_address_join': {
                            'network_interface_id': 'eth0',
                            'ip_address': {
                                'address': '2.3.2.4',
                                'primary': True,
                            }
                        }
                    },
                ]
            elif param == 'settings/hypervisors/testhv1':
                return {
                    'hypervisor': {
                        'ip_address': '1.1.2.2',
                    }
                }
            elif param == 'version':
                return {
                    'version': '6.4.1rc'
                }

            raise RuntimeError(f'unhandled onapprequsets.get({param})')

        self.mock_onapprequests.get.side_effect = onapprequestsget
        mock_onapprequests1.return_value = self.mock_onapprequests
        mock_onapprequests2.return_value = self.mock_onapprequests
        expected = {
            'domain': 'localdomain',
            'hostname': 'test-host',
            'hot_migrate': True,
            'hv_ip': '1.1.2.2',
            'network_info': { 'eth0': ['2.3.2.4'] },
            'vm_ip_addr': '2.3.2.4',
            'vm_os': 'centos7',
        }

        result = get_vm_source_properties(self.mock_cfg, 'abcdef')

        self.assertEqual(result, expected)


class CheckSecurityGroupExistsInProjectTestCase(OnAppHelpersTestCase):

    def setUp(self):
        super().setUp()
        self.mock_ssh_vinfra_security_groups = Mock(spec=SSH)
        self.mock_ssh_vinfra_project = Mock(spec=SSH)

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_security_group_exists(self, mock_ssh):
        self.mock_ssh_vinfra_project.execute.side_effect = [
            (0, json.dumps({'id': 'a-proj-id'})),
        ]
        self.mock_ssh_vinfra_security_groups.execute.side_effect = [
            (0, json.dumps([{'project_id': 'a-proj-id', 'id': 'a-sg-id'}])),
        ]

        mock_ssh.side_effect = [
            self.mock_ssh_vinfra_security_groups,
            self.mock_ssh_vinfra_project,
        ]

        self.assertTrue(check_sg_exists_in_project(self.mock_cfg, 'testprj', 'a-sg-id'))

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_security_group_doesnt_exists(self, mock_ssh):
        self.mock_ssh_vinfra_project.execute.side_effect = [
            (0, json.dumps({'id': 'a-proj-id'})),
        ]
        self.mock_ssh_vinfra_security_groups.execute.side_effect = [
            (0, json.dumps([{'project_id': 'a-proj-id', 'id': '1-sg-id'}])),
        ]

        mock_ssh.side_effect = [
            self.mock_ssh_vinfra_security_groups,
            self.mock_ssh_vinfra_project,
        ]

        self.assertFalse(check_sg_exists_in_project(self.mock_cfg, 'testprj', 'a-sg-id'))

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_diff_project(self, mock_ssh):
        self.mock_ssh_vinfra_project.execute.side_effect = [
            (0, json.dumps({'id': '1-proj-id'})),
        ]
        self.mock_ssh_vinfra_security_groups.execute.side_effect = [
            (0, json.dumps([{'project_id': 'a-proj-id', 'id': 'a-sg-id'}])),
        ]

        mock_ssh.side_effect = [
            self.mock_ssh_vinfra_security_groups,
            self.mock_ssh_vinfra_project,
        ]

        self.assertFalse(check_sg_exists_in_project(self.mock_cfg, 'testprj', 'a-sg-id'))


class TransferFirewallRulesToSecurityGroupTestCase(OnAppHelpersTestCase):

    def setUp(self):
        super().setUp()
        self.mock_onapprequests = Mock(spec=OnAppRequests, name='mock_onapprequests')
        self.mock_ssh_vinfra_security_group = Mock(spec=SSH, name='mock_visg')
        self.mock_ssh_vinfra_security_group_rules = Mock(spec=SSH, name='mock_visgr')
        self.mock_ssh_vinfra_project = Mock(spec=SSH, name='mock_vip')

    @patch('onapp2vhi.inc.onapp_helpers.OnAppRequests')
    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_transfer_ok_default_accept(self, mock_ssh, mock_onapprequests):

        def onapprequestsget(param:str):
            if param == 'virtual_machines/abcdef/network_interfaces':
                return [
                    {
                        'network_interface': {
                            'id': 'eth0',
                            'identifier': 'eth0',
                            'virtual_machine_id': 11,
                            'label': 'main iface',
                            'primary': ['2.2.2.2'],
                            'mac_address': 'aa:bb:cc:dd:ee:ff',
                            'network_join_id': 'eth0',
                            'default_firewall_rule': 'ACCEPT',
                            'connected': True,
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
            elif param == 'version':
                return {'version': '5.9.9.testbuild(99)'}
            elif param == 'virtual_machines/abcdef/firewall_rules':
                return [
                    { 'firewall_rule':
                        { 'id': 'rule1_id', 'position': 1, 'address': '1.2.3.4', 'command': 'DROP',
                          'port': '123,234', 'protocol': 'udp', 'network_interface_id': 'eth0',
                          'source_port': 65432, 'destination_ip': 'any', 'protocol_type': 'ipv4'}
                      },
                    { 'firewall_rule':
                        { 'id': 'rule2_id', 'position': 2, 'address': '2.3.4.5', 'command': 'ACCEPT',
                          'port': '80', 'protocol': 'tcp', 'network_interface_id': 'eth0',
                          'source_port': 54321, 'destination_ip': 'any', 'protocol_type': 'ipv4'}
                      },
                ]

            raise RuntimeError(f'unhandled onapprequsets.get({param})')

        self.mock_onapprequests.get.side_effect = onapprequestsget

        self.mock_ssh_vinfra_project.execute.side_effect = [
            (0, json.dumps({'id': 123})),
        ]
        self.mock_ssh_vinfra_security_group.execute.side_effect = [
            (0, json.dumps([])),                        # list security group
            (0, json.dumps({'name': 'test_grp', })),    # create security group
            (0, json.dumps([{'id': 'sec_grp_1'}])),     # list security group
            (0, json.dumps([{'id': 'sec_grp_1'}])),     # list security group, verify
        ]
        self.mock_ssh_vinfra_security_group_rules.execute.side_effect = [
            (0, json.dumps({'result': 'ok'})),  # port 80 rule
            (0, json.dumps({'result': 'ok'})),  # default rule
        ]

        mock_ssh.side_effect = [
            self.mock_ssh_vinfra_security_group,
            self.mock_ssh_vinfra_security_group_rules,
            self.mock_ssh_vinfra_project
        ]
        mock_onapprequests.return_value = self.mock_onapprequests
        expected = 'sec_grp_1'

        results = transfer_firewall_rules_to_sg(self.mock_cfg, 'abcdef', 'dummy_vhi_proj')

        self.assertEquals(results, expected)
        self.mock_ssh_vinfra_project.execute.assert_has_calls([
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' domain "
                 "project show --domain Migration dummy_vhi_proj -f json"),
        ])
        self.mock_ssh_vinfra_security_group.execute.assert_has_calls([
            # first check purposely return empty
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group list --project 123 -f json"),
            # security group creation
            call("vinfra --vinfra-username='domain_user' --vinfra-password='domain_pass' "
                 "--vinfra-domain='Migration' --vinfra-project='dummy_vhi_proj' service compute "
                 "security-group create sg_from_vs_abcdef_and_nic_eth0 "
                 "--description 'Security group created from the VS: abcdef with primary NIC: eth0' "
                 "-f json"),
            # verify creation
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group list --name test_grp -f json"),
            # get security group name
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group list --name test_grp -f json")
        ])
        self.mock_ssh_vinfra_security_group_rules.execute.assert_has_calls([
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group rule create test_grp --ethertype IPv4 --protocol tcp "
                 "--remote-ip 2.3.4.5 --port-range-min 80 --port-range-max 80 --ingress -f json"),
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group rule create test_grp --ethertype IPv4 --port-range-min 1 "
                 "--port-range-max 65535 --remote-ip 0.0.0.0/0 --ingress -f json"),
        ])

    @patch('onapp2vhi.inc.onapp_helpers.OnAppRequests')
    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_transfer_ok_default_drop(self, mock_ssh, mock_onapprequests):

        def onapprequestsget(param:str):
            if param == 'virtual_machines/abcdef/network_interfaces':
                return [
                    {
                        'network_interface': {
                            'id': 'eth0',
                            'identifier': 'eth0',
                            'virtual_machine_id': 11,
                            'label': 'main iface',
                            'primary': ['2.2.2.2'],
                            'mac_address': 'aa:bb:cc:dd:ee:ff',
                            'network_join_id': 'eth0',
                            'default_firewall_rule': 'DROP',
                            'connected': True,
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
            elif param == 'version':
                return {'version': '5.9.9.testbuild(99)'}
            elif param == 'virtual_machines/abcdef/firewall_rules':
                return [
                    { 'firewall_rule':
                        { 'id': 'rule1_id', 'position': 1, 'address': '1.2.3.4', 'command': 'DROP',
                          'port': '123,234', 'protocol': 'udp', 'network_interface_id': 'eth0',
                          'source_port': 65432, 'destination_ip': 'any', 'protocol_type': 'ipv4'}
                      },
                    { 'firewall_rule':
                        { 'id': 'rule2_id', 'position': 2, 'address': '2.3.4.5', 'command': 'ACCEPT',
                          'port': '80', 'protocol': 'tcp', 'network_interface_id': 'eth0',
                          'source_port': 54321, 'destination_ip': 'any', 'protocol_type': 'ipv4'}
                      },
                ]

            raise RuntimeError(f'unhandled onapprequsets.get({param})')

        self.mock_onapprequests.get.side_effect = onapprequestsget

        self.mock_ssh_vinfra_project.execute.side_effect = [
            (0, json.dumps({'id': 123})),
        ]
        self.mock_ssh_vinfra_security_group.execute.side_effect = [
            (0, json.dumps([])),                        # list security group
            (0, json.dumps({'name': 'test_grp', })),    # create security group
            (0, json.dumps([{'id': 'sec_grp_1'}])),     # list security group
            (0, json.dumps([{'id': 'sec_grp_1'}])),     # list security group, verify
        ]
        self.mock_ssh_vinfra_security_group_rules.execute.side_effect = [
            (0, json.dumps({'result': 'ok'})),  # port 80 rule
            (0, json.dumps({'result': 'ok'})),  # default rule
        ]

        mock_ssh.side_effect = [
            self.mock_ssh_vinfra_security_group,
            self.mock_ssh_vinfra_security_group_rules,
            self.mock_ssh_vinfra_project
        ]
        mock_onapprequests.return_value = self.mock_onapprequests
        expected = 'sec_grp_1'

        results = transfer_firewall_rules_to_sg(self.mock_cfg, 'abcdef', 'dummy_vhi_proj')

        self.assertEquals(results, expected)
        self.mock_ssh_vinfra_project.execute.assert_has_calls([
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' domain "
                 "project show --domain Migration dummy_vhi_proj -f json"),
        ])
        self.mock_ssh_vinfra_security_group.execute.assert_has_calls([
            # first check purposely return empty
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group list --project 123 -f json"),
            # security group creation
            call("vinfra --vinfra-username='domain_user' --vinfra-password='domain_pass' "
                 "--vinfra-domain='Migration' --vinfra-project='dummy_vhi_proj' service compute "
                 "security-group create sg_from_vs_abcdef_and_nic_eth0 "
                 "--description 'Security group created from the VS: abcdef with primary NIC: eth0' "
                 "-f json"),
            # verify creation
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group list --name test_grp -f json"),
            # get security group name
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group list --name test_grp -f json")
        ])
        self.mock_ssh_vinfra_security_group_rules.execute.assert_has_calls([
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group rule create test_grp --ethertype IPv4 --protocol tcp "
                 "--remote-ip 2.3.4.5 --port-range-min 80 --port-range-max 80 --ingress -f json"),
        ])

    @patch('onapp2vhi.inc.onapp_helpers.OnAppRequests')
    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_transfer_default_drop_others_all_accept(self, mock_ssh, mock_onapprequests):

        def onapprequestsget(param:str):
            if param == 'virtual_machines/abcdef/network_interfaces':
                return [
                    {
                        'network_interface': {
                            'id': 'eth0',
                            'identifier': 'eth0',
                            'virtual_machine_id': 11,
                            'label': 'main iface',
                            'primary': ['2.2.2.2'],
                            'mac_address': 'aa:bb:cc:dd:ee:ff',
                            'network_join_id': 'eth0',
                            'default_firewall_rule': 'DROP',
                            'connected': True,
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
            elif param == 'version':
                return {'version': '5.9.9.testbuild(99)'}
            elif param == 'virtual_machines/abcdef/firewall_rules':
                return [
                    { 'firewall_rule':
                        { 'id': 'rule1_id', 'position': 1, 'address': '1.2.3.4', 'command': 'ACCEPT',
                          'port': '123,234', 'protocol': 'udp', 'network_interface_id': 'eth0',
                          'source_port': 65432, 'destination_ip': 'any', 'protocol_type': 'ipv4'}
                      },
                    { 'firewall_rule':
                        { 'id': 'rule2_id', 'position': 2, 'address': '2.3.4.5', 'command': 'ACCEPT',
                          'port': '80', 'protocol': 'tcp', 'network_interface_id': 'eth0',
                          'source_port': 54321, 'destination_ip': 'any', 'protocol_type': 'ipv4'}
                      },
                ]

            raise RuntimeError(f'unhandled onapprequsets.get({param})')

        self.mock_onapprequests.get.side_effect = onapprequestsget

        self.mock_ssh_vinfra_project.execute.side_effect = [
            (0, json.dumps({'id': 123})),
        ]
        self.mock_ssh_vinfra_security_group.execute.side_effect = [
            (0, json.dumps([])),                        # list security group
            (0, json.dumps({'name': 'test_grp', })),    # create security group
            (0, json.dumps([{'id': 'sec_grp_1'}])),     # list security group
            (0, json.dumps([{'id': 'sec_grp_1'}])),     # list security group, verify
        ]
        self.mock_ssh_vinfra_security_group_rules.execute.side_effect = [
            (0, json.dumps({'result': 'ok'})),  # port 123 rule
            (0, json.dumps({'result': 'ok'})),  # port 234 rule
            (0, json.dumps({'result': 'ok'})),  # port 80 rule
        ]

        mock_ssh.side_effect = [
            self.mock_ssh_vinfra_security_group,
            self.mock_ssh_vinfra_security_group_rules,
            self.mock_ssh_vinfra_project
        ]
        mock_onapprequests.return_value = self.mock_onapprequests
        expected = 'sec_grp_1'

        results = transfer_firewall_rules_to_sg(self.mock_cfg, 'abcdef', 'dummy_vhi_proj')

        self.assertEquals(results, expected)
        self.mock_ssh_vinfra_project.execute.assert_has_calls([
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' domain "
                 "project show --domain Migration dummy_vhi_proj -f json"),
        ])
        self.mock_ssh_vinfra_security_group.execute.assert_has_calls([
            # first check purposely return empty
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group list --project 123 -f json"),
            # security group creation
            call("vinfra --vinfra-username='domain_user' --vinfra-password='domain_pass' "
                 "--vinfra-domain='Migration' --vinfra-project='dummy_vhi_proj' service compute "
                 "security-group create sg_from_vs_abcdef_and_nic_eth0 "
                 "--description 'Security group created from the VS: abcdef with primary NIC: eth0' "
                 "-f json"),
            # verify creation
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group list --name test_grp -f json"),
            # get security group name
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group list --name test_grp -f json")
        ])
        self.mock_ssh_vinfra_security_group_rules.execute.assert_has_calls([
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group rule create test_grp --ethertype IPv4 --protocol udp "
                 "--remote-ip 1.2.3.4 --port-range-min 234 --port-range-max 234 --ingress -f json"),
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group rule create test_grp --ethertype IPv4 --protocol udp "
                 "--remote-ip 1.2.3.4 --port-range-min 123 --port-range-max 123 --ingress -f json"),
            call("vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service "
                 "compute security-group rule create test_grp --ethertype IPv4 --protocol tcp "
                 "--remote-ip 2.3.4.5 --port-range-min 80 --port-range-max 80 --ingress -f json"),
        ], any_order=True)

    # TODO! cases not covered:
    # - vinfra operation failed, i.e: output = empty / None
    # - default firewall rule not in DROP/ACCEPT
    # - no rules to transfer
    # - security group already exists in vhi


class GetIfaceFromSpecificVSTestCase(OnAppHelpersTestCase):

    def setUp(self):
        super().setUp()
        self.mock_ssh = Mock(spec=SSH)

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_get_iface_ok(self, mock_ssh):
        self.mock_ssh.execute.side_effect = [
            (0, json.dumps([{'id': 'eth0'}])),
        ]
        mock_ssh.return_value = self.mock_ssh
        expected = [{'id': 'eth0'}]

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


class AttachSecurityGroupToNicAndEnableSpoofing(OnAppHelpersTestCase):

    def setUp(self):
        super().setUp()
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
        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service compute "
            "server iface set eth0 --server vm1 --spoofing-protection-enable "
            "--security-group security_group_a -f json")

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


class CreateNewVhiVmTestCase(OnAppHelpersTestCase):

    def setUp(self):
        super().setUp()
        self.mock_ssh = Mock(spec=SSH)

    def test_create_ok(self):
        mock_disks = [{ 'size': '5',},]
        mock_nics = [{ 'ips': ['1.1.1.1',],},]

        def mock_ssh_execute(command:str, real_data=False):
            if 'service compute server create' in command:
                return (0, json.dumps({'id': '1111-2222-3333-444444444444'}))
            elif 'for ((i=1;i<=100;i++))' in command:
                return (0, 'done')

            raise RuntimeError(f'Unhandled command: {command}')

        self.mock_ssh.execute.side_effect = mock_ssh_execute
        expected = '1111-2222-3333-444444444444'

        result = create_new_vhi_vm(self.mock_cfg, self.mock_ssh, 'vinfra vhi-creds', 'abcdef',
                                   'public2', 'vhi_image.qow', mock_disks, 'flavor_1_128', mock_nics,
                                   'test-server', 'localdomain', 'default')
        self.assertEqual(result, expected)

    def test_create_failed(self):
        mock_disks = [{ 'size': '5',},]
        mock_nics = [{ 'ips': ['1.1.1.1',],},]

        def mock_ssh_execute(command:str, real_data=False):
            if 'service compute server create' in command:
                return (1, 'create failed!')

            raise RuntimeError(f'Unhandled command: {command}')

        self.mock_ssh.execute.side_effect = mock_ssh_execute

        result = create_new_vhi_vm(self.mock_cfg, self.mock_ssh, 'vinfra vhi-creds', 'abcdef',
                                   'public2', 'vhi_image.qow', mock_disks, 'flavor_1_128', mock_nics,
                                   'test-server', 'localdomain', 'default')
        self.assertFalse(result)

    def test_create_stop_failed(self):
        mock_disks = [{ 'size': '5',},]
        mock_nics = [{ 'ips': ['1.1.1.1',],},]

        def mock_ssh_execute(command:str, real_data=False):
            if 'service compute server create' in command:
                return (0, json.dumps({'id': '1111-2222-3333-444444444444'}))
            elif 'for ((i=1;i<=100;i++))' in command:
                return (1, 'vm wont stop!')

            raise RuntimeError(f'Unhandled command: {command}')

        self.mock_ssh.execute.side_effect = mock_ssh_execute

        result = create_new_vhi_vm(self.mock_cfg, self.mock_ssh, 'vinfra vhi-creds', 'abcdef',
                                   'public2', 'vhi_image.qow', mock_disks, 'flavor_1_128', mock_nics,
                                   'test-server', 'localdomain', 'default')
        self.assertFalse(result)

    def test_create_ok_multiple_disk(self):
        mock_disks = [{ 'size': '5',}, { 'size': '2' }]
        mock_nics = [{ 'ips': ['1.1.1.1',],},]

        def mock_ssh_execute(command:str, real_data=False):
            if 'service compute server create' in command:
                return (0, json.dumps({'id': '1111-2222-3333-444444444444'}))
            elif 'for ((i=1;i<=100;i++))' in command:
                return (0, 'done')
            elif 'service compute volume create' in command:
                return (0, json.dumps({'id': 'wwww-qwerty-asdfghjkl'}))
            elif 'service compute server volume attach' in command:
                return (0, json.dumps({'result': 'ok'}))

            raise RuntimeError(f'Unhandled command: {command}')

        self.mock_ssh.execute.side_effect = mock_ssh_execute
        expected = '1111-2222-3333-444444444444'

        result = create_new_vhi_vm(self.mock_cfg, self.mock_ssh, 'vinfra vhi-creds', 'abcdef',
                                   'public2', 'vhi_image.qow', mock_disks, 'flavor_1_128', mock_nics,
                                   'test-server', 'localdomain', 'default')
        self.assertEqual(result, expected)

    def test_create_multiple_disk_volume_with_rm_by_default(self):
        mock_disks = [{ 'size': '5',}, { 'size': '2' }]
        mock_nics = [{ 'ips': ['1.1.1.1',],},]

        def mock_ssh_execute(command:str, real_data=False):
            if 'rm=yes,boot-index=1' in command:
                return (0, json.dumps({'id': '1111-2222-3333-444444444444'}))
            elif 'for ((i=1;i<=100;i++))' in command:
                return (0, 'done')

            raise RuntimeError(f'Unhandled command: {command}')

        self.mock_ssh.execute.side_effect = mock_ssh_execute

        result = create_new_vhi_vm(self.mock_cfg, self.mock_ssh, 'vinfra vhi-creds', 'abcdef',
                                   'public2', 'vhi_image.qow', mock_disks, 'flavor_1_128', mock_nics,
                                   'test-server', 'localdomain', 'default')
        self.assertTrue(result)

    def test_create_multiple_disk_without_rm(self):
        mock_disks = [{ 'size': '5',}, { 'size': '2' }]
        mock_nics = [{ 'ips': ['1.1.1.1',],},]

        def mock_ssh_execute(command:str, real_data=False):
            if 'rm=no,boot-index=1' in command:
                return (0, json.dumps({'id': '1111-2222-3333-444444444444'}))
            elif 'for ((i=1;i<=100;i++))' in command:
                return (0, 'done')

            raise RuntimeError(f'Unhandled command: {command}')

        self.mock_ssh.execute.side_effect = mock_ssh_execute

        write_mock = mock_open()
        with patch("builtins.open", write_mock):
            self.mock_cfg.update("vhi", "remove_disk_on_termination", "no")

        result = create_new_vhi_vm(self.mock_cfg, self.mock_ssh, 'vinfra vhi-creds', 'abcdef',
                                   'public2', 'vhi_image.qow', mock_disks, 'flavor_1_128', mock_nics,
                                   'test-server', 'localdomain', 'default')
        self.assertTrue(result)

    def test_create_ok_multi_ips(self):
        mock_disks = [{ 'size': '5',},]
        mock_nics = [{ 'ips': ['1.1.1.1', '2.2.2.2'],},]

        def mock_ssh_execute(command:str, real_data=False):
            if 'service compute server create' in command:
                return (0, json.dumps({'id': '1111-2222-3333-444444444444'}))
            elif 'for ((i=1;i<=100;i++))' in command:
                return (0, 'done')
            elif 'service compute server iface list' in command:
                return (
                    0,
                    json.dumps([ { 'id': 'eth0', }, { 'id': 'eth1', } ])
                )
            elif 'service compute server iface set' in command:
                return (0, 'ok')

            raise RuntimeError(f'Unhandled command: {command}')

        self.mock_ssh.execute.side_effect = mock_ssh_execute
        expected = '1111-2222-3333-444444444444'

        result = create_new_vhi_vm(self.mock_cfg, self.mock_ssh, 'vinfra vhi-creds', 'abcdef',
                                   'public2', 'vhi_image.qow', mock_disks, 'flavor_1_128', mock_nics,
                                   'test-server', 'localdomain', 'default')
        self.assertEqual(result, expected)

    def test_create_multi_ips_list_iface_failed(self):
        mock_disks = [{ 'size': '5',},]
        mock_nics = [{ 'ips': ['1.1.1.1', '2.2.2.2'],},]

        def mock_ssh_execute(command:str, real_data=False):
            if 'service compute server create' in command:
                return (0, json.dumps({'id': '1111-2222-3333-444444444444'}))
            elif 'for ((i=1;i<=100;i++))' in command:
                return (0, 'done')
            elif 'service compute server iface list' in command:
                return (1, 'list iface failed!')

            raise RuntimeError(f'Unhandled command: {command}')

        self.mock_ssh.execute.side_effect = mock_ssh_execute

        result = create_new_vhi_vm(self.mock_cfg, self.mock_ssh, 'vinfra vhi-creds', 'abcdef',
                                   'public2', 'vhi_image.qow', mock_disks, 'flavor_1_128', mock_nics,
                                   'test-server', 'localdomain', 'default')
        self.assertFalse(result)

    def test_create_multi_ips_set_iface_failed(self):
        mock_disks = [{ 'size': '5',},]
        mock_nics = [{ 'ips': ['1.1.1.1', '2.2.2.2'],},]

        def mock_ssh_execute(command:str, real_data=False):
            if 'service compute server create' in command:
                return (0, json.dumps({'id': '1111-2222-3333-444444444444'}))
            elif 'for ((i=1;i<=100;i++))' in command:
                return (0, 'done')
            elif 'service compute server iface list' in command:
                return (
                    0,
                    json.dumps([ { 'id': 'eth0', }, { 'id': 'eth1', } ])
                )
            elif 'service compute server iface set' in command:
                return (1, 'not ok')

            raise RuntimeError(f'Unhandled command: {command}')

        self.mock_ssh.execute.side_effect = mock_ssh_execute

        result = create_new_vhi_vm(self.mock_cfg, self.mock_ssh, 'vinfra vhi-creds', 'abcdef',
                                   'public2', 'vhi_image.qow', mock_disks, 'flavor_1_128', mock_nics,
                                   'test-server', 'localdomain', 'default')
        self.assertFalse(result)


class PrepareVhiMigrationDataTestCase(OnAppHelpersTestCase):

    def setUp(self):
        super().setUp()
        self.mock_onapprequests = Mock(spec=OnAppRequests)
        self.mock_vinfraserver = Mock(spec=VinfraServer)

    @patch('onapp2vhi.inc.onapp_helpers.VinfraServer')
    @patch('onapp2vhi.inc.onapp_helpers.OnAppRequests')
    def test_prepare_migration_data_all_users(self, mock_onapprequests, mock_vinfraserver):
        mock_onapprequests.return_value = self.mock_onapprequests
        mock_vinfraserver.return_value = self.mock_vinfraserver

        self.mock_vinfraserver.list_server.return_value = json.dumps([
            {'name': 'vm1', 'domain_id': '58fa18b2cefc4bad8a52f11008dfbf72'},
        ])

        def mock_onapprequests_get(path: str):
            if path == 'users':
                return [
                    {
                        'user': {
                            'login': 'testuser',
                            'email': 'testuser@unit.onapp2vhi.test',
                            'id': 13,
                            'first_name': 'test',
                            'last_name': 'user',
                            'roles': ['Admin', 'user'],
                            'bucket_id': 'abc123',
                        }
                    },
                ]
            elif path == 'virtual_machines':
                return [
                    {
                        'virtual_machine': {
                            'identifier': 'abcdef',
                            'label': 'test-vm1-label',
                            'hostname': 'test-vm1',
                            'domain': 'testdomain',
                            'user_id': 13,
                            'ip_addresses': [],
                            'booted': True,
                            'operating_system': 'centos7',
                            'built_from_iso': False,
                            'built_from_ova': False,
                            'vip': False,
                            'suspended': False,
                        },
                    },
                ]
            elif path == 'billing/buckets/abc123/access_controls':
                return [
                    {
                        'access_control': {
                            'type': 'compute_zone_resource',
                            'server_type': 'virtual',
                            'limits': {
                                'limit_memory': '4096',
                                'limit_cpu': '4',
                            },
                            'target_name': 'sample compute target name',
                        }
                    },
                    {
                        'access_control': {
                            'type': 'data_store_zone_resource',
                            'limits': {
                                'limit': '40',
                            },
                            'target_name': 'sample datastore target name',
                        }
                    }
                ]
            elif path == 'version':
                return {'version': '6.4.12345-unittest'}

            raise RuntimeError('unhandled path = {path}'.format(path=path))

        self.mock_onapprequests.get.side_effect = mock_onapprequests_get
        expected = [{'first_name': 'test',
                     'id': 13,
                     'last_name': 'user',
                     'password': ANY,
                     'project_name': 'project_testuser@unit.onapp2vhi.test',
                     'quotas': {'cores': 4, 'ram-size': 4398046511104, 'storage': 40},
                     'roles': ['Admin', 'user'],
                     'user_email': 'testuser@unit.onapp2vhi.test',
                     'user_login': 'testuser',
                     'virtual_machines': [{'booted': True,
                                           'built_from_iso': False,
                                           'built_from_ova': False,
                                           'domain': 'testdomain',
                                           'hostname': 'test-vm1',
                                           'id': 'abcdef',
                                           'ip_addr': None,
                                           'label': 'test-vm1-label',
                                           'operating_system': 'centos7'}]}]

        result = prepare_vhi_migration_data(self.mock_cfg)

        self.assertNotEqual(result, [])
        self.assertTrue(isinstance(result, list))
        self.assertEqual(result, expected)

    @patch('onapp2vhi.inc.onapp_helpers.VinfraServer')
    @patch('onapp2vhi.inc.onapp_helpers.OnAppRequests')
    def test_prepare_migration_data_all_users_no_vm(self, mock_onapprequests, mock_vinfraserver):
        mock_onapprequests.return_value = self.mock_onapprequests
        mock_vinfraserver.return_value = self.mock_vinfraserver

        self.mock_vinfraserver.list_server.return_value = json.dumps([
            {'name': 'vm1', 'domain_id': '58fa18b2cefc4bad8a52f11008dfbf72'},
        ])

        def mock_onapprequests_get(path: str):
            if path == 'users':
                return [
                    {
                        'user': {
                            'login': 'testuser',
                            'email': 'testuser@unit.onapp2vhi.test',
                            'id': 13,
                            'first_name': 'test',
                            'last_name': 'user',
                            'roles': ['Admin', 'user'],
                            'bucket_id': 'abc123',
                        }
                    },
                    {
                        'user': {   # user has no vm
                            'login': 'dummy',
                            'email': 'dummy@unit.onapp2vhi.test',
                            'id': 14,
                            'first_name': 'dum',
                            'last_name': 'my',
                            'roles': ['Admin', 'user'],
                            'bucket_id': 'abc123',
                        }
                    },
                ]
            elif path == 'virtual_machines':
                return [
                    {
                        'virtual_machine': {
                            'identifier': 'abcdef',
                            'label': 'test-vm1-label',
                            'hostname': 'test-vm1',
                            'domain': 'testdomain',
                            'user_id': 13,
                            'ip_addresses': [],
                            'booted': True,
                            'operating_system': 'centos7',
                            'built_from_iso': False,
                            'built_from_ova': False,
                            'vip': False,
                            'suspended': False,
                        },
                    },
                ]
            elif path == 'billing/buckets/abc123/access_controls':
                return [
                    {
                        'access_control': {
                            'type': 'compute_zone_resource',
                            'server_type': 'virtual',
                            'limits': {
                                'limit_memory': '4096',
                                'limit_cpu': '4',
                            },
                            'target_name': 'sample compute target name',
                        }
                    },
                    {
                        'access_control': {
                            'type': 'data_store_zone_resource',
                            'limits': {
                                'limit': '40',
                            },
                            'target_name': 'sample datastore target name',
                        }
                    }
                ]
            elif path == 'version':
                return {'version': '6.4.12345-unittest'}

            raise RuntimeError('unhandled path = {path}'.format(path=path))

        self.mock_onapprequests.get.side_effect = mock_onapprequests_get
        expected = [{'first_name': 'test',
                     'id': 13,
                     'last_name': 'user',
                     'password': ANY,
                     'project_name': 'project_testuser@unit.onapp2vhi.test',
                     'quotas': {'cores': 4, 'ram-size': 4398046511104, 'storage': 40},
                     'roles': ['Admin', 'user'],
                     'user_email': 'testuser@unit.onapp2vhi.test',
                     'user_login': 'testuser',
                     'virtual_machines': [{'booted': True,
                                           'built_from_iso': False,
                                           'built_from_ova': False,
                                           'domain': 'testdomain',
                                           'hostname': 'test-vm1',
                                           'id': 'abcdef',
                                           'ip_addr': None,
                                           'label': 'test-vm1-label',
                                           'operating_system': 'centos7'}]},
                    {'first_name': 'dum',
                     'id': 14,
                     'last_name': 'my',
                     'password': ANY,
                     'project_name': 'project_dummy@unit.onapp2vhi.test',
                     'quotas': {'cores': 4, 'ram-size': 4398046511104, 'storage': 40},
                     'roles': ['Admin', 'user'],
                     'user_email': 'dummy@unit.onapp2vhi.test',
                     'user_login': 'dummy',
                     'virtual_machines': []}]

        result = prepare_vhi_migration_data(self.mock_cfg)

        self.maxDiff = None
        self.assertNotEqual(result, [])
        self.assertTrue(isinstance(result, list))
        self.assertEqual(result, expected)

    @patch('onapp2vhi.inc.onapp_helpers.VinfraServer')
    @patch('onapp2vhi.inc.onapp_helpers.OnAppRequests')
    def test_prepare_migration_data_for_a_user(self, mock_onapprequests, mock_vinfraserver):
        mock_onapprequests.return_value = self.mock_onapprequests
        mock_vinfraserver.return_value = self.mock_vinfraserver

        self.mock_vinfraserver.list_server.return_value = json.dumps([
            {'name': 'vm1', 'domain_id': '58fa18b2cefc4bad8a52f11008dfbf72'},
        ])

        def mock_onapprequests_get(path: str, params: str = None):
            if path == 'users/1':
                return {
                    'user': {
                        'login': 'tester',
                        'email': 'tester@unit.onapp2vhi.test',
                        'id': 1,
                        'first_name': 'test',
                        'last_name': 'er',
                        'roles': ['Admin', 'user'],
                        'bucket_id': 'abc123',
                    }
                }
            elif path == 'virtual_machines':
                return [
                    {
                        'virtual_machine': {
                            'identifier': 'abcdef',
                            'label': 'test-vm1-label',
                            'hostname': 'test-vm1',
                            'domain': 'testdomain',
                            'user_id': 1,
                            'ip_addresses': [
                                {
                                    'ip_address': {
                                        'address': '1.2.3.4',
                                        'primary': True,
                                    }
                                }
                            ],
                            'booted': True,
                            'operating_system': 'centos7',
                            'built_from_iso': False,
                            'built_from_ova': False,
                            'vip': False,
                            'suspended': False,
                        },
                    },
                ]
            elif path == 'billing/buckets/abc123/access_controls':
                return [
                    {
                        'access_control': {
                            'type': 'compute_zone_resource',
                            'server_type': 'virtual',
                            'limits': {
                                'limit_memory': '4096',
                                'limit_cpu': '4',
                            },
                            'target_name': 'sample compute target name',
                        }
                    },
                    {
                        'access_control': {
                            'type': 'data_store_zone_resource',
                            'limits': {
                                'limit': '40',
                            },
                            'target_name': 'sample datastore target name',
                        }
                    }
                ]
            elif path == 'version':
                return {'version': '6.4.12345-unittest'}

            raise RuntimeError('unhandled path = {path}'.format(path=path))

        self.mock_onapprequests.get.side_effect = mock_onapprequests_get
        expected = [{'first_name': 'test',
                     'id': 1,
                     'last_name': 'er',
                     'password': ANY,
                     'project_name': 'project_tester@unit.onapp2vhi.test',
                     'quotas': {'cores': 4, 'ram-size': 4398046511104, 'storage': 40},
                     'roles': ['Admin', 'user'],
                     'user_email': 'tester@unit.onapp2vhi.test',
                     'user_login': 'tester',
                     'virtual_machines': [{'booted': True,
                                           'built_from_iso': False,
                                           'built_from_ova': False,
                                           'domain': 'testdomain',
                                           'hostname': 'test-vm1',
                                           'id': 'abcdef',
                                           'ip_addr': '1.2.3.4',
                                           'label': 'test-vm1-label',
                                           'operating_system': 'centos7'}]}]

        result = prepare_vhi_migration_data(self.mock_cfg, 1)

        self.assertNotEqual(result, [])
        self.assertTrue(isinstance(result, list))
        self.assertEqual(result, expected)

    @patch('onapp2vhi.inc.onapp_helpers.VinfraServer')
    @patch('onapp2vhi.inc.onapp_helpers.OnAppRequests')
    def test_prepare_migration_data_user_not_found(self, mock_onapprequests, mock_vinfraserver):
        mock_onapprequests.return_value = self.mock_onapprequests
        mock_vinfraserver.return_value = self.mock_vinfraserver

        self.mock_vinfraserver.list_server.return_value = json.dumps([
            {'name': 'vm1', 'domain_id': '58fa18b2cefc4bad8a52f11008dfbf72'},
        ])

        def mock_onapprequests_get(path: str, params: str = None):
            if path == 'users/1':
                return None
            elif path == 'virtual_machines':
                return [
                    {
                        'virtual_machine': {
                            'identifier': 'abcdef',
                            'label': 'test-vm1-label',
                            'hostname': 'test-vm1',
                            'domain': 'testdomain',
                            'user_id': 13,
                            'ip_addresses': [
                                {
                                    'ip_address': {
                                        'address': '1.2.3.4',
                                        'primary': True,
                                    }
                                }
                            ],
                            'booted': True,
                            'operating_system': 'centos7',
                            'built_from_iso': False,
                            'built_from_ova': False,
                            'vip': False,
                            'suspended': False,
                        },
                    },
                ]
            elif path == 'version':
                return {'version': '6.4.12345-unittest'}

            raise RuntimeError('unhandled path = {path}'.format(path=path))

        self.mock_onapprequests.get.side_effect = mock_onapprequests_get

        result = prepare_vhi_migration_data(self.mock_cfg, 1)
        self.assertFalse(result)

    @patch('onapp2vhi.inc.onapp_helpers.VinfraServer')
    @patch('onapp2vhi.inc.onapp_helpers.OnAppRequests')
    def test_prepare_migration_data_user_has_no_vm(self, mock_onapprequests, mock_vinfraserver):
        mock_onapprequests.return_value = self.mock_onapprequests
        mock_vinfraserver.return_value = self.mock_vinfraserver

        self.mock_vinfraserver.list_server.return_value = json.dumps([
            {'name': 'vm1', 'domain_id': '58fa18b2cefc4bad8a52f11008dfbf72'},
        ])

        def mock_onapprequests_get(path: str, params: str = None):
            if path == 'users/1':
                return {
                    'user': {
                        'login': 'tester',
                        'email': 'tester@unit.onapp2vhi.test',
                        'id': 1,
                        'first_name': 'test',
                        'last_name': 'er',
                        'roles': ['Admin', 'user'],
                        'bucket_id': 'abc123',
                    }
                }
            elif path == 'virtual_machines':
                return []

            raise RuntimeError('unhandled path = {path}'.format(path=path))

        self.mock_onapprequests.get.side_effect = mock_onapprequests_get

        result = prepare_vhi_migration_data(self.mock_cfg, 1)
        self.assertFalse(result)

    @patch('onapp2vhi.inc.onapp_helpers.VinfraServer')
    @patch('onapp2vhi.inc.onapp_helpers.OnAppRequests')
    def test_prepare_migration_data_with_vm_id(self, mock_onapprequests, mock_vinfraserver):
        mock_onapprequests.return_value = self.mock_onapprequests
        mock_vinfraserver.return_value = self.mock_vinfraserver

        self.mock_vinfraserver.list_server.return_value = json.dumps([
            {'name': 'vm1', 'domain_id': '58fa18b2cefc4bad8a52f11008dfbf72'},
        ])

        def mock_onapprequests_get(path: str, params: str = None):
            if path == 'virtual_machines/abcdef':
                return {
                    'virtual_machine': {
                        'identifier': 'abcdef',
                        'label': 'test-vm1-label',
                        'hostname': 'test-vm1',
                        'domain': 'testdomain',
                        'user_id': 13,
                        'ip_addresses': [
                            {
                                'ip_address': {
                                    'address': '1.2.3.4',
                                    'primary': True,
                                }
                            }
                        ],
                        'booted': True,
                        'operating_system': 'centos7',
                        'built_from_iso': False,
                        'built_from_ova': False,
                        'vip': False,
                        'suspended': False,
                    },
                }
            elif path == 'users/13':
                return {
                    'user': {
                        'login': 'tester',
                        'email': 'tester@unit.onapp2vhi.test',
                        'id': 13,
                        'first_name': 'test',
                        'last_name': 'er',
                        'roles': ['Admin', 'user'],
                        'bucket_id': 'abc123',
                    }
                }
            elif path == 'billing/buckets/abc123/access_controls':
                return [
                    {
                        'access_control': {
                            'type': 'compute_zone_resource',
                            'server_type': 'virtual',
                            'limits': {
                                'limit_memory': '4096',
                                'limit_cpu': '4',
                            },
                            'target_name': 'sample compute target name',
                        }
                    },
                    {
                        'access_control': {
                            'type': 'data_store_zone_resource',
                            'limits': {
                                'limit': '40',
                            },
                            'target_name': 'sample datastore target name',
                        }
                    }
                ]
            elif path == 'version':
                return {'version': '6.4.12345-unittest'}

            raise RuntimeError('unhandled path = {path}'.format(path=path))

        self.mock_onapprequests.get.side_effect = mock_onapprequests_get
        expected = [{'first_name': 'test',
                     'id': 13,
                     'last_name': 'er',
                     'password': ANY,
                     'project_name': 'project_tester@unit.onapp2vhi.test',
                     'quotas': {'cores': 4, 'ram-size': 4398046511104, 'storage': 40},
                     'roles': ['Admin', 'user'],
                     'user_email': 'tester@unit.onapp2vhi.test',
                     'user_login': 'tester',
                     'virtual_machines': [{'booted': True,
                                           'built_from_iso': False,
                                           'built_from_ova': False,
                                           'domain': 'testdomain',
                                           'hostname': 'test-vm1',
                                           'id': 'abcdef',
                                           'ip_addr': '1.2.3.4',
                                           'label': 'test-vm1-label',
                                           'operating_system': 'centos7'}]}]

        result = prepare_vhi_migration_data(self.mock_cfg, vm_idn='abcdef')
        self.assertEqual(result, expected)

    @patch('onapp2vhi.inc.onapp_helpers.VinfraServer')
    @patch('onapp2vhi.inc.onapp_helpers.OnAppRequests')
    def test_prepare_migration_data_with_vm_not_found(self, mock_onapprequests, mock_vinfraserver):
        mock_onapprequests.return_value = self.mock_onapprequests
        mock_vinfraserver.return_value = self.mock_vinfraserver

        self.mock_vinfraserver.list_server.return_value = json.dumps([
            {'name': 'vm1', 'domain_id': '58fa18b2cefc4bad8a52f11008dfbf72'},
        ])

        def mock_onapprequests_get(path: str, params: str = None):

            if path == 'virtual_machines/abcdef':
                raise OnAppRequestsException('404, vm not found')

            raise RuntimeError('unhandled path = {path}'.format(path=path))

        self.mock_onapprequests.get.side_effect = mock_onapprequests_get

        result = prepare_vhi_migration_data(self.mock_cfg, vm_idn='abcdef')
        self.assertFalse(result)

    @patch("onapp2vhi.inc.onapp_helpers.VinfraServer")
    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    def test_prepare_migration_data_with_multiple_vm_id(
        self, mock_onapprequests, mock_vinfraserver
    ):
        mock_onapprequests.return_value = self.mock_onapprequests
        mock_vinfraserver.return_value = self.mock_vinfraserver

        self.mock_vinfraserver.list_server.return_value = json.dumps(
            [
                {
                    "name": "vm1",
                    "domain_id": "58fa18b2cefc4bad8a52f11008dfbf72",
                },
            ]
        )

        def mock_onapprequests_get(path: str, params: str = None):
            if path == "virtual_machines/abcdef":
                return {
                    "virtual_machine": {
                        "identifier": "abcdef",
                        "label": "test-vm1-label",
                        "hostname": "test-vm1",
                        "domain": "testdomain",
                        "user_id": 13,
                        "ip_addresses": [
                            {
                                "ip_address": {
                                    "address": "1.2.3.4",
                                    "primary": True,
                                }
                            }
                        ],
                        "booted": True,
                        "operating_system": "centos7",
                        "built_from_iso": False,
                        "built_from_ova": False,
                        "vip": False,
                        "suspended": False,
                    },
                }
            elif path == "virtual_machines/hijklmn":
                return {
                    "virtual_machine": {
                        "identifier": "hijklmn",
                        "label": "test-vm2-label",
                        "hostname": "test-vm2",
                        "domain": "testdomain",
                        "user_id": 13,
                        "ip_addresses": [
                            {
                                "ip_address": {
                                    "address": "1.2.3.5",
                                    "primary": True,
                                }
                            }
                        ],
                        "booted": True,
                        "operating_system": "centos7",
                        "built_from_iso": False,
                        "built_from_ova": False,
                        "vip": False,
                        "suspended": False,
                    },
                }

            elif path == "users/13":
                return {
                    "user": {
                        "login": "tester",
                        "email": "tester@unit.onapp2vhi.test",
                        "id": 13,
                        "first_name": "test",
                        "last_name": "er",
                        "roles": ["Admin", "user"],
                        "bucket_id": "abc123",
                    }
                }
            elif path == "billing/buckets/abc123/access_controls":
                return [
                    {
                        "access_control": {
                            "type": "compute_zone_resource",
                            "server_type": "virtual",
                            "limits": {
                                "limit_memory": "4096",
                                "limit_cpu": "4",
                            },
                            "target_name": "sample compute target name",
                        }
                    },
                    {
                        "access_control": {
                            "type": "data_store_zone_resource",
                            "limits": {
                                "limit": "40",
                            },
                            "target_name": "sample datastore target name",
                        }
                    },
                ]
            elif path == "version":
                return {"version": "6.4.12345-unittest"}

            raise RuntimeError("unhandled path = {path}".format(path=path))

        self.mock_onapprequests.get.side_effect = mock_onapprequests_get
        expected = [
            {
                "first_name": "test",
                "id": 13,
                "last_name": "er",
                "password": ANY,
                "project_name": "project_tester@unit.onapp2vhi.test",
                "quotas": {
                    "cores": 4,
                    "ram-size": 4398046511104,
                    "storage": 40,
                },
                "roles": ["Admin", "user"],
                "user_email": "tester@unit.onapp2vhi.test",
                "user_login": "tester",
                "virtual_machines": [
                    {
                        "booted": True,
                        "built_from_iso": False,
                        "built_from_ova": False,
                        "domain": "testdomain",
                        "hostname": "test-vm1",
                        "id": "abcdef",
                        "ip_addr": "1.2.3.4",
                        "label": "test-vm1-label",
                        "operating_system": "centos7",
                    },
                    {
                        "booted": True,
                        "built_from_iso": False,
                        "built_from_ova": False,
                        "domain": "testdomain",
                        "hostname": "test-vm2",
                        "id": "hijklmn",
                        "ip_addr": "1.2.3.5",
                        "label": "test-vm2-label",
                        "operating_system": "centos7",
                    }
                ],
            },
        ]

        result = prepare_vhi_migration_data(
            self.mock_cfg, vm_idn="abcdef,hijklmn"
        )
        self.assertEqual(result, expected)


class TestVerifyVmUser(OnAppHelpersTestCase):
    def setUp(self):
        super().setUp()
        self.mock_onapprequests = Mock(spec=OnAppRequests)

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    def test_vm_correct_vm_id(self, mock_onapprequests):
        mock_onapprequests.return_value = self.mock_onapprequests
        self.mock_onapprequests.get.side_effect = [
            OnAppRequestsException()
        ]

        self.assertFalse(verify_vm_user(self.mock_cfg, 888, "xxx"))

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    def test_vm_correct_user(self, mock_onapprequests):
        mock_onapprequests.return_value = self.mock_onapprequests
        self.mock_onapprequests.get.side_effect = [
            {"virtual_machine": {"user_id": 888}}
        ]

        self.assertTrue(verify_vm_user(self.mock_cfg, 888, "xxx"))

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    def test_vm_incorrect_user(self, mock_onapprequests):
        mock_onapprequests.return_value = self.mock_onapprequests
        self.mock_onapprequests.get.side_effect = [
            {"virtual_machine": {"user_id": 888}}
        ]

        self.assertFalse(verify_vm_user(self.mock_cfg, 777, "xxx"))

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    def test_multiple_vm(self, mock_onapprequests):
        mock_onapprequests.return_value = self.mock_onapprequests
        self.mock_onapprequests.get.side_effect = [
            {"virtual_machine": {"user_id": 777}},
            {"virtual_machine": {"user_id": 888}},
        ]

        self.assertFalse(verify_vm_user(self.mock_cfg, 777, "xxx,yyy"))


class TestGenerateXmlConfig(unittest.TestCase):

    @patch('onapp2vhi.inc.onapp_helpers.SSH')
    def setUp(self, mock_ssh_ctor):
        super().setUp()

        self.mock_ssh = Mock(spec=SSH, name='mock_ssh')

        mock_cfg = Mock(spec=OnApp2VHIConfig, name='mock_onapp_cfg')
        mock_config_path = '/tmp/dummy.xml'
        mock_vm_idn = 'abcd123'
        mock_hv_ip = '127.0.0.4'

        mock_ssh_ctor.return_value = self.mock_ssh

        self.gxc = GenerateXmlConfig(mock_cfg, mock_config_path, mock_vm_idn, mock_hv_ip)

    @patch('onapp2vhi.inc.onapp_helpers.KVMxml')
    def test_shutdown_vm_ok(self, mock_element_tree_ctor):
        self.mock_ssh.execute.side_effect = [
            (0, '<xml>virsh dump result</xml>'),
            (0, '<xml>virsh shutdown result</xml>')
        ]
        mock_element_tree_ctor.return_value = Mock(name='mock_xml')

        self.gxc.shut_down_vm()
        self.mock_ssh.execute.assert_has_calls([
            call(command='virsh dumpxml abcd123 2>/dev/null > /tmp/abcd123.xml;'
                         ' cat /tmp/abcd123.xml 2>/dev/null'),
            call(command='virsh shutdown abcd123'),
        ])
