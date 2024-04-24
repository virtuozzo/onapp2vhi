from unittest import TestCase
from mock import Mock

from onapp2vhi.onapp.onappstore import OnAppStore
from onapp2vhi.inc.ssh_connector import SSH


class OnAppStoreTest(TestCase):

    def setUp(self):
        super().setUp()
        self.mock_ssh = Mock(spec=SSH)
        self.onappstore = OnAppStore(self.mock_ssh)

    def test_get_id_ok(self):
        self.mock_ssh.execute.return_value = (0, 'uuid=1234')
        result = self.onappstore.get_id()
        self.assertIsNotNone(result)
        self.assertEquals(result, '1234')
        self.mock_ssh.execute.assert_called_once_with(command='onappstore getid')

    def test_get_id_ok_twice(self):
        self.mock_ssh.execute.return_value = (0, 'uuid=1234')
        result = self.onappstore.get_id()
        self.assertIsNotNone(result)
        self.assertEquals(result, '1234')
        self.mock_ssh.execute.assert_called_once_with(command='onappstore getid')

        result = self.onappstore.get_id()
        self.assertIsNotNone(result)
        self.assertEquals(result, '1234')
        self.mock_ssh.execute.assert_called_once_with(command='onappstore getid')

    def test_acquire_ok(self):
        self.mock_ssh.execute.side_effect = [
            (0, 'uuid=123456'),
            (0, 'SUCCESS')
        ]

        result = self.onappstore.acquire('abcdef', 'ghifjk')
        self.assertTrue(result)

    def test_offline_ok(self):
        self.mock_ssh.execute.side_effect = [
            (0, 'SUCCESS')
        ]

        self.onappstore.offline(disk_id='test1', key='12345')
