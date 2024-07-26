import unittest
from mock import patch, mock_open, Mock

from onapp2vhi.ops.migrate import (
    migrate_impl,
    select_vm_network_configuration,
    MigrationError
)
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.inc.rest_client import OnAppRequests
from onapp2vhi.inc.vinfra_wrapper import (
    VinfraError,
    VinfraServiceComputeNetwork
)

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
vhi_storage_policy = ''

 Network ID for migration VM's, you can get it on VHI cloud
migration_network_id = 5afcb27b-1c92-4561-a81c-fcf4f89bd543

vhi_secondary_security_group = 1234-1234fasd-safce0-adsfew

[key]
ssh_key = path/to/your/ssh_key/id_rsa
"""


class TestMigrationImpl(unittest.TestCase):

    @staticmethod
    def mock_onapprequests_get(params):
        if params == 'virtual_machines/1234':
            return {"virtual_machine": {"user_id": 123}}
        if params == 'virtual_machines/123':
            return {"virtual_machine": {"user_id": 123}}
        raise NotImplementedError(f'unhandled onapprequest.get(\'{params})\')')

    @patch("builtins.open", mock_open(read_data=TEST_CONFIG))
    def setUp(self):
        self.mock_cfg = OnApp2VHIConfig.load_config("test.ini")
        self.mock_onapprequests = Mock(spec=OnAppRequests)

    @patch("onapp2vhi.inc.onapp_helpers.OnAppRequests")
    @patch("onapp2vhi.ops.migrate.get_user_ssh_keys")
    @patch("onapp2vhi.ops.migrate.VhiSshKeys")
    @patch("onapp2vhi.ops.migrate.Vhi")
    @patch("onapp2vhi.ops.migrate.prepare_vhi_migration_data")
    @patch("onapp2vhi.ops.migrate.logs")
    def test_migrate_with_no_primary_ip(self, mock_logs, mock_vhi_data,
                                        mock_vhi, mock_ssh_key, mock_get_ssh,
                                        mock_onapprequests):

        mock_onapprequests.return_value = self.mock_onapprequests
        self.mock_onapprequests.get.side_effect = TestMigrationImpl.mock_onapprequests_get
        mock_vhi.return_value.create_user.return_value = ("test", "tests")
        mock_data = [
            {
                "first_name": "test",
                "last_name": "testing",
                "virtual_machines": [
                    {
                        "id": "123",
                        "ip_addr": None,
                        "label": "label_test"
                    }
                ]
            },
        ]
        mock_vhi_data.return_value = mock_data
        mock_vinfraservicecomputenetwork = Mock(spec=VinfraServiceComputeNetwork)
        mock_vinfraservicecomputenetwork.show.return_value = "[{}]"

        with patch("onapp2vhi.ops.migrate.VinfraServiceComputeNetwork",
                   return_value=mock_vinfraservicecomputenetwork):
            result = migrate_impl(self.mock_cfg, user="123", vm="123", project="test")
            self.assertFalse(result)

    def test_migrate_with_invalid_network_param(self):
        self.mock_onapprequests.get.side_effect = TestMigrationImpl.mock_onapprequests_get

        mock_vinfraservicecomputenetwork= Mock(spec=VinfraServiceComputeNetwork)
        mock_vinfraservicecomputenetwork.show.side_effect = VinfraError('some_command', 1, 'some error')

        with patch("onapp2vhi.inc.onapp_helpers.OnAppRequests",
                   return_value=self.mock_onapprequests):

            with patch("onapp2vhi.ops.migrate.VinfraServiceComputeNetwork",
                       return_value = mock_vinfraservicecomputenetwork):

                result = migrate_impl(self.mock_cfg,
                                      user='123',
                                      vm='1234',
                                      project='test',
                                      network='invalid_network')
                self.assertFalse(result)

    def test_migrate_with_network_param_with_unparsable_reply(self):
        self.mock_onapprequests.get.side_effect = TestMigrationImpl.mock_onapprequests_get

        mock_vinfraservicecomputenetwork= Mock(spec=VinfraServiceComputeNetwork)
        mock_vinfraservicecomputenetwork.show.return_value = ""

        with patch("onapp2vhi.inc.onapp_helpers.OnAppRequests",
                   return_value=self.mock_onapprequests):

            with patch("onapp2vhi.ops.migrate.VinfraServiceComputeNetwork",
                       return_value = mock_vinfraservicecomputenetwork):

                result = migrate_impl(self.mock_cfg,
                                      user='123',
                                      vm='1234',
                                      project='test',
                                      network='invalid_network')
                self.assertFalse(result)


class SelectVmNetworkConfigurationTestCase(unittest.TestCase):

    def test_supply_network_parameter(self):
        mock_config = Mock(spec=OnApp2VHIConfig)
        result = select_vm_network_configuration(mock_config, 'a_vm', 'some_vhi_project',
                                                 'fake_network')
        self.assertEqual(result, '--network id=fake_network')

    def test_empty_network_parameter(self):
        with patch('onapp2vhi.ops.migrate.get_network_configuration',
                   return_value='real_network_config'):
            mock_config = Mock(spec=OnApp2VHIConfig)
            result = select_vm_network_configuration(mock_config, 'a_vm',
                                                     'some_vhi_project', '')
            self.assertEqual(result, 'real_network_config')

    def test_no_network_configration(self):
        with self.assertRaises(MigrationError):
            with patch('onapp2vhi.ops.migrate.get_network_configuration',
                       return_value=''):
                mock_config = Mock(spec=OnApp2VHIConfig)
                result = select_vm_network_configuration(mock_config, 'a_vm',
                                                         'some_vhi_project', '')
                self.assertEqual(result, 'real_network_config')
