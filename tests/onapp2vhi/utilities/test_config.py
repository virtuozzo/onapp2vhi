# Desc: Test the config module
import unittest
from mock import mock_open, patch

from onapp2vhi.utilities.config import AttributeDict, OnApp2VHIConfig

# pylint: disable=no-member

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

TEST_CFG_2 = """
[onapp]
host = different_host
"""


class TestSingleton(unittest.TestCase):
    """
    Test the singleton class
    """

    def setUp(self):
        pass

    def test_no_config_load(self):
        """
        Instantiating the class without loading the config should raise an
        error
        """
        with self.assertRaises(RuntimeError):
            OnApp2VHIConfig()

    @patch("builtins.open", mock_open(read_data=TEST_CFG))
    def test_with_config_load(self):
        """
        Test that the config is loaded and the same instance is returned
        """

        first_instance = OnApp2VHIConfig.load_config("test.ini")
        second_instance = OnApp2VHIConfig()

        self.assertIsNotNone(first_instance)
        self.assertIs(first_instance, second_instance)

    def test_config_load_no_file(self):
        """
        Test that the config is not loaded if the file does not exist
        """
        with self.assertRaises(FileNotFoundError):
            OnApp2VHIConfig.load_config("some_random_file.ini")

    def test_update_config(self):
        """
        Test that the config is updated and written to file
        """
        with patch("builtins.open", mock_open(read_data=TEST_CFG)):
            first_instance = OnApp2VHIConfig.load_config("test.ini")
            second_instance = OnApp2VHIConfig()

        write_mock = mock_open()
        with patch("builtins.open", write_mock):
            first_instance.update("onapp", "host", "new_host")

        self.assertEqual(second_instance.onapp_conf["host"], "new_host")
        self.assertEqual(second_instance.onapp_conf.host, "new_host")

        write_mock.assert_called_once_with("test.ini", "w+")
        handler = write_mock()
        handler.write.assert_any_call("host = new_host\n")

    def test_load_different_config(self):
        """
        Load a different config file will update the config
        """
        with patch("builtins.open", mock_open(read_data=TEST_CFG)):
            first_instance = OnApp2VHIConfig.load_config("test.ini")
            self.assertEqual(
                first_instance.onapp_conf["host"], "127.0.0.1"
            )

        with patch("builtins.open", mock_open(read_data=TEST_CFG_2)):
            OnApp2VHIConfig.load_config("test.ini")
            self.assertEqual(
                first_instance.onapp_conf["host"], "different_host"
            )

    def tearDown(self):
        try:
            del OnApp2VHIConfig._instance
        except AttributeError:
            pass


class TestData(unittest.TestCase):
    def setUp(self):
        with patch("builtins.open", mock_open(read_data=TEST_CFG)):
            self.cfg = OnApp2VHIConfig.load_config("test.ini")

    def test_get_config(self):
        config = self.cfg.get_config(cp_type="onapp")
        self.assertEqual(config["url"], "http://onapp")
        self.assertIsInstance(config, AttributeDict)

    def test_onapp_conf(self):
        self.assertEqual(self.cfg.onapp_conf.url, "http://onapp")
        self.assertEqual(self.cfg.onapp_conf["url"], "http://onapp")

    def test_vhi_conf(self):
        self.assertEqual(self.cfg.vhi_conf.url, "https://vhi")
        self.assertEqual(self.cfg.vhi_conf["url"], "https://vhi")

    def test_auth(self):
        admin_test_string = (
            "vinfra --vinfra-username='admin'"
            " --vinfra-password='ui_admin_password'"
        )
        self.assertEqual(self.cfg.ADMIN_AUTH, admin_test_string)

        vinfra_test_string = (
            "vinfra --vinfra-username='user_login'"
            " --vinfra-password='user_pwd'"
        )
        self.cfg.VINFRA_AUTH
        self.assertEqual(self.cfg.VINFRA_AUTH, vinfra_test_string)

        domain_test_string = (
            "vinfra --vinfra-username='domain_user'"
            " --vinfra-password='domain_pass'"
        )
        self.cfg.DOMAIN_AUTH
        self.assertEqual(self.cfg.DOMAIN_AUTH, domain_test_string)

    def test_ssh_key(self):
        self.assertEqual(self.cfg.ssh_key, "path/to/your/ssh_key/id_rsa")

    def tearDown(self):
        try:
            del OnApp2VHIConfig._instance
        except AttributeError:
            pass


if __name__ == "__main__":
    unittest.main()
