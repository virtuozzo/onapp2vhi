import unittest
from mock import patch, mock_open

from onapp2vhi.ops.migrate import migrate_impl
from onapp2vhi.utilities.config import OnApp2VHIConfig

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


class TestVmColdMigration(unittest.TestCase):

    @patch("builtins.open", mock_open(read_data=TEST_CONFIG))
    def setUp(self):
        self.mock_cfg = OnApp2VHIConfig.load_config("test.ini")

    @patch("onapp2vhi.ops.migrate.get_user_ssh_keys")
    @patch("onapp2vhi.ops.migrate.VhiSshKeys")
    @patch("onapp2vhi.ops.migrate.Vhi")
    @patch("onapp2vhi.ops.migrate.prepare_vhi_migration_data")
    @patch("onapp2vhi.ops.migrate.logs")
    def test_migrate_with_no_primary_ip(self, mock_logs, mock_vhi_data, mock_vhi, mock_ssh_key, mock_get_ssh):
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
        result = migrate_impl(self.mock_cfg, user="123", vm="123", project="test")
        self.assertFalse(result)
