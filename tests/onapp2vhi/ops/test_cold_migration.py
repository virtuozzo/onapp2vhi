import unittest
import json
from mock import patch, Mock, mock_open

from onapp2vhi.ops.cold_migrate import vm_cold_migrate
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.inc.vinfra_wrapper import VinfraCommand
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


class TestVmColdMigration(unittest.TestCase):

    @patch("builtins.open", mock_open(read_data=TEST_CONFIG))
    def setUp(self):
        self.mock_cfg = OnApp2VHIConfig.load_config("test.ini")
        self.mock_ssh = Mock(spec=SSH)
        self.mock_vinfra = Mock(spec=VinfraCommand)

    @patch("onapp2vhi.inc.vhi_helpers.Vhi")
    @patch("onapp2vhi.ops.cold_migrate.get_onapp_vm_disks")
    @patch("onapp2vhi.ops.cold_migrate.get_onapp_vm_nics")
    @patch("onapp2vhi.ops.cold_migrate.get_onapp_vm_flavor")
    @patch("onapp2vhi.ops.cold_migrate.logs")
    @patch("onapp2vhi.ops.cold_migrate.SSH")
    @patch("onapp2vhi.ops.cold_migrate.VinfraCommand")
    def test_vm_cold_migration_network_not_ready(self, mock_vinfra, mock_ssh, mock_logs, mock_vm_flavor, mock_vm_nics, mock_vm_disks, mock_vhi):

        mock_vm_flavor.return_value = "test_123"
        mock_vm_nics.return_value = [{"ips": ["1.2.3.4"], "mac": "test"}]
        mock_vm_disks.return_value = "disk_test"
        mock_vhi.flavor_name.return_value = "test_213"

        self.mock_ssh.execute.return_value = (0, "")
        mock_ssh.return_value = self.mock_ssh

        self.mock_vinfra.execute.return_value = json.dumps([{"id": "test_id_123", "networks": [],
                                                             "name": "vm_faidhi_testidn", "status": "BUILD"}])
        mock_vinfra.return_value = self.mock_vinfra

        mock_vdom = "behave"
        mock_vproj = "Default_Project"
        mock_idn = "testidn"
        mock_properties = {
            'hv_ip': '10.116.0.32',
            'vm_os': 'linux',
            'vm_ip_addr': '10.119.0.4',
            'network_info': {860: ['10.119.0.4']},
            'hot_migrate': True,
            'hostname': 'faidhi2',
            'domain': 'localdomain',
            'storage_policy': 'default'
        }

        result = vm_cold_migrate(self.mock_cfg, mock_vdom, mock_vproj, mock_idn, mock_properties, mock_vhi)
        self.assertFalse(result)
