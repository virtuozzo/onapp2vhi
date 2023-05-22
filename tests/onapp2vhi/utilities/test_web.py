import requests_mock
from unittest import TestCase
from requests.exceptions import HTTPError

from onapp2vhi.utilities.web import download_file


class DownloadFileTestCase(TestCase):

    @requests_mock.Mocker()
    def test_download_file_ok(self, mock_requests):
        mock_requests.get('http://onapp2vhi.unittest.dev/file/sample.txt',
                          content=b'saldfpqweurqwieyr')

        result = download_file('http://onapp2vhi.unittest.dev/file/sample.txt', '/tmp')
        self.assertEqual(result, '/tmp/sample.txt')

    @requests_mock.Mocker()
    def test_download_file_not_found(self, mock_requests):
        mock_requests.get('http://onapp2vhi.unittest.dev/file/sample.txt',
                          content=b'qwreuqpwiufsd',
                          status_code=404)

        with self.assertRaises(HTTPError):
            download_file('http://onapp2vhi.unittest.dev/file/sample.txt', '/tmp')
