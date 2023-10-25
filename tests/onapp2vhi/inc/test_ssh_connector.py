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
