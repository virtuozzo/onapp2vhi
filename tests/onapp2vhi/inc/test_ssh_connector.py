import socket
import unittest

from mock import patch
from onapp2vhi.inc.ssh_connector import SSH


class Test_progress_bar(unittest.TestCase):
    @patch("onapp2vhi.inc.ssh_connector.paramiko", autospec=True)
    def setUp(self, mock_ssh):
        self.ssh = SSH(host="8.8.8.8", ssh_key="fake_key")

    @patch("onapp2vhi.inc.ssh_connector.tqdm", autospec=True)
    @patch("onapp2vhi.inc.ssh_connector.socket", autospec=True)
    def test_live_migration(self, mock_socket, mock_tqdm):
        mock_socket.timeout = socket.timeout
        transport = self.ssh.client.get_transport()
        channel = transport.open_session()
        channel.recv_ready.side_effect = [False, False]
        channel.recv_stderr_ready.side_effect = [True, False]
        channel.recv_stderr.side_effect = [
            b"Migration: [ 99 %]",
            b"Migration: [ 100 %]",
            socket.timeout,
        ]
        self.ssh.execute("virsh migrate", real_data=True)
        self.assertEquals(mock_tqdm().update.call_count, 2)

    @patch("onapp2vhi.inc.ssh_connector.tqdm", autospec=True)
    @patch("onapp2vhi.inc.ssh_connector.socket", autospec=True)
    def test_cold_migration(self, mock_socket, mock_tqdm):
        mock_socket.timeout = socket.timeout
        transport = self.ssh.client.get_transport()
        channel = transport.open_session()
        channel.recv_ready.side_effect = [True, False]
        channel.recv_stderr_ready.side_effect = [False, False]
        channel.recv.side_effect = [
            b"(97.5/100%)",
            b"(98.5/100%)",
            b"(99.6/100%)",
            b"(100/100%)",
            socket.timeout,
        ]
        self.ssh.execute("qemu-img convert", real_data=True)
        self.assertEquals(mock_tqdm().update.call_count, 4)


class TestSSH(unittest.TestCase):
    
    def test_ssh_constructor_no_host_parameter(self):
        with self.assertRaises(ValueError):
            ssh = SSH()

    def test_ssh_constructor_wrong_port_number_type(self):
        with self.assertRaises(TypeError):
            ssh = SSH(host='target.virtuozzo.test', port='22')

    def test_ssh_constructor_wrong_connect_timeout_type(self):
        with self.assertRaises(TypeError):
            ssh = SSH(host='target.virtuozzo.test', port=22, connect_timeout='60')

    def test_ssh_constructor_wrong_channel_timeout_type(self):
        with self.assertRaises(TypeError):
            ssh = SSH(host='target.virtuozzo.test', port=22, channel_timeout='60')

    def test_ssh_constructor_default_parameter(self):
        with patch('paramiko.RSAKey.from_private_key_file') as mock_from_private_key_file:
            ssh = SSH(host='target.virtuozzo.test', ssh_key='~/.ssh/id_rsa')

            self.assertIsNotNone(ssh.host)
            self.assertEqual(ssh.port, 22)
            mock_from_private_key_file.assert_called_once_with('~/.ssh/id_rsa')

            self.assertIsNone(ssh.jumpbox)

    def test_ssh_constructor_wrong_jump_host_external(self):
        with self.assertRaises(TypeError):
            with patch('paramiko.RSAKey.from_private_key_file') as mock_from_private_key_file:
                ssh = SSH(host='target', jump_host_external=1, jump_host_internal='internal',
                          ssh_key='~/.ssh/id_rsa')

    def test_ssh_constructor_without_jump_host_internal(self):
        with self.assertRaises(TypeError):
            with patch('paramiko.RSAKey.from_private_key_file') as mock_from_private_key_file:
                ssh = SSH(host='target', jump_host_external='jumphost', ssh_key='~/.ssh/id_rsa')
                self.assertIsNotNone(ssh.jumpbox)
                self.assertIsNotNone(ssh.jump_host_internal)

    def test_ssh_constructor_without_jump_host_internal(self):
        with self.assertRaises(TypeError):
            with patch('paramiko.RSAKey.from_private_key_file') as mock_from_private_key_file:
                ssh = SSH(host='target', jump_host_external='jumphost', ssh_key='~/.ssh/id_rsa')
                self.assertIsNotNone(ssh.jumpbox)
                self.assertIsNotNone(ssh.jump_host_internal)

    def test_ssh_constructor_wrong_jump_host_internal(self):
        with self.assertRaises(TypeError):
            with patch('paramiko.RSAKey.from_private_key_file') as mock_from_private_key_file:
                ssh = SSH(host='target', jump_host_external='jumphost', jump_host_internal=1,
                          ssh_key='~/.ssh/id_rsa')
                self.assertIsNotNone(ssh.jumpbox)
                self.assertIsNotNone(ssh.jump_host_internal)

    def test_ssh_constructor_wrong_jump_host_port(self):
        with self.assertRaises(TypeError):
            with patch('paramiko.RSAKey.from_private_key_file') as mock_from_private_key_file:
                ssh = SSH(host='target', jump_host_external='jumphost', jump_host_internal='internal',
                          jump_host_port='21', ssh_key='~/.ssh/id_rsa')
                self.assertIsNotNone(ssh.jumpbox)
                self.assertIsNotNone(ssh.jump_host_internal)
