import unittest
from mock import mock_open, patch
from onapp2vhi.utilities.config_cli import ConfigCli

TEST_CFG = """
[onapp]
host = 127.0.0.1
url = http://onapp
api_key = here_is_yours_admin_api_key
email = onapp@gmail.com
cp_ssh_port = 2222
hv_ssh_port = 22

[vhi]
url = https://vhi
panel_url = https://cvhi.onapp.virtuozzo.com:8800
api_path = /api/v2
login = admin
admin_ui_pwd = ui_admin_password
hv_ip = 10.0.0.2
cp_ip = 127.0.0.1
network = public2
cloud_ssh_port = 2222
hv_ssh_port = 22
linux_image = debian-10-openstack-amd64.qcow2
windows_image = windows2012
domain_id = 00000000000000000000000000000000
vinfra_domain = Migration
vinfra_project = migproj
vinfra_user = user_login
vinfra_pass = user_pwd
vinfra_domain_user = domain_user
vinfra_domain_pass = domain_pass

[key]
ssh_key = path/to/your/ssh_key/id_rsa
"""


class TestConfigCli(unittest.TestCase):

    def setUp(self):
        pass

    @patch("onapp2vhi.utilities.config_cli.questionary")
    def test_cli_update(self, mock_questionary):
        with patch("builtins.open", mock_open(read_data=TEST_CFG)):
            mock_questionary.select.return_value.unsafe_ask.side_effect = ["onapp",
                                                                           "email: onapp@gmail.com",
                                                                           KeyboardInterrupt(),
                                                                           KeyboardInterrupt(),
                                                                           ]
            mock_questionary.text.return_value.ask.return_value = "test@test.com"

            config_cli = ConfigCli("test.ini")
            config_cli.run()
            self.assertEqual(config_cli._config.onapp_conf["email"], "test@test.com")
