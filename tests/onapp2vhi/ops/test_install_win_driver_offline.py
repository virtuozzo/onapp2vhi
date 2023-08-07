import unittest
from mock import patch, Mock, mock_open, call

from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.ops.install_win_drivers_offline import vm_install_win_drivers_offline
from onapp2vhi.inc.ssh_connector import SSH
from onapp2vhi.inc.windows_network_reconfig import WindowsNetworkReconfig

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


class TestInstallWinDriverOffline(unittest.TestCase):

    @patch("builtins.open", mock_open(read_data=TEST_CONFIG))
    def setUp(self):
        self.mock_cfg = OnApp2VHIConfig.load_config("test.ini")
        self.mock_ssh = Mock(spec=SSH)
        self.mock_network_reconfig = Mock(spec=WindowsNetworkReconfig)

    @patch("onapp2vhi.ops.install_win_drivers_offline.WindowsNetworkReconfig")
    @patch("onapp2vhi.ops.install_win_drivers_offline.deactivate_disk")
    @patch("onapp2vhi.ops.install_win_drivers_offline.get_disk_type")
    @patch("onapp2vhi.ops.install_win_drivers_offline.activate_disk")
    @patch("onapp2vhi.inc.onapp_helpers.VmHandler")
    @patch("onapp2vhi.ops.install_win_drivers_offline.ssh_run")
    @patch("onapp2vhi.ops.install_win_drivers_offline.exit_status_code_handler")
    @patch("onapp2vhi.ops.install_win_drivers_offline.SSH")
    @patch("onapp2vhi.ops.install_win_drivers_offline.get_onapp_vm_disks")
    @patch("onapp2vhi.ops.install_win_drivers_offline.logs")
    @patch("onapp2vhi.ops.install_win_drivers_offline.download_file")
    def test_vm_install_win_drivers_offline(self, mock_download, mock_logs, mock_vm_disks,
                                            mock_ssh, mock_exit_status,
                                            mock_ssh_run, mock_vm_handler,
                                            mock_activate_disk, mock_get_disk_type,
                                            mock_deactivate_disk, mock_network_reconfig):

        self.mock_ssh.execute.return_value = (1, "")
        mock_ssh.return_value = self.mock_ssh
        self.mock_network_reconfig.create_file.return_value = True
        self.mock_network_reconfig.file = "test_file"
        mock_network_reconfig.return_value = self.mock_network_reconfig
        mock_ssh_run.return_value = (1, "")
        mock_exit_status.return_value = True

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

        result = vm_install_win_drivers_offline(self.mock_cfg, mock_vm_handler, "aabbccdd", mock_properties)

        self.assertTrue(result)
        mock_ssh_run.assert_has_calls(
            [
                call("scp -o 'ForwardAgent yes' -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' -r /home/faidhi/VHI/onapp2vhi/onapp2vhi/ops/scripts/vz-guest-tools-win.tar root@10.116.0.32:/mnt/aabbccdd/vz-guest-tools-win.tar"),
                call("scp -o 'ForwardAgent yes' -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' -r /home/faidhi/VHI/onapp2vhi/onapp2vhi/ops/scripts/CloudbaseInitSetup_Stable_x64.msi  root@10.116.0.32:/mnt/aabbccdd/CloudbaseInitSetup_Stable_x64.msi"),
                call("scp -o 'ForwardAgent yes' -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' -r /home/faidhi/VHI/onapp2vhi/onapp2vhi/ops/scripts/onapp.bat_ci_vz root@10.116.0.32:/mnt/aabbccdd/onapp.bat"),
                call("scp -o 'ForwardAgent yes' -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' -r test_file root@10.116.0.32:/mnt/aabbccdd/vhi_rebuild_network.bat")
            ]
        )
