from unittest import TestCase
from mock import patch, Mock

from onapp2vhi.inc.ssh_connector import SSH
from onapp2vhi.inc.vinfra_wrapper import VinfraBase, VinfraError, VinfraCommand
from onapp2vhi.utilities.config import OnApp2VHIConfig


class VinfraBaseTestCase(TestCase):

    def setUp(self):
        self.mock_config = Mock(spec=OnApp2VHIConfig)
        self.mock_config.ADMIN_AUTH = 'dummy_admin_auth'
        self.mock_config.VINFRA_AUTH = 'dummy_vinfra_auth'
        self.mock_config.DOMAIN_AUTH = 'dummy_domain_auth'
        self.mock_config.vhi_conf = {
            'hv_ip': 'unittest.onapp2vhi.test',
            'cloud_ssh_port': 22,
            'vinfra_domain': 'unittest-vinfra.onapp2vhi.test',
            'cp_ip': 'unittestcp.onapp2vhi.test',
        }

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
        self.assertEqual(base.vinfra_root, 'dummy_admin_auth')

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
                         'dummy_admin_auth --vinfra-domain=unittest-vinfra.onapp2vhi.test')

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
        self.assertEqual(base.vinfra_root, 'dummy_vinfra_auth')

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
        self.assertEqual(base.vinfra_root, 'dummy_domain_auth')

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
        self.assertEqual(base.vinfra_root, 'dummy_admin_auth')

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
        self.assertEqual(base.vinfra_root, 'dummy_admin_auth')

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
        self.assertEqual(base.vinfra_root, 'dummy_admin_auth')

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_execute_with_long(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        mock_ssh = Mock(spec=SSH)
        mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = mock_ssh

        base = VinfraBase(self.mock_config)

        base.execute('test command', long=True)
        mock_ssh.execute.assert_called_with('test command --long -f json')
        self.assertEqual(base.vinfra_root, 'dummy_admin_auth')

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_execute_with_no_json(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        mock_ssh = Mock(spec=SSH)
        mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = mock_ssh

        base = VinfraBase(self.mock_config)

        base.execute('test command', json=False)
        mock_ssh.execute.assert_called_with('test command')
        self.assertEqual(base.vinfra_root, 'dummy_admin_auth')


class VinfraCommandTestCase(TestCase):

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def setUp(self, mock_ssh_ctor):
        self.mock_config = Mock(spec=OnApp2VHIConfig)
        self.mock_config.ADMIN_AUTH = 'vinfra --credentials=dummy_credentials'
        self.mock_config.vhi_conf = {
            'hv_ip': 'unittest.onapp2vhi.test',
            'cloud_ssh_port': 22,
            'vinfra_domain': 'unittest-vinfra.onapp2vhi.test',
        }

        self.mock_ssh = Mock(spec=SSH)
        mock_ssh_ctor.return_value = self.mock_ssh

        self.command = VinfraCommand(self.mock_config, self.mock_config.ADMIN_AUTH)

    def test_execute_command(self):
        mock_output = (0, 'ok')
        self.mock_ssh.execute.return_value = mock_output

        self.command.execute('test command')

        self.mock_ssh.execute.assert_called_with('vinfra --credentials=dummy_credentials test command')

    def test_execute_with_error(self):
        mock_output = (1, 'not ok')
        self.mock_ssh.execute.return_value = mock_output

        with self.assertRaises(VinfraError) as e:
            self.command.execute('test command')

            self.mock_ssh.execute.assert_called_with(
                'vinfra special_param test command -f json')
            self.assertEqual(repr(e), 'VinfraError: command = vinfra special_param test -f json, '
                                      'exit_code = 1, output = not ok')

    @patch('onapp2vhi.inc.vinfra_wrapper.SSH')
    def test_constructor_with_vinfra_access(self, mock_ssh_ctor):
        mock_output = (0, 'ok')
        self.mock_ssh.execute.return_value = mock_output
        mock_ssh_ctor.return_value = self.mock_ssh

        command = VinfraCommand(self.mock_config, vinfra_access="vinfra special_param")

        command.execute('test command')

        self.mock_ssh.execute.assert_called_with(
            'vinfra special_param test command')
