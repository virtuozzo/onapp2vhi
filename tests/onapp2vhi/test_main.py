import unittest
from mock import patch

from click import BadParameter
from onapp2vhi.main import validate_flavor


class ClickCallbackTest(unittest.TestCase):

    @patch("onapp2vhi.main.VinfraFlavor")
    def test_validate_flavor_not_exist(self, vhi_mock):
        vhi_mock.return_value.flavor_list.return_value = "[{\"name\": \"test\"}]"
        mock_flavor = "flavor_test_1"

        with self.assertRaises(BadParameter):
            validate_flavor("", "", mock_flavor)

    @patch("onapp2vhi.main.VinfraFlavor")
    def test_validate_flavor_exist_in_vhi(self, vhi_mock):
        vhi_mock.return_value.flavor_list.return_value = "[{\"name\": \"flavor_test\"}]"
        mock_flavor = "flavor_test"
        result = validate_flavor("", "", mock_flavor)
        self.assertEqual(result, {"name": "flavor_test"})
