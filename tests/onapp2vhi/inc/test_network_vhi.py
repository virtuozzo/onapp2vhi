import unittest
import json

from mock import mock_open, patch
from onapp2vhi.inc.network_vhi import Network
from onapp2vhi.utilities.config import OnApp2VHIConfig

# pylint: disable=no-member

TEST_CFG = """
[onapp]
host = 69.168.239.170
url = http://onapp
api_key = here_is_yours_admin_api_key
email = onapp@gmail.com
cp_ssh_port = 2222
hv_ssh_port = 22

[vhi]
url = https://vhi
panel_url = https://cvhi.onappdev.com:8800
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
vinfra_domain_user = domain_user
vinfra_domain_pass = domain_pass

[key]
ssh_key = path/to/your/ssh_key/id_rsa
"""


class TestNetwork(unittest.TestCase):
    @patch("builtins.open", mock_open(read_data=TEST_CFG))
    def setUp(self):
        self.cfg = OnApp2VHIConfig.load_config("test.ini")

    @patch("onapp2vhi.inc.network_vhi.SSH", autospec=True)
    def test_update_attributes(self, mock_ssh):
        network = Network(self.cfg)
        network.update({"id": 69, "cidr": "8.8.8.8/8"})

        self.assertEqual(network.id, 69)
        self.assertEqual(network.cidr, "8.8.8.8/8")

    @patch("onapp2vhi.inc.network_vhi.SSH", autospec=True)
    def test_create_network(self, mock_ssh):
        test_uuid = "e997d733-5fe2-434f-5141-4933f0bce4e7"

        network_data = {
            "vinfra_project": "test_project",
            "dns_nameservers": ["8.8.8.8", "8.8.4.4"],
            "start_address": "8.8.8.2",
            "end_address": "8.8.8.254",
        }

        network = Network(
            self.cfg, name="test_network", cidr="10.0.0.0/24", **network_data
        )
        network._ssh.execute.return_value = (0, json.dumps({"id": test_uuid}))
        self.assertEqual(network.create(), test_uuid)

        network._ssh.execute.assert_called_with(
            (
                "vinfra --vinfra-username='domain_user'"
                " --vinfra-password='domain_pass'"
                ' --vinfra-domain="Migration"'
                ' --vinfra-project="test_project"'
                " service compute network create test_network"
                " --cidr 10.0.0.0/24 --dns-nameserver ['8.8.8.8', '8.8.4.4']"
                " --allocation-pool 8.8.8.2-8.8.8.254 --no-dhcp --no-gateway"
                ' -f json'
            )
        )

    @patch("onapp2vhi.inc.network_vhi.SSH", autospec=True)
    def test_create_network_fail(self, mock_ssh):
        test_uuid = ""

        network = Network(self.cfg, name="test_network", cidr="10.0.0.0/24")
        network._ssh.execute.return_value = (0, json.dumps({"id": test_uuid}))
        self.assertFalse(network.create())

        network = Network(self.cfg, name="test_network", cidr="10.0.0.0/24")
        network._ssh.execute.return_value = (1, json.dumps({"id": test_uuid}))
        self.assertFalse(network.create())

        network = Network(self.cfg, name="test_network", cidr="10.0.0.0/24")
        network._ssh.execute.return_value = (0, json.dumps({"idx": test_uuid}))
        self.assertFalse(network.create())

    @patch("onapp2vhi.inc.network_vhi.SSH", autospec=True)
    def test_get_detail(self, mock_ssh):
        network = Network(self.cfg)
        network._ssh.execute.return_value = (0, '{"key": "value"}\n{to}\n{me}')
        detail = network.get_detail()
        self.assertEqual(detail, {"key": "value"})

        network._ssh.execute.assert_called_with(
            "service compute network show  -f json"
        )

    @patch("onapp2vhi.inc.network_vhi.SSH", autospec=True)
    def test_get_detail_fail(self, mock_ssh):
        network = Network(self.cfg)
        network._ssh.execute.return_value = (1, "")
        detail = network.get_detail()
        self.assertFalse(detail)

    @patch("onapp2vhi.inc.network_vhi.SSH", autospec=True)
    def test_is_present(self, mock_ssh):
        network_data = {
            "id": 69,
            "cidr": "8.8.8.0/24",
            "vinfra_project": "test_project",
            "start_address": "8.8.8.2",
            "end_address": "8.8.8.254",
        }
        test_data = (
            '[{"subnets": [{"cidr": "8.8.8.0/24", "allocation_pools": '
            '[{"start": "8.8.8.2", "end": "8.8.8.254"}]}, {"cidr":'
            '"4.4.4.0/24"} ], "id": 69}]\nuseless\nuseless'
        )
        network = Network(self.cfg, **network_data)
        network._ssh.execute.return_value = (0, test_data)
        self.assertTrue(network.is_present())

        network._ssh.execute.assert_called_with(
            (
                "vinfra --vinfra-username='domain_user'"
                " --vinfra-password='domain_pass'"
                ' --vinfra-domain="Migration"'
                ' --vinfra-project="test_project"'
                " service compute network list --long -f json"
            )
        )

    @patch("onapp2vhi.inc.network_vhi.SSH", autospec=True)
    def test_is_present_fail_cidr(self, mock_ssh):
        network_data = {
            "id": 69,
            "cidr": "9.9.9.0/24",
            "vinfra_project": "test_project",
            "start_address": "8.8.8.2",
            "end_address": "8.8.8.254",
        }
        test_data = (
            '[{"subnets": [{"cidr": "8.8.8.0/24", "allocation_pools": '
            '[{"start": "8.8.8.2", "end": "8.8.8.254"}]}, {"cidr":'
            '"4.4.4.0/24"} ], "id": 69}]\nuseless\nuseless'
        )

        network = Network(self.cfg, **network_data)
        network._ssh.execute.return_value = (0, test_data)
        self.assertFalse(network.is_present())

    @patch("onapp2vhi.inc.network_vhi.SSH", autospec=True)
    def test_is_present_fail_address_range(self, mock_ssh):
        network_data = {
            "id": 69,
            "cidr": "8.8.8.0/24",
            "vinfra_project": "test_project",
            "start_address": "8.8.8.20",
            "end_address": "8.8.8.40",
        }
        test_data = (
            '[{"subnets": [{"cidr": "8.8.8.0/24", "allocation_pools": '
            '[{"start": "8.8.8.2", "end": "8.8.8.254"}]}, {"cidr":'
            '"4.4.4.0/24"} ], "id": 69}]\nuseless\nuseless'
        )

        network = Network(self.cfg, **network_data)
        network._ssh.execute.return_value = (0, test_data)
        self.assertFalse(network.is_present())

    @patch("onapp2vhi.inc.network_vhi.SSH", autospec=True)
    def test_is_present_fail_no_allocation_pools(self, mock_ssh):
        network_data = {
            "id": 69,
            "cidr": "8.8.8.0/24",
            "vinfra_project": "test_project",
            "start_address": "8.8.8.20",
            "end_address": "8.8.8.40",
        }
        test_data = (
            '[{"subnets": [{"cidr": "8.8.8.0/24", "allocation_pools": '
            '[]}, {"cidr": "4.4.4.0/24"} ], "id": 69}]'
        )

        network = Network(self.cfg, **network_data)
        network._ssh.execute.return_value = (0, test_data)
        self.assertFalse(network.is_present())

    @patch("onapp2vhi.inc.network_vhi.SSH", autospec=True)
    def test_attach_to_virtual_server(self, mock_ssh):
        network_data = {
            "id": 69,
            "cidr": "9.9.9.9/24",
            "vinfra_project": "test_project",
        }
        test_data = '{"id": "69"}\nuseless\nuseless'
        network = Network(self.cfg, **network_data)
        network._ssh.execute.return_value = (0, test_data)
        self.assertEqual(
            network.attach_to_virtual_server(
                "test_virtual_server", ["8.8.8.8", "9.9.9.9"]
            ),
            "69",
        )

        network._ssh.execute.assert_called_with(
            (
                "vinfra --vinfra-username='domain_user'"
                " --vinfra-password='domain_pass'"
                ' --vinfra-domain="Migration" '
                '--vinfra-project="test_project" '
                "service compute server iface attach"
                " --fixed-ip ip-address='8.8.8.8'"
                " --fixed-ip ip-address='9.9.9.9'"
                "  --network 69 --server test_virtual_server -f json"
            )
        )
