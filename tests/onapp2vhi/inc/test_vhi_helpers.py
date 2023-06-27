import unittest

from mock import mock_open, patch, Mock, call
from onapp2vhi.inc.vhi_helpers import Vhi
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.inc.ssh_connector import SSH

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


class TestVhiHelpers(unittest.TestCase):
    @patch("builtins.open", mock_open(read_data=TEST_CFG))
    @patch("onapp2vhi.inc.vhi_helpers.SSH", autospec=True)
    def setUp(self, mock_ssh):
        self.cfg = OnApp2VHIConfig.load_config("test.ini")
        self.vhi = Vhi(self.cfg)
        self.mock_flavor_ssh = Mock(spec=SSH)
        self.mock_placement_ssh = Mock(spec=SSH)

    def test_vhi_flavor_payload(self):
        flavor_payload = {
            "name": "test_flavor",
            "vcpus": 1,
            "ram": 1024,
            "disk": 20,
        }

        result = '{"name": "test_flavor", "vcpus": 1, "ram": 1024, "disk": 0}'
        self.assertEquals(self.vhi._vhi_flavor_payload(flavor_payload), result)

    @patch("builtins.open", mock_open())
    def test_set_project_value(self):
        self.vhi.set_project_value("test_project")
        self.assertEquals(self.cfg.vhi_conf.vinfra_project, "test_project")

    def test_clean_up_cache(self):
        self.vhi._vhi_ssh.execute.return_value = (0, "test_project")
        self.assertTrue(self.vhi.clean_up_cache())

        self.vhi._vhi_ssh.execute.return_value = (1, "test_project")
        self.assertFalse(self.vhi.clean_up_cache())

    @patch("builtins.open", mock_open())
    def test_check_default_project(self):
        # Failed to get project list
        self.vhi._vhi_ssh.execute.return_value = (1, "test_project")
        self.assertFalse(self.vhi.check_default_project())

        self.vhi._vhi_ssh.execute.assert_called_with(
            (
                "vinfra --vinfra-username='admin'"
                " --vinfra-password='ui_admin_password'"
                " domain project list --domain='Migration' -f json"
            )
        )

        # Default project is set
        self.vhi._vhi_ssh.execute.return_value = (
            0,
            '[{"name": "Default_Project"}]',
        )
        self.assertTrue(self.vhi.check_default_project())

        # Default project is not set
        side_effect = [
            (0, '[{"name": "XXX_Project"}]'),
            (0, '{"name": "XXX_Project", "id": "69"}'),
        ]

        self.vhi._vhi_ssh.execute.side_effect = side_effect
        self.assertTrue(self.vhi.check_default_project())
        self.assertEqual(self.cfg.vhi_conf.vinfra_project, "XXX_Project")

        create_cmd = (
            "vinfra --vinfra-username='admin'"
            " --vinfra-password='ui_admin_password' domain project"
            " create 'Default_Project' --domain='Migration' --enable"
            " --description='Default project for migrations.' -f json"
        )

        self.vhi._vhi_ssh.execute.assert_called_with(create_cmd)

    @patch("onapp2vhi.inc.vhi_helpers.generate_random_password", autospec=True)
    def test_update_user_password(self, mock_password):
        mock_password.return_value = 4
        self.assertEqual(self.vhi.update_user_password("test_user"), 4)

        self.vhi._vhi_ssh.execute.assert_called_with(
            (
                "echo -e '4' | vinfra --vinfra-username='admin'"
                " --vinfra-password='ui_admin_password' domain user set"
                " 'test_user' --password --domain Migration"
            )
        )

    @patch("onapp2vhi.inc.vhi_helpers.VinfraFlavor", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.VinfraPlacement", autospec=True)
    def test_flavor_handler(self, mock_placement, mock_flavor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        mock_flavor_instance = mock_flavor.return_value
        mock_placement_instance = mock_placement.return_value

        # No flavor returned
        mock_flavor_instance.flavor_list.return_value = [
            2,
            {"name": "flavorless"},
        ]
        self.assertFalse(self.vhi.flavor_handler(flavor))

        # Flavor returned and exist in vhi
        mock_flavor_instance.flavor_list.return_value = [
            0,
            '[{"name": "flavor_2_512"}]',
        ]
        self.assertTrue(self.vhi.flavor_handler(flavor))
        self.assertEqual(self.vhi.flavor_name, "flavor_2_512")

        # Flavor returned and exist in vhi with placement
        mock_flavor_instance.flavor_list.return_value = [
            0,
            '[{"name": "flavor_2_512"}]',
        ]
        mock_placement_instance.assign_placement_to_flavor.return_value = [
            0,
            "test_placement",
        ]
        self.assertTrue(self.vhi.flavor_handler(flavor, "test_placement"))
        self.assertEqual(self.vhi.flavor_name, "flavor_2_512")

        # Flavor returned and not in vhi with placement
        mock_flavor_instance.flavor_list.return_value = [
            0,
            '[{"name": "flavorless"}]',
        ]

        mock_flavor_instance.create.return_value = [
            0,
            '{"name": "flavorless"}',
        ]

        mock_placement_instance.assign_placement_to_flavor.return_value = [
            0,
            "test_placement",
        ]
        self.assertTrue(self.vhi.flavor_handler(flavor, "test_placement"))
        self.assertEqual(self.vhi.flavor_name, "flavorless")

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_vinfra_check_no_flavor(self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        # No flavor returned
        mock_ssh_ctor.side_effect = [
            self.mock_flavor_ssh,
            self.mock_placement_ssh,
        ]
        self.mock_flavor_ssh.execute.side_effect = [
            (2, {"name": "flavorless"}),
        ]
        self.assertFalse(self.vhi.flavor_handler(flavor))
        self.mock_flavor_ssh.execute.assert_called_once_with(
            "vinfra --vinfra-username='user_login' --vinfra-password='user_pwd' service compute "
            "flavor list -f json")
        self.mock_placement_ssh.execute.assert_not_called()

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_vinfra_check_flavor_returned_and_exists_in_vhi(self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        # Flavor returned and exist in vhi
        mock_ssh_ctor.side_effect = [
            self.mock_flavor_ssh,
            self.mock_placement_ssh,
        ]
        self.mock_flavor_ssh.execute.side_effect = [
            (0, '[{"name": "flavor_2_512"}]'),
        ]
        self.assertTrue(self.vhi.flavor_handler(flavor))
        self.assertEqual(self.vhi.flavor_name, "flavor_2_512")
        self.mock_flavor_ssh.execute.assert_called_once_with(
            "vinfra --vinfra-username='user_login' --vinfra-password='user_pwd' service compute "
            "flavor list -f json")
        self.mock_placement_ssh.execute.assert_not_called()

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_vinfra_check_flavor_returned_and_exist_in_vhi_with_placement(
            self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        # Flavor returned and exist in vhi with placement
        self.mock_flavor_ssh.execute.side_effect = [
            (0, '[{"name": "flavor_2_512"}]'),
        ]
        self.mock_placement_ssh.execute.side_effect = [
            (0, "test_placement"),
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_flavor_ssh,
            self.mock_placement_ssh,
        ]

        self.assertTrue(self.vhi.flavor_handler(flavor, "test_placement"))
        self.assertEqual(self.vhi.flavor_name, "flavor_2_512")
        self.mock_flavor_ssh.execute.assert_called_once_with(
            "vinfra --vinfra-username='user_login' --vinfra-password='user_pwd' service compute "
            "flavor list -f json")
        self.mock_placement_ssh.execute.assert_called_once_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service compute "
            "placement assign --flavors flavor_2_512 test_placement")

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_vinfra_check_flavor_returned_and_not_in_vhi_with_placemant(
            self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        # Flavor returned and not in vhi with placement
        self.mock_flavor_ssh.execute.side_effect = [
            (0, '[{"name": "flavorless"}]'),
            (0, '{"name": "flavorless"}'),
        ]
        self.mock_placement_ssh.execute.side_effect = [
            (0, "test_placement"),
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_flavor_ssh,
            self.mock_placement_ssh,
        ]

        self.assertTrue(self.vhi.flavor_handler(flavor, "test_placement"))
        self.assertEqual(self.vhi.flavor_name, "flavorless")
        self.mock_flavor_ssh.execute.assert_has_calls([
            call("vinfra --vinfra-username='user_login' --vinfra-password='user_pwd' service compute "
                 "flavor list -f json"),
            call("vinfra --vinfra-username='user_login' --vinfra-password='user_pwd' service compute "
                 "flavor create flavor_2_512 --vcpus=2 --ram=512 -f json")
        ])
        self.mock_placement_ssh.execute.assert_called_once_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' service compute "
            "placement assign --flavors flavorless test_placement")

    @patch("onapp2vhi.inc.vhi_helpers.VinfraUser", autospec=True)
    def test_verify_user_exists(self, mock_user):
        mock_user_instance = mock_user.return_value
        mock_user_instance.user_list.return_value = [
            0,
            '[{"name": "test_user", "email": "a@a.com"}]',
        ]
        self.assertTrue(self.vhi._verify_user_exists("a@a.com", "test_domain"))
        self.assertFalse(
            self.vhi._verify_user_exists("b@b.com", "test_domain")
        )

    @patch("builtins.open", mock_open())
    @patch("onapp2vhi.inc.vhi_helpers.VinfraUser", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.generate_random_password", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.VinfraImage", autospec=True)
    def test_create_domain_service_user(
        self, mock_image, mock_password, mock_user
    ):
        mock_password.return_value = "test_password"

        mock_user_instance = mock_user.return_value
        mock_user_instance.user_list.return_value = [
            0,
            '[{"name": "test_user", "email": "Migration@user.com"}]',
        ]

        mock_image_instance = mock_image.return_value

        # user exist
        mock_image_instance.images.return_value = [0, "some_output"]
        self.assertTrue(self.vhi._create_domain_service_user())

        # user exist but wrong password
        mock_image_instance.images.return_value = [1, "some_output"]
        self.assertTrue(self.vhi._create_domain_service_user())

        # user does not exist failed created
        mock_user_instance.user_list.return_value = [
            1,
            '[{"name": "test_user", "email": "no_exist@user.com"}]',
        ]
        mock_user_instance.create.return_value = [1, "some_output"]
        self.assertFalse(self.vhi._create_domain_service_user())

        # user does not exist create success
        mock_user_instance.user_list.return_value = [
            1,
            '[{"name": "test_user", "email": "no_exist@user.com"}]',
        ]
        mock_user_instance.create.return_value = [0, "some_output"]
        self.assertTrue(self.vhi._create_domain_service_user())
        mock_user_instance.set.assert_called_with(
            user_name="dom_migration_user_migration",
            domain="Migration",
            assign_domain=["Migration", "compute"],
        )
        self.assertEqual(
            self.cfg.vhi_conf["vinfra_domain_user"],
            "dom_migration_user_migration",
        )
        self.assertEqual(
            self.cfg.vhi_conf["vinfra_domain_pass"], "test_password"
        )

    @patch("builtins.open", mock_open())
    @patch("onapp2vhi.inc.vhi_helpers.VinfraUser", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.generate_random_password", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.VinfraImage", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.VinfraNode", autospec=True)
    def test_create_service_user(
        self, mock_node, mock_image, mock_password, mock_user
    ):
        mock_user_instance = mock_user.return_value
        mock_image_instance = mock_image.return_value
        mock_node_instance = mock_node.return_value

        mock_node_instance.list_node.side_effect = [
            (1, "[]"),
            (0, "[]"),
            (0, "[]"),
        ]

        # service user exist with wrong credentials
        mock_password.return_value = "test_password"
        mock_user_instance.user_list.return_value = [
            0,
            (
                '[{"email": "Migration@user.com"}, '
                '{"email": "migration_helper@user.com"}]'
            ),
        ]
        mock_image_instance.images.return_value = [0, "some_output"]

        self.vhi.create_service_user()
        self.assertEqual(self.cfg.vhi_conf["vinfra_user"], "migration_user")

        # service user not exists failed creation

        mock_user_instance.user_list.return_value = [
            0,
            ('[{"email": "Migration@user.com"}] '),
        ]

        mock_user_instance.create.return_value = [
            0,
            '{"email": "migration_helper@user.com",'
            '"system_permissions": "no_permission", "name": "migration_user",'
            '"enable": true, "assign-domain": ["Default", "compute"],'
            '"domain": "Default"}',
        ]

        self.assertFalse(self.vhi.create_service_user())

        # service user not exists success creation

        mock_user_instance.user_list.return_value = [
            0,
            ('[{"email": "Migration@user.com"}] '),
        ]

        mock_user_instance.create.return_value = [
            0,
            '{"email": "migration_helper@user.com",'
            '"system_permissions": "compute", "name": "migration_user",'
            '"enable": true, "assign-domain": ["Default", "compute"],'
            '"domain": "Default"}',
        ]
        mock_password.return_value = "new_password"

        self.assertTrue(self.vhi.create_service_user())
        self.assertEqual(self.cfg.vhi_conf["vinfra_pass"], "new_password")

    @patch("builtins.open", mock_open())
    @patch("onapp2vhi.inc.vhi_helpers.VinfraProject", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.VinfraStoragePolicies", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.VinfraQuotas", autospec=True)
    def test_create_project(self, mock_quota, mock_policy, mock_project):
        # project exist
        mock_project_instance = mock_project.return_value
        mock_project_instance.projects.return_value = [
            0,
            '[{"name": "project_roman.holovko@virtuozzo.com"}]',
        ]

        user_data = {
            "user_email": "roman.holovko@virtuozzo.com",
            "id": 4,
            "first_name": "Roman",
            "last_name": "Holovko",
            "password": "pwd",
            "user_login": "roman_holovko@virtuozzo_com",
            "project_name": "project_roman.holovko@virtuozzo.com",
            "quotas": {"cores": -1, "RAM": -1, "storage": -1},
        }
        self.assertTrue(self.vhi.create_project(user_data))

        # project does not exist and quota unlimited

        mock_project_instance = mock_project.return_value
        mock_project_instance.projects.return_value = [
            0,
            '[{"name": "project_test"}]',
        ]
        mock_project_instance.create.return_value = [
            0,
            '{"name": "project_roman.holovko@virtuozzo.com", "id": "4"}',
        ]

        user_data = {
            "user_email": "roman.holovko@virtuozzo.com",
            "id": 4,
            "first_name": "Roman",
            "last_name": "Holovko",
            "password": "pwd",
            "user_login": "roman_holovko@virtuozzo_com",
            "project_name": "project_roman.holovko@virtuozzo.com",
            "quotas": {"cores": -1, "RAM": -1, "storage": -1},
        }

        mock_storage_instance = mock_policy.return_value
        mock_storage_instance.storage_policy_list.return_value = [
            0,
            '[{"name": "Default"}]',
        ]

        self.assertTrue(self.vhi.create_project(user_data))

        # Project does not exist and storage quota limited

        mock_project_instance = mock_project.return_value
        mock_project_instance.projects.return_value = [
            0,
            '[{"name": "project_test"}]',
        ]
        mock_project_instance.create.return_value = [
            0,
            '{"name": "project_roman.holovko@virtuozzo.com", "id": "4"}',
        ]

        user_data = {
            "user_email": "roman.holovko@virtuozzo.com",
            "id": 4,
            "first_name": "Roman",
            "last_name": "Holovko",
            "password": "pwd",
            "user_login": "roman_holovko@virtuozzo_com",
            "project_name": "project_roman.holovko@virtuozzo.com",
            "quotas": {"cores": -1, "RAM": -1, "storage": 2},
        }

        mock_storage_instance = mock_policy.return_value
        mock_storage_instance.storage_policy_list.return_value = [
            0,
            '[{"name": "Default"}]',
        ]

        mock_quota_instance = mock_quota.return_value
        mock_quota_instance.update_quotas.return_value = [0, "some_output"]

        self.assertTrue(self.vhi.create_project(user_data))

    @patch("onapp2vhi.inc.vhi_helpers.VinfraUser", autospec=True)
    def test_create_user(self, mock_user):
        user_data = {
            "user_email": "roman.holovko@virtuozzo.com",
            "id": 4,
            "first_name": "Roman",
            "last_name": "Holovko",
            "password": "pwd",
            "user_login": "roman_holovko@virtuozzo_com",
            "project_name": "project_roman.holovko@virtuozzo.com",
            "quotas": {"cores": -1, "RAM": -1, "storage": -1},
            "roles": [{"role": {"identifier": "staff"}}],
        }

        user_data_admin = {
            "user_email": "roman.holovko@virtuozzo.com",
            "id": 4,
            "first_name": "Roman",
            "last_name": "Holovko",
            "password": "pwd",
            "user_login": "roman_holovko@virtuozzo_com",
            "project_name": "project_roman.holovko@virtuozzo.com",
            "quotas": {"cores": -1, "RAM": -1, "storage": -1},
            "roles": [{"role": {"identifier": "admin"}}],
        }

        # user exists
        mock_user_instance = mock_user.return_value
        mock_user_instance.user_list.return_value = [
            0,
            ('[{"email": "roman.holovko@virtuozzo.com"}] '),
        ]

        result, passwd = self.vhi.create_user(user_data)
        self.assertTrue(result)
        self.assertEqual(len(passwd), 24)

        # user does not exist with admin role
        mock_user_instance = mock_user.return_value
        mock_user_instance.user_list.return_value = [
            0,
            ('[{"email": "fake@email.com"}] '),
        ]
        mock_user_instance.create.return_value = [0, '{"id": 888}']

        result, passwd = self.vhi.create_user(user_data_admin)
        self.assertTrue(result)
        self.assertEqual(len(passwd), 24)
        self.assertEqual(self.vhi.user_id, 888)

        # user does not exist with non-admin role
        mock_user_instance = mock_user.return_value
        mock_user_instance.user_list.return_value = [
            0,
            ('[{"email": "fake@email.com"}] '),
        ]
        mock_user_instance.create.return_value = [0, '{"id": 777}']

        result, passwd = self.vhi.create_user(user_data)
        self.assertTrue(result)
        self.assertEqual(len(passwd), 24)
        self.assertEqual(self.vhi.user_id, 777)
