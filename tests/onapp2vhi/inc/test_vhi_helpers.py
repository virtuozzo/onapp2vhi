import unittest
import json

from mock import mock_open, patch, Mock, call
from onapp2vhi.inc.vhi_helpers import Vhi
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.inc.ssh_connector import SSH
from onapp2vhi.inc.vinfra_wrapper import VinfraError

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
            '[{"name": "Default_Project", "domain_id": "test123"}]',
        )
        self.assertTrue(self.vhi.check_default_project())

        # Default project is not set
        side_effect = [
            (0, '[{"name": "XXX_Project", "domain_id": "test123"}]'),
            (0, '{"name": "XXX_Project", "id": "69", "domain_id": "test123"}'),
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

    @patch("onapp2vhi.inc.vhi_helpers.VinfraProject", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.VinfraQuotas", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.VinfraFlavor", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.VinfraPlacement", autospec=True)
    def test_flavor_handler(self, mock_placement, mock_flavor, mock_quotas, mock_project):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        mock_flavor_instance = mock_flavor.return_value
        mock_placement_instance = mock_placement.return_value
        mock_quotas_instance = mock_quotas.return_value
        mock_project_instance = mock_project.return_value

        mock_placement_instance.list.return_value = json.dumps([{
            'name': 'test_placement',
            'id': 'abdc-1234-fegh-6789',
        }])
        mock_project_instance.show.return_value = json.dumps({'id': '12324-basdf'})
        mock_quotas_instance.show_quotas.return_value = json.dumps({
            'placement': {
                'abdc-1234-fegh-6789': {
                    'limit': -1,
                }
            }
        })

        # No flavor returned
        mock_flavor_instance.flavor_list.side_effect =\
            VinfraError(command='list flavor', exit_code=2, output='No flavor')
        self.assertFalse(self.vhi.flavor_handler(flavor))

        # Flavor returned and exist in vhi
        mock_flavor_instance.flavor_list.side_effect = None
        mock_flavor_instance.flavor_list.return_value = '[{"name": "flavor_2_512"}]'
        self.assertTrue(self.vhi.flavor_handler(flavor))
        self.assertEqual(self.vhi.flavor_name, "flavor_2_512")

        # Flavor returned and exist in vhi with placement
        mock_flavor_instance.flavor_list.return_value = '[{"name": "flavor_2_512"}]'
        mock_placement_instance.assign_placement_to_flavor.return_value = "test_placement"
        self.assertTrue(self.vhi.flavor_handler(flavor, "test_placement"))
        self.assertEqual(self.vhi.flavor_name, "flavor_2_512")

        # Flavor returned and not in vhi with placement
        mock_flavor_instance.flavor_list.return_value = '[{"name": "flavorless"}]'
        mock_flavor_instance.create.return_value = '{"name": "flavorless"}'
        mock_placement_instance.assign_placement_to_flavor.return_value = "test_placement"
        self.assertTrue(self.vhi.flavor_handler(flavor, "test_placement"))
        self.assertEqual(self.vhi.flavor_name, "flavorless")

    @patch("onapp2vhi.inc.vhi_helpers.VinfraUser", autospec=True)
    def test_verify_user_exists(self, mock_user):
        mock_user_instance = mock_user.return_value
        mock_user_instance.user_list.return_value = '[{"name": "test_user", "email": "a@a.com"}]'
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
        mock_user_instance.user_list.return_value =\
            '[{"name": "test_user", "email": "Migration@user.com"}]'

        mock_image_instance = mock_image.return_value

        # user exist
        mock_image_instance.images.return_value = json.dumps([{"some_output": "some_value"}])
        self.assertTrue(self.vhi._create_domain_service_user())

        # user exist but wrong password
        mock_image_instance.images.side_effect = VinfraError(command='the failed command', exit_code=1, output='failed password')
        self.assertTrue(self.vhi._create_domain_service_user())

        # user does not exist failed created
        mock_user_instance.user_list.return_value =\
            '[{"name": "test_user", "email": "no_exist@user.com"}]'
        mock_user_instance.create.side_effect = VinfraError(command='create command',
                                                            exit_code=1,
                                                            output='failed user create')
        self.assertFalse(self.vhi._create_domain_service_user())

        # user does not exist create success
        mock_user_instance.user_list.return_value =\
            '[{"name": "test_user", "email": "no_exist@user.com"}]'
        mock_user_instance.create.side_effect = None
        mock_user_instance.create.return_value = "some_output"
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
        mock_user_instance.user_list.return_value = '[{"email": "Migration@user.com"}, '\
            '{"email": "migration_helper@user.com"}]'
        mock_image_instance.images.return_value = [0, "some_output"]

        self.vhi.create_service_user()
        self.assertEqual(self.cfg.vhi_conf["vinfra_user"], "migration_user")

        # service user not exists failed creation

        mock_user_instance.user_list.return_value = '[{"email": "Migration@user.com"}] '

        mock_user_instance.create.return_value = '{"email": "migration_helper@user.com",'\
            '"system_permissions": "no_permission", "name": "migration_user",'\
            '"enable": true, "assign-domain": ["Default", "compute"],'\
            '"domain": "Default"}'

        self.assertFalse(self.vhi.create_service_user())

        # service user not exists success creation

        mock_user_instance.user_list.return_value = '[{"email": "Migration@user.com"}]'

        mock_user_instance.create.return_value =\
            '{"email": "migration_helper@user.com",'\
            '"system_permissions": "compute", "name": "migration_user",'\
            '"enable": true, "assign-domain": ["Default", "compute"],'\
            '"domain": "Default"}'
        mock_password.return_value = "new_password"
        mock_node_instance.list_node.side_effect = None
        mock_node_instance.list_node.return_value = '[]'

        self.assertTrue(self.vhi.create_service_user())
        self.assertEqual(self.cfg.vhi_conf["vinfra_pass"], "new_password")

    @patch("builtins.open", mock_open())
    @patch("onapp2vhi.inc.vhi_helpers.VinfraProject", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.VinfraStoragePolicies", autospec=True)
    @patch("onapp2vhi.inc.vhi_helpers.VinfraQuotas", autospec=True)
    def test_create_project(self, mock_quota, mock_policy, mock_project):
        # project exist
        mock_project_instance = mock_project.return_value
        mock_project_instance.projects.return_value =\
            '[{"name": "project_roman.holovko@virtuozzo.com"}]'

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
        mock_project_instance.projects.return_value = '[{"name": "project_test"}]'
        mock_project_instance.create.return_value =\
            '{"name": "project_roman.holovko@virtuozzo.com", "id": "4"}'

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
        mock_storage_instance.storage_policy_list.return_value = '[{"name": "Default"}]'

        self.assertTrue(self.vhi.create_project(user_data))

        # Project does not exist and storage quota limited

        mock_project_instance = mock_project.return_value
        mock_project_instance.projects.return_value = '[{"name": "project_test"}]'
        mock_project_instance.create.return_value =\
            '{"name": "project_roman.holovko@virtuozzo.com", "id": "4"}'

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
        mock_storage_instance.storage_policy_list.return_value = '[{"name": "Default"}]'

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
        mock_user_instance.user_list.return_value = '[{"email": "roman.holovko@virtuozzo.com"}]'

        result, passwd = self.vhi.create_user(user_data)
        self.assertTrue(result)
        self.assertEqual(len(passwd), 24)

        # user does not exist with admin role
        mock_user_instance = mock_user.return_value
        mock_user_instance.user_list.return_value = '[{"email": "fake@email.com"}]'
        mock_user_instance.create.return_value = '{"id": 888}'

        result, passwd = self.vhi.create_user(user_data_admin)
        self.assertTrue(result)
        self.assertEqual(len(passwd), 24)
        self.assertEqual(self.vhi.user_id, 888)

        # user does not exist with non-admin role
        mock_user_instance = mock_user.return_value
        mock_user_instance.user_list.return_value = '[{"email": "fake@email.com"}]'
        mock_user_instance.create.return_value = '{"id": 777}'

        result, passwd = self.vhi.create_user(user_data)
        self.assertTrue(result)
        self.assertEqual(len(passwd), 24)
        self.assertEqual(self.vhi.user_id, 777)


class TestVhiHelpersNoVinfraMocks(unittest.TestCase):

    @patch("onapp2vhi.inc.vhi_helpers.SSH", autospec=True)
    def setUp(self, mock_ssh):
        self.mock_cfg = Mock(spec=OnApp2VHIConfig)
        self.mock_cfg.vhi_conf = {
            'cp_ip': 'dummycp.unittest.test',
            'hv_ip': 'dummyhv.unittest.test',
            'vinfra_project': 'test_proj',
            'vinfra_domain': 'behave',
            'domain_id': '58fa18b2cefc4bad8a52f11008dfbf72',
            'cloud_ssh_port': 22,
            'vinfra_user': 'migration_user',
            'vinfra_domain_user': 'dom_migration_user_behave',
        }
        self.mock_cfg.ADMIN_AUTH = 'vinfra admin_auth'
        self.mock_cfg.VINFRA_AUTH = 'vinfra vinfra_auth'
        self.mock_cfg.DOMAIN_AUTH = 'vinfra domain_auth'
        self.vhi = Vhi(self.mock_cfg)

        self.mock_flavor_ssh = Mock(spec=SSH)
        self.mock_placement_ssh = Mock(spec=SSH)
        self.mock_hv_user_ssh = Mock(spec=SSH)
        self.mock_cp_user_ssh = Mock(spec=SSH)
        self.mock_node_ssh = Mock(spec=SSH)
        self.mock_image_ssh = Mock(spec=SSH)
        self.mock_project_ssh = Mock(spec=SSH)
        self.mock_storage_policy_ssh = Mock(spec=SSH)
        self.mock_quotas_ssh = Mock(spec=SSH)
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh.return_value = self.mock_ssh

        self.user_data = {
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

        self.user_data_admin = {
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

        self.project_data = {
            'first_name': 'unit',
            'last_name': 'test',
            'project_name': 'unittest',
            'quotas': {
                'cores': 4,
                'RAM': -1,
                'storage': '1GB',
            }
        }

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_vinfra_check_no_flavor(self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        # No flavor returned
        mock_ssh_ctor.side_effect = [
            self.mock_placement_ssh,
            self.mock_flavor_ssh,
        ]
        self.mock_flavor_ssh.execute.side_effect = [
            (2, {"name": "flavorless"}),
        ]
        self.assertFalse(self.vhi.flavor_handler(flavor))
        self.mock_flavor_ssh.execute.assert_called_once_with(
            "vinfra vinfra_auth service compute flavor list -f json")
        self.mock_placement_ssh.execute.assert_not_called()

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_vinfra_check_flavor_returned_and_exists_in_vhi(self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        # Flavor returned and exist in vhi
        mock_ssh_ctor.side_effect = [
            self.mock_placement_ssh,
            self.mock_flavor_ssh,
        ]
        self.mock_flavor_ssh.execute.side_effect = [
            (0, '[{"name": "flavor_2_512"}]'),
        ]
        self.assertTrue(self.vhi.flavor_handler(flavor))
        self.assertEqual(self.vhi.flavor_name, "flavor_2_512")
        self.mock_flavor_ssh.execute.assert_called_once_with(
            "vinfra vinfra_auth service compute flavor list -f json")
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
            (0, '[{"name": "test_placement", "id": "1234-abcdef"}]'),
            (0, 'ok'),
        ]
        self.mock_project_ssh.execute.side_effect = [
            (0, json.dumps({'id': '2345-defg'})),
        ]
        self.mock_quotas_ssh.execute.side_effect = [
            (0, json.dumps({'placement': {'1234-abcdef': {'limit': -1}}}) + 'show quotas result'),
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_placement_ssh,
            self.mock_project_ssh,
            self.mock_quotas_ssh,
            self.mock_flavor_ssh,
        ]

        self.assertTrue(self.vhi.flavor_handler(flavor, "test_placement"))
        self.assertEqual(self.vhi.flavor_name, "flavor_2_512")
        self.mock_flavor_ssh.execute.assert_called_once_with(
            "vinfra vinfra_auth service compute flavor list -f json")
        self.mock_placement_ssh.execute.assert_has_calls([
            call("vinfra admin_auth service compute placement list -f json"),
            call("vinfra admin_auth service compute placement assign --flavors flavor_2_512 "
                 "test_placement")
        ])
        self.mock_quotas_ssh.execute.assert_called_once_with(
            'vinfra admin_auth service compute quotas show 2345-defg -f json')

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_vinfra_check_flavor_returned_and_exist_in_vhi_with_placement_no_quotas(
            self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        # Flavor returned and exist in vhi with placement
        self.mock_flavor_ssh.execute.side_effect = [
            (0, '[{"name": "flavor_2_512"}]'),
        ]
        self.mock_placement_ssh.execute.side_effect = [
            (0, '[{"name": "test_placement", "id": "1234-abcdef"}]'),
            (0, 'ok'),
        ]
        self.mock_project_ssh.execute.side_effect = [
            (0, json.dumps({'id': '2345-defg'})),
        ]
        self.mock_quotas_ssh.execute.side_effect = [
            (0, 'show quotas result'),
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_placement_ssh,
            self.mock_project_ssh,
            self.mock_quotas_ssh,
            self.mock_flavor_ssh,
        ]

        self.assertFalse(self.vhi.flavor_handler(flavor, "test_placement"))

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
            (0, json.dumps([{"name": "test_placement", "id": "1234-abcdef"}])),
            (0, 'ok')
        ]
        self.mock_project_ssh.execute.side_effect = [
            (0, json.dumps({'id': '2345-defg'})),
        ]
        self.mock_quotas_ssh.execute.side_effect = [
            (0, json.dumps({'placement': {'1234-abcdef': {'limit': -1}}})),
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_placement_ssh,
            self.mock_project_ssh,
            self.mock_quotas_ssh,
            self.mock_flavor_ssh,
        ]

        self.assertTrue(self.vhi.flavor_handler(flavor, "test_placement"))
        self.assertEqual(self.vhi.flavor_name, "flavorless")
        self.mock_flavor_ssh.execute.assert_has_calls([
            call("vinfra vinfra_auth service compute flavor list -f json"),
            call("vinfra vinfra_auth service compute flavor create flavor_2_512 --vcpus=2 "
                 "--ram=512 -f json")
        ])
        self.mock_placement_ssh.execute.assert_has_calls([
            call("vinfra admin_auth service compute placement list -f json"),
            call("vinfra admin_auth service compute placement assign --flavors flavorless "
                 "test_placement")
        ])
        self.mock_quotas_ssh.execute.assert_called_once_with(
            'vinfra admin_auth service compute quotas show 2345-defg -f json')

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_placement_listing_failed(self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        self.mock_placement_ssh.execute.side_effect = [(1, 'listing failed!')]

        mock_ssh_ctor.side_effect = [
            self.mock_placement_ssh,
        ]

        self.assertFalse(self.vhi.flavor_handler(flavor, "test_placement"))

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_no_placements(self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        self.mock_placement_ssh.execute.side_effect = [
            (0, json.dumps([])),
        ]

        mock_ssh_ctor.side_effect = [
            self.mock_placement_ssh,
        ]

        self.assertFalse(self.vhi.flavor_handler(flavor, "test_placement"))

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_placement_not_found(self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        self.mock_placement_ssh.execute.side_effect = [
            (0, json.dumps([{"name": "test_placement!", "id": "1234-abcdef"}])),
        ]

        mock_ssh_ctor.side_effect = [
            self.mock_placement_ssh,
        ]

        self.assertFalse(self.vhi.flavor_handler(flavor, "test_placement"))

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_project_show_failed(self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        self.mock_placement_ssh.execute.side_effect = [
            (0, json.dumps([{"name": "test_placement", "id": "1234-abcdef"}])),
        ]
        self.mock_project_ssh.execute.side_effect = [(1, 'show failed!')]

        mock_ssh_ctor.side_effect = [
            self.mock_placement_ssh,
            self.mock_project_ssh,
        ]

        self.assertFalse(self.vhi.flavor_handler(flavor, "test_placement"))

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_quotas_show_quota_failed(self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        self.mock_placement_ssh.execute.side_effect = [
            (0, json.dumps([{"name": "test_placement", "id": "1234-abcdef"}])),
        ]
        self.mock_project_ssh.execute.side_effect = [
            (0, json.dumps({'id': '2345-defg'})),
        ]
        self.mock_quotas_ssh.execute.side_effect = [(1, 'show quotas failed!')]

        mock_ssh_ctor.side_effect = [
            self.mock_placement_ssh,
            self.mock_project_ssh,
            self.mock_quotas_ssh,
        ]

        self.assertFalse(self.vhi.flavor_handler(flavor, "test_placement"))

    @patch("onapp2vhi.inc.vinfra_wrapper.SSH")
    def test_flavor_handler_project_placement_quota_not_set(self, mock_ssh_ctor):
        flavor = {"vcpus": 2, "ram": 512, "name": "flavor_2_512"}

        self.mock_placement_ssh.execute.side_effect = [
            (0, json.dumps([{"name": "test_placement", "id": "1234-abcdef"}])),
        ]
        self.mock_project_ssh.execute.side_effect = [
            (0, json.dumps({'id': '2345-defg'})),
        ]
        self.mock_quotas_ssh.execute.side_effect = [
            (0, json.dumps({'placement': {'1234-abcdef': {'limit': 0}}}))
        ]

        mock_ssh_ctor.side_effect = [
            self.mock_placement_ssh,
            self.mock_project_ssh,
            self.mock_quotas_ssh,
        ]

        self.assertFalse(self.vhi.flavor_handler(flavor, "test_placement"))

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_create_user_user_exists(self, mock_ssh_ctor):
        # user exists
        self.mock_hv_user_ssh.execute.side_effect = [
            (0, '[{"email": "roman.holovko@virtuozzo.com"}]'),  # list users reply
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_cp_user_ssh,     # in create_user()
            self.mock_hv_user_ssh,     # in _verify_user_exists()
        ]

        result, passwd = self.vhi.create_user(self.user_data)
        self.assertTrue(result)
        self.assertEqual(len(passwd), 24)

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_create_user_with_admin_role_user_not_exists(self, mock_ssh_ctor):
        # user does not exist with admin role
        self.mock_hv_user_ssh.execute.side_effect = [
            (0, '[{"email": "fake@email.com"}] '),  # list users reply
            (0, '{"id": 888}'),                     # create result
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_hv_user_ssh,     # in create_user()
            self.mock_hv_user_ssh,     # in _verify_user_exists()
        ]

        result, passwd = self.vhi.create_user(self.user_data_admin)
        self.assertTrue(result)
        self.assertEqual(len(passwd), 24)
        self.assertEqual(self.vhi.user_id, 888)

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_create_user_with_non_admin_user_not_exists(self, mock_ssh_ctor):
        # user does not exist with non-admin role
        self.mock_hv_user_ssh.execute.side_effect = [
            (0, '[{"email": "fake@email.com"}] '),  # list user reply
            (0, '{"id": 777}'),                     # create result
        ]
        mock_ssh_ctor.return_value = self.mock_hv_user_ssh

        result, passwd = self.vhi.create_user(self.user_data)
        self.assertTrue(result)
        self.assertEqual(len(passwd), 24)
        self.assertEqual(self.vhi.user_id, 777)

    @patch('builtins.open', mock_open)
    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_create_migration_user_ok_correct_migration_user_domain_default(self, mock_ssh_ctor):
        self.vhi.vinfra_domain = 'Default'
        self.mock_hv_user_ssh.execute.side_effect = [
            (0, json.dumps([])),                                        # migration user not created
        ]
        self.mock_cp_user_ssh.execute.side_effect = [
            (0, json.dumps({'email': 'migration_helper@user.com',
                            'name': 'migration_user',
                            'system_permissions': 'compute'})),  # create ok
        ]
        self.mock_node_ssh.execute.side_effect = [
            (0, json.dumps([{'result': 'ok'}])),
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_cp_user_ssh,  # in create_service_user
            self.mock_hv_user_ssh,  # in _verify_user_exists
            self.mock_node_ssh,     # verify service user with node list
        ]
        self.assertTrue(self.vhi.create_service_user())

    # TODO! cover case create migration user failed

    @patch('builtins.open', mock_open)
    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_migration_user_wrong_password_password_update_ok(self, mock_ssh_ctor):
        self.vhi.vinfra_domain = 'Default'
        self.mock_hv_user_ssh.execute.side_effect = [
            (0, json.dumps([{'email': 'migration_helper@user.com'}])),  # migration user present
        ]
        self.mock_node_ssh.execute.side_effect = [
            (1, json.dumps([{'result': 'not ok, wrong password'}])),
            (0, json.dumps([{'result': 'ok'}])),
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_cp_user_ssh,  # in create_service_user
            self.mock_hv_user_ssh,  # in _verify_user_exists
            self.mock_node_ssh,     # verify service user with node list
            self.mock_node_ssh,     # verify service user with node list
        ]
        self.assertTrue(self.vhi.create_service_user())

    @patch('builtins.open', mock_open)
    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_migration_user_wrong_password_password_update_failed(self, mock_ssh_ctor):
        self.vhi.vinfra_domain = 'Default'
        self.mock_hv_user_ssh.execute.side_effect = [
            (0, json.dumps([{'email': 'migration_helper@user.com'}])),  # migration user present
        ]
        self.mock_node_ssh.execute.side_effect = [
            (1, json.dumps([{'result': 'not ok, wrong password'}])),
            (1, json.dumps([{'result': 'not ok, wrong password'}])),
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_cp_user_ssh,  # in create_service_user
            self.mock_hv_user_ssh,  # in _verify_user_exists
            self.mock_node_ssh,     # verify service user with node list
            self.mock_node_ssh,     # verify service user with node list
        ]
        self.assertFalse(self.vhi.create_service_user())

    @patch('builtins.open', mock_open)
    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_create_domain_migration_user_ok_correct_migration_user_domain_different(
            self, mock_ssh_ctor):
        self.mock_hv_user_ssh.execute.side_effect = [
            (0, json.dumps([{'email': 'fake@fake.com'}])),    # domain migration user not created
            (0, json.dumps([{'email': 'migration_helper@user.com'}]))   # migration user created
        ]
        self.mock_cp_user_ssh.execute.side_effect = [
            (0, json.dumps({'result': 'ok'})),  # create ok
            (0, json.dumps({'result': 'ok'})),  # set user ok
        ]
        self.mock_node_ssh.execute.side_effect = [
            (0, json.dumps([{'result': 'ok'}])),
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_cp_user_ssh,  # in create_service_user
            self.mock_cp_user_ssh,  # in _create_domain_service_user
            self.mock_hv_user_ssh,  # in _verify_user_exists
            self.mock_hv_user_ssh,  # in _verify_user_exists
            self.mock_node_ssh,     # verify service user with node list
        ]
        self.assertTrue(self.vhi.create_service_user())

    # TODO! cover case create domain migration user failed

    @patch('builtins.open', mock_open)
    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_domain_migration_user_wrong_password_update_ok(self, mock_ssh_ctor):
        self.mock_hv_user_ssh.execute.side_effect = [
            (0, json.dumps([{'email': 'behave@user.com'}])),   # dom migration user present
            (0, json.dumps([{'email': 'migration_helper@user.com'}]))   # migration user created
        ]
        self.mock_image_ssh.execute.side_effect = [
            (1, json.dumps([{'result': 'not ok, password failed'}])),
        ]
        self.mock_node_ssh.execute.side_effect = [
            (0, json.dumps([{'result': 'ok'}])),
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_cp_user_ssh,  # in create_service_user
            self.mock_cp_user_ssh,  # in _create_domain_service_user
            self.mock_hv_user_ssh,  # in _verify_user_exists
            self.mock_image_ssh,     # verify service user with image list
            self.mock_hv_user_ssh,  # in _verify_user_exists
            self.mock_node_ssh,     # verify service user with node list
        ]
        self.assertTrue(self.vhi.create_service_user())

    # TODO add handling update migration user password failed

    @patch('builtins.open', mock_open)
    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_create_project_ok(self, mock_ssh_ctor):
        self.mock_project_ssh.execute.side_effect = [
            (0, json.dumps([])),     # no existing projects
            (0, json.dumps({'id': 'project_id_unit_test',
                            'name': 'unittesting',
                            'first_name': 'unit',
                            'last_name': 'test',
                            })),
        ]
        self.mock_storage_policy_ssh.execute.side_effect = [
            (0, json.dumps([{'name': 'dummy policy'}])),
        ]
        self.mock_quotas_ssh.execute.side_effect = [
            (0, json.dumps({'result': 'quota updated'})),
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_project_ssh,
            self.mock_storage_policy_ssh,
            self.mock_quotas_ssh,
        ]

        self.assertTrue(self.vhi.create_project(self.project_data))
        self.mock_project_ssh.execute.assert_has_calls([
            call('vinfra admin_auth domain project list --domain behave -f json'),
            call('vinfra admin_auth domain project create unittest --domain behave '
                 '--description "OnApp User unit test" --enable -f json'),
        ])
        self.mock_storage_policy_ssh.execute.assert_called_once_with(
            'vinfra vinfra_auth service compute storage-policy list -f json')
        self.mock_quotas_ssh.execute.assert_called_once_with(
            'vinfra vinfra_auth service compute quotas update project_id_unit_test --cores "4" '
            '--storage-policy dummy policy:1GBG')

    @patch('builtins.open', mock_open)
    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_create_project_already_exists(self, mock_ssh_ctor):
        self.mock_project_ssh.execute.side_effect = [
            (0, json.dumps([{'id': 'project_id_unit_test',
                             'name': 'unittest',
                             }])),
        ]
        mock_ssh_ctor.side_effect = [
            self.mock_project_ssh,
        ]
        self.assertTrue(self.vhi.create_project(self.project_data))

    # TODO! cover create project failed
    # TODO! cover no quota change
