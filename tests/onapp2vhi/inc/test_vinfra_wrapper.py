from unittest import TestCase
from mock import patch, Mock, mock_open

from onapp2vhi.inc.ssh_connector import SSH
from onapp2vhi.inc.vinfra_wrapper import (
    VinfraBase,
    VinfraError,
    VinfraCommand,
    VinfraServiceCompute,
    VinfraNode,
    VinfraImage,
    VinfraDomain,
    VinfraServiceComputeNetwork,
    VinfraServiceComputeServer,
    VinfraServerInterface,
    VinfraSecurityGroups,
    VinfraSGRules,
    VinfraProject,
    VinfraFlavor,
    VinfraUser,
    VinfraQuotas,
    VinfraStoragePolicies,
    VinfraPlacement,
)
from onapp2vhi.utilities.config import OnApp2VHIConfig


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
hv_ip = unittest.onapp2vhi.test
cp_ip = unittestcp.onapp2vhi.test
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
ssh_key = /path/to/your/ssh_key/id_rsa
"""

class VinfraErrorTestCase(TestCase):

    def test_password_in_command_is_hidden(self):
        command = "vinfra --password '1234'"
        output = 'some output'
        msg = str(VinfraError(command, 1, output))
        self.assertNotIn('1234', msg)
        self.assertIn('*hidden*', msg)


class VinfraBaseConstructorTestCase(TestCase):

    @patch("builtins.open", mock_open(read_data=TEST_CFG))
    def setUp(self):
        self.mock_config = OnApp2VHIConfig.load_config('test.ini')

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_no_constructor_params(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        mock_ssh = Mock(spec=SSH)
        mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = mock_ssh

        base = VinfraBase(self.mock_config)

        mock_ssh_ctor.assert_called_with(
            host='unittestcp.onapp2vhi.test',
            connect_timeout=300,
            channel_timeout=3600,
            ssh_key=self.mock_config.ssh_key)

        base.execute('test command')
        mock_ssh.execute.assert_called_with('test command -f json')
        self.assertEqual(base.vinfra_root, "vinfra --vinfra-username='admin' "
                                           "--vinfra-password='ui_admin_password'")

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_constructor_with_access_domain(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        mock_ssh = Mock(spec=SSH)
        mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = mock_ssh

        base = VinfraBase(self.mock_config, access_domain=True)

        mock_ssh_ctor.assert_called_with(
            host='unittestcp.onapp2vhi.test',
            connect_timeout=300,
            channel_timeout=3600,
            ssh_key=self.mock_config.ssh_key)

        base.execute('test command')
        mock_ssh.execute.assert_called_with('test command -f json')
        self.assertEqual(base.vinfra_root,
                         "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
                         "--vinfra-domain=Migration")

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_constructor_with_service_user(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        mock_ssh = Mock(spec=SSH)
        mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = mock_ssh

        base = VinfraBase(self.mock_config, service_user=True)

        mock_ssh_ctor.assert_called_with(
            host='unittestcp.onapp2vhi.test',
            connect_timeout=300,
            channel_timeout=3600,
            ssh_key=self.mock_config.ssh_key)

        base.execute('test command')
        mock_ssh.execute.assert_called_with('test command -f json')
        self.assertEqual(base.vinfra_root, "vinfra --vinfra-username='user_login' "
                                           "--vinfra-password='user_pwd'")

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_constructor_with_domain_service_user(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        mock_ssh = Mock(spec=SSH)
        mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = mock_ssh

        base = VinfraBase(self.mock_config, domain_service_user=True)

        mock_ssh_ctor.assert_called_with(
            host='unittestcp.onapp2vhi.test',
            connect_timeout=300,
            channel_timeout=3600,
            ssh_key=self.mock_config.ssh_key)

        base.execute('test command')
        mock_ssh.execute.assert_called_with('test command -f json')
        self.assertEqual(base.vinfra_root, "vinfra --vinfra-username='domain_user' "
                                           "--vinfra-password='domain_pass'")

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_constructor_with_domain_diff_connection_timeout(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        mock_ssh = Mock(spec=SSH)
        mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = mock_ssh

        base = VinfraBase(self.mock_config, connect_timeout=100)

        mock_ssh_ctor.assert_called_with(
            host='unittestcp.onapp2vhi.test',
            connect_timeout=100,
            channel_timeout=3600,
            ssh_key=self.mock_config.ssh_key)

        base.execute('test command')
        mock_ssh.execute.assert_called_with('test command -f json')
        self.assertEqual(base.vinfra_root, "vinfra --vinfra-username='admin' "
                                           "--vinfra-password='ui_admin_password'")

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_constructor_with_domain_diff_channel_timeout(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        mock_ssh = Mock(spec=SSH)
        mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = mock_ssh

        base = VinfraBase(self.mock_config, channel_timeout=100)

        mock_ssh_ctor.assert_called_with(
            host='unittestcp.onapp2vhi.test',
            connect_timeout=300,
            channel_timeout=100,
            ssh_key=self.mock_config.ssh_key)

        base.execute('test command')
        mock_ssh.execute.assert_called_with('test command -f json')
        self.assertEqual(base.vinfra_root, "vinfra --vinfra-username='admin' "
                                           "--vinfra-password='ui_admin_password'")

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_constructor_with_cp_ip(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        mock_ssh = Mock(spec=SSH)
        mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = mock_ssh

        base = VinfraBase(self.mock_config, cp_ip=True)

        mock_ssh_ctor.assert_called_with(
            host='unittest.onapp2vhi.test',
            connect_timeout=300,
            channel_timeout=3600,
            ssh_key=self.mock_config.ssh_key)

        base.execute('test command')
        mock_ssh.execute.assert_called_with('test command -f json')
        self.assertEqual(base.vinfra_root, "vinfra --vinfra-username='admin' "
                                           "--vinfra-password='ui_admin_password'")

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_execute_with_long(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        mock_ssh = Mock(spec=SSH)
        mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = mock_ssh

        base = VinfraBase(self.mock_config)

        base.execute('test command', long=True)
        mock_ssh.execute.assert_called_with('test command --long -f json')
        self.assertEqual(base.vinfra_root, "vinfra --vinfra-username='admin' "
                                           "--vinfra-password='ui_admin_password'")

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_execute_with_no_json(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        mock_ssh = Mock(spec=SSH)
        mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = mock_ssh

        base = VinfraBase(self.mock_config)

        base.execute('test command', json=False)
        mock_ssh.execute.assert_called_with('test command')
        self.assertEqual(base.vinfra_root, "vinfra --vinfra-username='admin' "
                                           "--vinfra-password='ui_admin_password'")


class VinfraCommandTestCase(TestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    @patch("builtins.open", mock_open(read_data=TEST_CFG))
    def setUp(self, mock_ssh_ctor):
        self.mock_config = OnApp2VHIConfig.load_config('test.ini')

        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraCommand(self.mock_config, self.mock_config.ADMIN_AUTH)

    def test_execute_command(self):
        mock_output = (0, 'ok')
        self.mock_ssh.execute.return_value = mock_output

        self.command.execute('test command')

        self.mock_ssh.execute.assert_called_with("vinfra --vinfra-username='admin' "
                                                 "--vinfra-password='ui_admin_password' test command")

    def test_execute_with_error(self):
        mock_output = (1, 'not ok')
        self.mock_ssh.execute.return_value = mock_output

        with self.assertRaises(VinfraError) as e:
            self.command.execute('test command')

            self.mock_ssh.execute.assert_called_with(
                'vinfra special_param test command -f json')
            self.assertEqual(str(e), 'VinfraError: command = vinfra special_param test -f json, '
                                     'exit_code = 1, output = not ok')

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_constructor_with_vinfra_access(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        self.mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = self.mock_ssh

        command = VinfraCommand(self.mock_config, vinfra_access="vinfra special_param")

        command.execute('test command')

        mock_ssh_ctor.assert_called_with(
            host='unittestcp.onapp2vhi.test', port=2222, connect_timeout=300, channel_timeout=3600,
            ssh_key='/path/to/your/ssh_key/id_rsa')
        self.mock_ssh.execute.assert_called_with(
            'vinfra special_param test command')


class VinfraBaseTestCase(TestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    @patch("builtins.open", mock_open(read_data=TEST_CFG))
    def setUp(self, mock_ssh_ctor):
        super().setUp()
        self.mock_config = OnApp2VHIConfig.load_config('test.ini')

        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self._create_command()

    def _create_command(self):
        self.command = VinfraBase(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='admin' "
                                                   "--vinfra-password='ui_admin_password'")

    def test_execute_command(self):
        mock_output = (0, 'ok')
        self.mock_ssh.execute.return_value = mock_output

        output = self.command.execute('test command')

        self.mock_ssh.execute.assert_called_with("test command -f json")
        self.assertEqual(output, 'ok')

    def test_execute_failed(self):
        mock_output = (1, 'not ok')
        self.mock_ssh.execute.return_value = mock_output

        with self.assertRaises(VinfraError) as e:
            self.command.execute('test command')

            self.mock_ssh.execute.assert_called_with("test command -f json")
            self.assertEqual(repr(e), '')


class VinfraServiceComputeTestCase(VinfraBaseTestCase):

    def _create_command(self):
        self.command = VinfraServiceCompute(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='admin' "
                                                   "--vinfra-password='ui_admin_password' "
                                                   "service compute")


class VinfraNodeTestCase(VinfraServiceComputeTestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def _create_command(self, mock_ssh_ctor):
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraNode(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='user_login' "
                                                   "--vinfra-password='user_pwd' "
                                                   "service compute node")

    def test_list_node(self):
        mock_ssh_execute_results = (0, 'list_node_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.list_node()

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='user_login' --vinfra-password='user_pwd' "
            "service compute node list -f json")
        self.assertEqual(results, 'list_node_results')


class VinfraImageTestCase(VinfraServiceComputeTestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def _create_command(self, mock_ssh_ctor):
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraImage(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='domain_user' "
                                                   "--vinfra-password='domain_pass' "
                                                   "--vinfra-domain=Migration "
                                                   "service compute image")

    def test_images(self):
        mock_ssh_execute_results = (0, 'image_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.images()

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='domain_user' --vinfra-password='domain_pass' "
            "--vinfra-domain=Migration service compute image list -f json")
        self.assertEqual(results, 'image_results')


class VinfraDomainTestCase(VinfraBaseTestCase):

    def _create_command(self):
        self.command = VinfraDomain(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='admin' "
                                                   "--vinfra-password='ui_admin_password' "
                                                   "domain")


class VinfraServiceComputeNetworkTestCase(VinfraServiceComputeTestCase):

    def _create_command(self):
        with patch('onapp2vhi.inc.vinfra_wrapper.SSH', return_value=self.mock_ssh):
            self.command = VinfraServiceComputeNetwork(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='admin' "
                                                   "--vinfra-password='ui_admin_password' "
                                                   "service compute network")

    def test_list(self):
        self.mock_ssh.execute.return_value = (0, 'mock_result')

        result = self.command.list()
        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute network list --long -f json"
        )
        self.assertEqual(result, 'mock_result')

    def test_show(self):
        self.mock_ssh.execute.return_value = (0, 'mock_result')

        result = self.command.show('dummy_network')
        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute network show dummy_network --long -f json"
        )
        self.assertEqual(result, 'mock_result')


class VinfraServiceComputeServerTestCase(VinfraServiceComputeTestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def _create_command(self, mock_ssh_ctor):
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraServiceComputeServer(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='admin' "
                                                   "--vinfra-password='ui_admin_password' "
                                                   "service compute server")

    def test_create(self):
        mock_ssh_execute_results = (0, 'create_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.create("test_server", test_key='test_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute server create test_server --test_key test_value -f json")
        self.assertEquals(results, 'create_results')

    def test_list_server(self):
        mock_ssh_execute_results = (0, 'list_server_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.list_server()

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute server list --long -f json")
        self.assertEquals(results, 'list_server_results')

    def test_show(self):
        mock_ssh_execute_results = (0, 'show_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.show('test_server')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute server show test_server -f json")
        self.assertEquals(results, 'show_results')


class VinfraServerInterfaceTestCase(VinfraServiceComputeServerTestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def _create_command(self, mock_ssh_ctor):
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraServerInterface(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='admin' "
                                                   "--vinfra-password='ui_admin_password' "
                                                   "service compute server iface")

    def test_create(self):
        mock_ssh_execute_results = (0, 'create_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.create("test_server", test_key='test_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute server iface create test_server --test_key test_value -f json")
        self.assertEquals(results, 'create_results')

    def test_list_server(self):
        mock_ssh_execute_results = (0, 'list_server_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.list_server('test_server')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute server iface list --server test_server -f json")
        self.assertEquals(results, 'list_server_results')

        self.command.list_server('test_server', a_key='a_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute server iface list --server test_server --a_key a_value -f json")

    def test_show(self):
        mock_ssh_execute_results = (0, 'show_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.show('test_server')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute server iface show test_server -f json")
        self.assertEquals(results, 'show_results')

    def test_set(self):
        mock_ssh_execute_results = (0, 'set_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.set('eth0', a_key='a_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute server iface set eth0 --spoofing-protection-disable --a_key a_value "
            "-f json")
        self.assertEquals(results, 'set_results')

        self.command.set('eth0', a_key='a_value', another_key='another_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute server iface set eth0 --spoofing-protection-disable --a_key a_value "
            "--another_key another_value -f json")

        self.command.set('eth0', vm_name='test_vm', a_key='a_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute server iface set eth0 --server test_vm --spoofing-protection-disable "
            "--a_key a_value -f json")

        self.command.set('eth0', spoofing=True, a_key='a_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute server iface set eth0 --spoofing-protection-enable "
            "--a_key a_value -f json")


class VinfraSecurityGroupsTestCase(VinfraServiceComputeTestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def _create_command(self, mock_ssh_ctor):
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraSecurityGroups(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='admin' "
                                                   "--vinfra-password='ui_admin_password' "
                                                   "service compute security-group")

    def test_create(self):
        mock_ssh_execute_results = (0, 'create_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.create('test-security-group')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute security-group create test-security-group -f json")
        self.assertEquals(results, 'create_results')

        self.command.create('test-security-group', 'a group description')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute security-group create test-security-group "
            "--description \"a group description\" -f json")

    def test_list_security_group(self):
        mock_ssh_execute_results = (0, 'list_security_group_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.list_security_group()

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute security-group list -f json")
        self.assertEquals(results, 'list_security_group_results')

        self.command.list_security_group(a_key='a_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute security-group list --a_key a_value -f json")


class VinfraSGRulesTestCase(VinfraServiceComputeTestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def _create_command(self, mock_ssh_ctor):
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraSGRules(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='admin' "
                                                   "--vinfra-password='ui_admin_password' "
                                                   "service compute security-group rule")

    def test_create(self):
        mock_ssh_execute_results = (0, 'create_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.create('security_group_name')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute security-group rule create security_group_name --ingress -f json")
        self.assertEquals(results, 'create_results')

        self.command.create('security_group_name', a_key='a_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute security-group rule create security_group_name --a_key a_value "
            "--ingress -f json")

        self.command.create('security_group_name', a_key='a_value', another_key='another_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute security-group rule create security_group_name --a_key a_value "
            "--another_key another_value --ingress -f json")

    def test_list_sg_rules(self):
        mock_ssh_execute_results = (0, 'list_sg_rules_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        self.command.list_sg_rules()

        # TODO! this is a possible bug
        self.mock_ssh.execute.assert_called_with(" -f json")

        results = self.command.list_sg_rules(list_all=True)

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute security-group rule list -f json")
        self.assertEquals(results, 'list_sg_rules_results')

        self.command.list_sg_rules('test_sg_group')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute security-group rule list test_sg_group -f json")

        self.command.list_sg_rules(list_all=True, a_key='a_value', another_key='another_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute security-group rule list --a_key a_value --another_key another_value "
            "-f json")


class VinfraProjectTestCase(VinfraDomainTestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def _create_command(self, mock_ssh_ctor):
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraProject(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='admin' "
                                                   "--vinfra-password='ui_admin_password' "
                                                   "domain project")

    def test_create(self):
        mock_ssh_execute_results = (0, 'create_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.create('test_project', 'test_domain')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "domain project create test_project --domain test_domain --enable -f json")
        self.assertEquals(results, 'create_results')

        self.command.create('test_project', 'test_domain', description='test_description')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "domain project create test_project --domain test_domain --description \"test_description\" "
            "--enable -f json")

        self.command.create('test_project', 'test_domain', enable=False)

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "domain project create test_project --domain test_domain --disable -f json")

    def test_projects(self):
        mock_ssh_execute_results = (0, 'project_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.projects()

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "domain project list -f json")
        self.assertEquals(results, 'project_results')

        self.command.projects(a_key='a_value', another_key='another_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "domain project list --a_key a_value --another_key another_value -f json")

        self.command.projects('test_project_name')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "domain project list test_project_name -f json")

        self.command.projects('test_project_name', a_key='a_value', another_key='another_value')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "domain project list test_project_name --a_key a_value --another_key another_value -f json")

    def test_show(self):
        mock_ssh_execute_results = (0, 'show_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.show('test_project_name', 'test_domain')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "domain project show --domain test_domain test_project_name -f json")
        self.assertEquals(results, 'show_results')


class VinfraFlavorTestCase(VinfraServiceComputeTestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def _create_command(self, mock_ssh_ctor):
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraFlavor(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='admin' "
                                                   "--vinfra-password='ui_admin_password' "
                                                   "service compute flavor")

    def test_create(self):
        mock_ssh_execute_results = (0, 'ok')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        result = self.command.create('test_flavor_name', 1, 8)

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute flavor create test_flavor_name --vcpus=1 --ram=8 -f json")
        self.assertEqual(result, 'ok')

    def test_flavor_list(self):
        mock_ssh_execute_results = (0, 'flavor_list_result')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        result = self.command.flavor_list()

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute flavor list -f json")
        self.assertEqual(result, 'flavor_list_result')


class VinfraUserTestCase(VinfraBaseTestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def _create_command(self, mock_ssh_ctor):
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraUser(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='admin' "
                                                   "--vinfra-password='ui_admin_password' "
                                                   "domain user")

    def test_user_list(self):
        mock_ssh_execute_results = (0, 'user_list_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.user_list('test_domain')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "domain user list --domain=test_domain -f json")
        self.assertEquals(results, 'user_list_results')

    def test_create(self):
        mock_user_data = { 'name': 'mock_user', }
        mock_ssh_execute_results = (0, 'create_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.create(mock_user_data, 'test_password')

        self.mock_ssh.execute.assert_called_with(
            "echo -e \"test_password\" | vinfra --vinfra-username='admin' "
            "--vinfra-password='ui_admin_password' domain user create mock_user -f json")
        self.assertEquals(results, 'create_results')

        mock_user_data = { 'dummy': True, 'name': 'mock_user', }

        self.command.create(mock_user_data, 'test_password')

        self.mock_ssh.execute.assert_called_with(
            "echo -e \"test_password\" | vinfra --vinfra-username='admin' "
            "--vinfra-password='ui_admin_password' domain user create mock_user -f json")

        mock_user_data = { 'name': 'mock_user', 'a_property': 'a_value'}

        self.command.create(mock_user_data, 'test_password')

        self.mock_ssh.execute.assert_called_with(
            "echo -e \"test_password\" | vinfra --vinfra-username='admin' "
            "--vinfra-password='ui_admin_password' domain user create mock_user "
            "--a_property \"a_value\" -f json")

        mock_user_data = {
            'name': 'mock_user',
            'a_property': 'a_value',
            'another_property': 'another_value'
        }

        self.command.create(mock_user_data, 'test_password')

        self.mock_ssh.execute.assert_called_with(
            "echo -e \"test_password\" | vinfra --vinfra-username='admin' "
            "--vinfra-password='ui_admin_password' domain user create mock_user "
            "--a_property \"a_value\" --another_property \"another_value\" -f json")

        mock_user_data = { 'name': 'mock_user', 'assign-domain': ['dummy_domain', 'compute']}

        self.command.create(mock_user_data, 'test_password')

        self.mock_ssh.execute.assert_called_with(
            "echo -e \"test_password\" | vinfra --vinfra-username='admin' "
            "--vinfra-password='ui_admin_password' domain user create mock_user "
            "--assign-domain dummy_domain compute -f json")

        mock_user_data = { 'name': 'mock_user', 'assign': ['param1', 'param2']}

        self.command.create(mock_user_data, 'test_password')

        self.mock_ssh.execute.assert_called_with(
            "echo -e \"test_password\" | vinfra --vinfra-username='admin' "
            "--vinfra-password='ui_admin_password' domain user create mock_user "
            "--assign param1 param2 -f json")

        mock_user_data = { 'name': 'mock_user', 'enable': True }

        self.command.create(mock_user_data, 'test_password')

        self.mock_ssh.execute.assert_called_with(
            "echo -e \"test_password\" | vinfra --vinfra-username='admin' "
            "--vinfra-password='ui_admin_password' domain user create mock_user --enable -f json")

        mock_user_data = { 'name': 'mock_user', 'enable': False }

        self.command.create(mock_user_data, 'test_password')

        self.mock_ssh.execute.assert_called_with(
            "echo -e \"test_password\" | vinfra --vinfra-username='admin' "
            "--vinfra-password='ui_admin_password' domain user create mock_user -f json")

        mock_user_data = { 'name': 'mock_user', 'disable': True }

        self.command.create(mock_user_data, 'test_password')

        self.mock_ssh.execute.assert_called_with(
            "echo -e \"test_password\" | vinfra --vinfra-username='admin' "
            "--vinfra-password='ui_admin_password' domain user create mock_user --disable -f json")

        mock_user_data = { 'name': 'mock_user', 'disable': False }

        self.command.create(mock_user_data, 'test_password')

        self.mock_ssh.execute.assert_called_with(
            "echo -e \"test_password\" | vinfra --vinfra-username='admin' "
            "--vinfra-password='ui_admin_password' domain user create mock_user -f json")

    def test_show(self):
        mock_ssh_execute_results = (0, 'show_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.show('test_username', 'test_domain')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "domain user show --domain=test_domain test_username -f json")
        self.assertEquals(results, 'show_results')

    def test_set(self):
        mock_ssh_execute_results = (0, 'set_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.set('mock_user', 'mock_domain', ['domain1', 'default', 'compute'])

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "domain user set mock_user --assign-domain domain1 default --domain mock_domain -f json")
        self.assertEquals(results, 'set_results')


class VinfraQuotasTestCase(VinfraServiceComputeTestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def _create_command(self, mock_ssh_ctor):
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraQuotas(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='user_login' "
                                                   "--vinfra-password='user_pwd' "
                                                   "service compute quotas")

    def test_update_quotas(self):
        mock_ssh_execute_results = (0, 'update_quotas_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.update_quotas('mock_project_id', param1='value1', param2='value2')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='user_login' --vinfra-password='user_pwd' "
            "service compute quotas update mock_project_id --param1 \"value1\" --param2 \"value2\"")
        self.assertEquals(results, 'update_quotas_results')

        data = {
            'param1': 'value1',
            'param2': 'value2',
            'storage-policy': {
                'name': 'dummy_storage_policy',
                'size': 64,
            }
        }
        self.command.update_quotas('mock_project_id', **data)

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='user_login' --vinfra-password='user_pwd' "
            "service compute quotas update mock_project_id --param1 \"value1\" --param2 \"value2\" "
            "--storage-policy dummy_storage_policy:64G")

    def test_show_quotas(self):
        self.mock_ssh.execute.return_value = (0, 'list of quota dict')

        results = self.command.show_quotas('mock_project_id')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='user_login' --vinfra-password='user_pwd' service compute "
            "quotas show mock_project_id -f json")
        self.assertEqual(results, 'list of quota dict')


class VinfraStoragePoliciesTestCase(VinfraServiceComputeTestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def _create_command(self, mock_ssh_ctor):
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraStoragePolicies(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='user_login' "
                                                   "--vinfra-password='user_pwd' "
                                                   "service compute storage-policy")

    def test_storage_policy_list(self):
        mock_ssh_execute_results = (0, 'storage_policy_list_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.storage_policy_list()

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='user_login' --vinfra-password='user_pwd' "
            "service compute storage-policy list -f json")
        self.assertEquals(results, 'storage_policy_list_results')


class VinfraPlacementTestCase(VinfraServiceComputeTestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def _create_command(self, mock_ssh_ctor):
        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraPlacement(self.mock_config)

    def test_vinfra_root(self):
        self.assertEqual(self.command.vinfra_root, "vinfra --vinfra-username='admin' "
                                                   "--vinfra-password='ui_admin_password' "
                                                   "service compute placement")

    def test_assign_placement_to_flavor(self):
        mock_ssh_execute_results = (0, 'assign_placement_results')
        self.mock_ssh.execute.return_value = mock_ssh_execute_results

        results = self.command.assign_placement_to_flavor('mock_flavor', 'mock_placement')

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute placement assign --flavors mock_flavor mock_placement")
        self.assertEqual(results, 'assign_placement_results')

    def test_list_placement(self):
        self.mock_ssh.execute.return_value = (0, 'placement list')

        results = self.command.list()

        self.mock_ssh.execute.assert_called_with(
            "vinfra --vinfra-username='admin' --vinfra-password='ui_admin_password' "
            "service compute placement list -f json")
        self.assertEqual(results, 'placement list')
